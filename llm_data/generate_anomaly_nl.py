"""
SkyOps Intelligence — 7주차 Step 6: 이상 탐지 결과 → 자연어 설명 템플릿 (~10K건)
================================================================================
Isolation Forest 탐지 결과 + CEP 룰 이벤트를 GPT-4로 자연어 설명으로 변환합니다.
관제사·운항 승무원 대상 이상 상황 보고 문체로 생성합니다.

생성 예시:
  Input:  항공기 KE123, 고도 급변 감지: 500m 하강/25초
  Output: "KE123편에서 비정상적인 고도 강하 패턴이 감지되었습니다.
           25초 이내 500m 강하는 표준 강하율(500fpm)을 3.2배 초과합니다..."

실행:
  python llm_data/generate_anomaly_nl.py
  python llm_data/generate_anomaly_nl.py --target 500 --no-api  # 템플릿만 500건 생성

출력:
  data/qa/anomaly_nl.jsonl   (~10K건)
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from string import Template

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
except ImportError:
    def retry(*a, **kw):
        def decorator(fn): return fn
        return decorator
    def stop_after_attempt(n): return None
    def wait_exponential(**kw): return None
    def retry_if_exception_type(e): return None

# ── 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).parent.parent
IF_ANOMALY    = PROJECT_ROOT / "data" / "results" / "if_anomaly_report.csv"
QA_DIR        = PROJECT_ROOT / "data" / "qa"
QA_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSONL     = QA_DIR / "anomaly_nl.jsonl"

# ── 이상 유형 정의 ─────────────────────────────────────────────────────
ANOMALY_TYPES = {
    "ALTITUDE_SPIKE": {
        "name_kr": "고도 급변",
        "severity_map": {"LOW": "주의", "MEDIUM": "경고", "HIGH": "긴급"},
    },
    "VELOCITY_SPIKE": {
        "name_kr": "속도 이상",
        "severity_map": {"LOW": "주의", "MEDIUM": "경고", "HIGH": "긴급"},
    },
    "PATH_DEVIATION": {
        "name_kr": "경로 이탈",
        "severity_map": {"LOW": "주의", "MEDIUM": "경고", "HIGH": "긴급"},
    },
    "FLIGHT_DELAY": {
        "name_kr": "비정상 지연",
        "severity_map": {"LOW": "주의", "MEDIUM": "경고", "HIGH": "심각"},
    },
}

# ── 템플릿 기반 설명 (API 없이 즉시 생성) ────────────────────────────
TEMPLATE_DB: dict[str, list[str]] = {
    "ALTITUDE_SPIKE": [
        "{callsign}편에서 비정상적인 고도 강하 패턴이 감지되었습니다. "
        "{elapsed}초 이내 {delta_m:.0f}m 강하는 표준 강하율(500fpm)을 초과합니다. "
        "FAA AIM 7-6-4 기준에 따라 즉시 조종사 확인 교신이 필요합니다.",

        "[{severity}] {callsign} — 고도 급변 탐지: {delta_m:.0f}m / {elapsed}초. "
        "현재 고도 {altitude_m:.0f}m. 관제사 확인 요망.",

        "이상 탐지 알림: {callsign}의 급격한 고도 변화({delta_m:.0f}m/{elapsed}초)가 "
        "감지되었습니다. 현재 비행 단계와 조종사 의도를 확인하십시오. "
        "비상 상황 가능성을 배제하지 마십시오.",
    ],
    "VELOCITY_SPIKE": [
        "{callsign}편에서 비정상적인 속도 변화가 탐지되었습니다. "
        "{elapsed}초 동안 {delta_kt:.1f}kt 변화(분당 {rate_kt:.1f}kt)는 "
        "기준치(100kt/min)를 {ratio:.1f}배 초과합니다. 즉각 교신 확인 바랍니다.",

        "[{severity}] 속도 이상 — {callsign}: {delta_kt:.1f}kt/{elapsed}초 변화. "
        "엔진 이상 또는 구조적 문제 가능성 확인 필요.",

        "SkyOps 이상 탐지: {callsign} 급속 속도 변화 탐지. "
        "TCAS 분리 및 주변 항공기 안전 간격 유지 상태 확인 권고.",
    ],
    "PATH_DEVIATION": [
        "{callsign}편이 계획 경로에서 {deviation_km:.1f}km 이탈하였습니다. "
        "항법 시스템 이상 또는 관제 지시 미준수 가능성을 확인하십시오. "
        "인근 제한 구역·특별 사용 공역(SUA) 진입 여부를 점검하세요.",

        "[{severity}] 경로 이탈 탐지 — {callsign}: {deviation_km:.1f}km 편차. "
        "NOTAM 및 ATIS 정보 재확인 후 조종사 교신 바랍니다.",

        "이상 경보: {callsign} 경로 이탈 {deviation_km:.1f}km. "
        "비상 상황 여부 확인 및 필요 시 긴급 주파수(121.5 MHz) 모니터링 권고.",
    ],
    "FLIGHT_DELAY": [
        "{callsign}편에서 비정상적인 지연 패턴이 ML 모델에 의해 감지되었습니다. "
        "직전 편 지연 {prev_delay:.0f}분, 이력 지연율 {hist_delay:.1f}% 기반 "
        "예측 지연 {pred_delay:.0f}분 이상. 지상 운영팀 사전 알림 권고.",

        "[이상 탐지] {carrier} {origin}→{dest}: 복합 지연 요인 탐지 "
        "(이력 지연·기상·혼잡도 앙상블 F1={f1:.2f}). "
        "슬롯 조정 및 여객 안내 선제 조치 권고.",

        "SkyOps 지연 위험 경보 — {callsign}: Isolation Forest 이상 점수 {if_score:.4f}. "
        "해당 편은 상위 {percentile:.0f}% 지연 위험군에 속합니다. "
        "대체 편 준비 및 연결편 여객 모니터링 시작.",
    ],
}

# ── GPT-4 생성 프롬프트 ────────────────────────────────────────────────
SYSTEM_PROMPT_ANOMALY = """You are an aviation safety expert generating natural language explanations
of flight anomalies for air traffic controllers and flight operations centers.
Generate formal, precise, aviation-standard language explanations.
Each explanation should:
1. State the anomaly type and severity clearly
2. Provide specific numeric values
3. Reference relevant regulations or procedures (FAA/ICAO)
4. Recommend immediate actions
5. Be in Korean (한국어) formal register (경어체)"""


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
)
def call_gpt4_anomaly(client, anomaly_data: dict) -> str:
    """GPT-4로 이상 탐지 자연어 설명 생성."""
    prompt = (
        f"다음 항공 이상 탐지 데이터를 관제사용 한국어 경어체로 설명하세요:\n\n"
        f"{json.dumps(anomaly_data, ensure_ascii=False, indent=2)}\n\n"
        f"2~3문장으로 이상 내용, 위험도, 권고 조치를 포함하여 설명하십시오."
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_ANOMALY},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.6,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


def generate_template_records(n: int) -> list[dict]:
    """API 없이 템플릿으로 이상 탐지 설명 레코드 생성."""
    records = []
    carriers  = ["KE", "OZ", "AA", "UA", "DL", "WN", "LH", "EK"]
    severities = ["LOW", "MEDIUM", "HIGH"]

    for i in range(n):
        a_type    = random.choice(list(TEMPLATE_DB.keys()))
        severity  = random.choices(severities, weights=[0.5, 0.35, 0.15])[0]
        template  = random.choice(TEMPLATE_DB[a_type])
        carrier   = random.choice(carriers)
        flight_no = random.randint(100, 999)
        callsign  = f"{carrier}{flight_no}"

        # 공통 필드
        fill = {
            "callsign":     callsign,
            "carrier":      carrier,
            "severity":     ANOMALY_TYPES[a_type]["severity_map"][severity],
            "elapsed":      random.randint(15, 90),
            "altitude_m":   random.uniform(1000, 12000),
            "origin":       random.choice(["ICN", "GMP", "PUS", "CJU", "JFK", "LAX"]),
            "dest":         random.choice(["NRT", "HKG", "SIN", "LHR", "CDG", "FRA"]),
            "delta_m":      random.uniform(200, 1500),
            "delta_kt":     random.uniform(30, 150),
            "rate_kt":      random.uniform(60, 300),
            "ratio":        random.uniform(1.2, 4.0),
            "deviation_km": random.uniform(5, 50),
            "prev_delay":   random.uniform(10, 120),
            "hist_delay":   random.uniform(15, 60),
            "pred_delay":   random.uniform(20, 90),
            "f1":           random.uniform(0.30, 0.45),
            "if_score":     random.uniform(-0.65, -0.40),
            "percentile":   random.uniform(80, 99),
        }

        try:
            explanation = template.format(**fill)
        except KeyError:
            explanation = f"[{fill['severity']}] {callsign} — {a_type} 탐지"

        # Alpaca instruction 생성
        instruction_templates = [
            f"다음 항공 이상 탐지 결과를 관제사에게 자연어로 설명하세요.",
            f"항공 이상 이벤트({ANOMALY_TYPES[a_type]['name_kr']})를 운항 관리 보고서 형식으로 작성하세요.",
            f"SkyOps 이상 탐지 시스템의 경보 내용을 관제사용 경어체로 변환하세요.",
            f"아래 이상 탐지 데이터의 의미와 권고 조치를 설명하세요.",
        ]

        input_data = {
            "icao24":       f"{random.randint(0x400000, 0x7FFFFF):06X}",
            "callsign":     callsign,
            "anomaly_type": a_type,
            "severity":     severity,
            "details":      {
                k: v for k, v in fill.items()
                if k in ["delta_m", "delta_kt", "deviation_km", "elapsed",
                         "altitude_m", "prev_delay", "pred_delay"]
            },
        }

        records.append({
            "type":        "anomaly_nl",
            "instruction": random.choice(instruction_templates),
            "input":       json.dumps(input_data, ensure_ascii=False),
            "output":      explanation,
            "category":    a_type.lower(),
            "severity":    severity,
        })

    return records


def generate_with_api(client, n_api: int, existing: list[dict]) -> list[dict]:
    """GPT-4로 고품질 이상 설명 생성 (전체의 20%)."""
    new_records = []
    print(f"   GPT-4 고품질 생성: {n_api}건")
    for i in range(n_api):
        a_type = random.choice(list(ANOMALY_TYPES.keys()))
        anomaly_data = {
            "anomaly_type": a_type,
            "severity":     random.choice(["LOW", "MEDIUM", "HIGH"]),
            "callsign":     f"KE{random.randint(100,999)}",
            "details":      {
                "delta_m":      round(random.uniform(300, 1200), 1),
                "elapsed_sec":  random.randint(15, 60),
                "altitude_m":   round(random.uniform(3000, 11000), 0),
            },
        }
        try:
            output = call_gpt4_anomaly(client, anomaly_data)
            new_records.append({
                "type":        "anomaly_nl",
                "instruction": "다음 항공 이상 탐지 결과를 관제사에게 자연어로 설명하세요.",
                "input":       json.dumps(anomaly_data, ensure_ascii=False),
                "output":      output,
                "category":    a_type.lower(),
                "source":      "gpt4",
            })
            if (i + 1) % 10 == 0:
                print(f"      [{i+1}/{n_api}]")
            time.sleep(0.3)
        except Exception as e:
            print(f"      ⚠️  오류 ({i}): {e}")

    return new_records


def main(args: argparse.Namespace) -> None:
    print("=" * 65)
    print("  SkyOps Intelligence — 이상 탐지 자연어 설명 생성")
    print("=" * 65)

    target      = args.target
    use_api     = not args.no_api
    if use_api:
        n_template = int(target * 0.80)
        n_api      = target - n_template
        print(f"  목표: {target:,}건 (템플릿 {n_template:,} + GPT-4 {n_api:,})")
    else:
        n_template = target
        n_api      = 0
        print(f"  목표: {target:,}건 (템플릿만)")

    # 템플릿 생성
    print(f"\n▶ 템플릿 기반 생성: {n_template:,}건")
    template_records = generate_template_records(n_template)
    print(f"   ✅ {len(template_records):,}건")

    # GPT-4 생성 (API 키 있을 때)
    api_records = []
    if use_api and n_api > 0:
        try:
            from dotenv import load_dotenv
            load_dotenv(PROJECT_ROOT / ".env")
        except ImportError:
            pass

        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                api_records = generate_with_api(client, n_api, template_records)
            except ImportError:
                print("   ⚠️  openai 미설치 — 템플릿만 사용")
        else:
            print("   ⚠️  OPENAI_API_KEY 없음 — 템플릿만 사용")

    all_records = template_records + api_records
    random.shuffle(all_records)

    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n✅ 완료: {len(all_records):,}건 → {OUT_JSONL}")
    print("\n다음 단계: python llm_data/generate_passenger_ann.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="이상 탐지 자연어 설명 생성")
    parser.add_argument("--target",   type=int,  default=10000,
                        help="생성 목표 수 (기본 10000)")
    parser.add_argument("--no-api",   action="store_true",
                        help="GPT-4 API 없이 템플릿만 사용")
    main(parser.parse_args())
