"""
SkyOps Intelligence — 7주차 Step 7: 승객 안내문 한/영 페어 생성 (~5K건)
=======================================================================
항공 이상 상황·지연·비상 시나리오에 대한 승객 안내 방송문을
한국어/영어 페어로 생성합니다.

생성 시나리오:
  - 출발 지연 (기상·기계·관제·연결편)
  - 도착지 변경 (ALTERNATE)
  - 고도 변경 (난기류·최적 고도)
  - 복행 (Go-Around)
  - 비상 착륙
  - 승객 의료 상황

실행:
  python llm_data/generate_passenger_ann.py
  python llm_data/generate_passenger_ann.py --no-api   # 템플릿만 목표 건수 생성

출력:
  data/qa/passenger_ann.jsonl (~5K건)
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
PROJECT_ROOT = Path(__file__).parent.parent
QA_DIR       = PROJECT_ROOT / "data" / "qa"
QA_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSONL    = QA_DIR / "passenger_ann.jsonl"

# ── 시나리오 템플릿 (한/영 페어) ──────────────────────────────────────
ANNOUNCEMENT_TEMPLATES: list[dict] = [
    # ── 출발 지연 ──────────────────────────────────────────────────────
    {
        "scenario":    "departure_delay_weather",
        "delay_min":   None,  # 동적 삽입
        "instruction": "기상으로 인한 출발 지연 상황을 승객에게 한국어와 영어로 안내하세요.",
        "input_ko":    "지연 원인: 기상(강풍), 예상 지연: {delay}분, 항공편: {flight}",
        "output_ko":   (
            "승객 여러분, 안녕하십니까. {flight}편 탑승객 여러분께 알려드립니다. "
            "현재 출발지 기상 악화(강풍)로 인해 약 {delay}분 지연 출발 예정입니다. "
            "불편을 드려 진심으로 사과드리며, 안전한 비행을 위한 조치임을 양해해 주시기 바랍니다. "
            "탑승 시작 시각이 변경되면 즉시 안내 방송을 드리겠습니다. 감사합니다."
        ),
        "output_en":   (
            "Ladies and gentlemen, good day. This is an announcement for passengers of flight {flight}. "
            "Due to adverse weather conditions at the departure airport, our departure will be delayed "
            "by approximately {delay} minutes. We sincerely apologize for this inconvenience. "
            "This delay is necessary to ensure your safety. "
            "We will update you as soon as boarding is ready. Thank you for your patience."
        ),
    },
    {
        "scenario":    "departure_delay_mechanical",
        "instruction": "기계적 결함으로 인한 출발 지연을 승객에게 안내하세요.",
        "input_ko":    "지연 원인: 기계 점검, 예상 지연: {delay}분, 항공편: {flight}",
        "output_ko":   (
            "존경하는 {flight}편 탑승객 여러분. 현재 항공기 정비 점검으로 인해 "
            "출발이 약 {delay}분 지연되고 있습니다. 저희 정비팀이 신속하게 작업 중이며, "
            "안전 운항을 위한 불가피한 조치임을 양해해 주시기 바랍니다. "
            "추가 정보가 확인되는 대로 다시 안내드리겠습니다."
        ),
        "output_en":   (
            "Dear passengers of flight {flight}, we regret to inform you that our departure "
            "has been delayed by approximately {delay} minutes due to a routine maintenance check. "
            "Our maintenance team is working diligently to resolve this matter. "
            "We assure you that your safety is our top priority. "
            "We will provide further updates as soon as possible."
        ),
    },
    {
        "scenario":    "departure_delay_atc",
        "instruction": "관제 지연(ATC hold)으로 인한 출발 지연을 승객에게 안내하세요.",
        "input_ko":    "지연 원인: 관제 허가 대기, 예상 지연: {delay}분, 항공편: {flight}",
        "output_ko":   (
            "{flight}편 탑승객 여러분, 안녕하십니까. "
            "현재 항공 교통 관제(ATC) 지연으로 인해 출발이 {delay}분 지연될 예정입니다. "
            "이는 저희 항공사의 통제 범위를 벗어난 사항으로, 양해를 부탁드립니다. "
            "좌석에서 편안히 기다려 주시면 감사하겠습니다."
        ),
        "output_en":   (
            "Attention passengers on flight {flight}. "
            "We have been informed by Air Traffic Control of a {delay}-minute delay in our departure. "
            "This is due to ATC flow restrictions and is beyond our control. "
            "We appreciate your patience and understanding. "
            "Please remain seated comfortably, and we will depart as soon as we receive clearance."
        ),
    },
    # ── 복행 (Go-Around) ───────────────────────────────────────────────
    {
        "scenario":    "go_around",
        "instruction": "착륙 복행(Go-Around) 상황을 승객에게 안내하세요.",
        "input_ko":    "상황: 복행(Go-Around), 항공편: {flight}, 원인: {reason}",
        "output_ko":   (
            "승객 여러분, 안전한 착륙을 위해 현재 복행 절차를 수행 중입니다. "
            "잠시 후 공항 상공을 선회하여 재착륙 예정이오니 좌석 벨트를 꼭 매주시기 바랍니다. "
            "이는 정상적인 안전 절차이며, 잠시 후 착륙 예정임을 알려드립니다. 감사합니다."
        ),
        "output_en":   (
            "Ladies and gentlemen, for safety reasons, we are currently performing a go-around. "
            "We will circle the airport and attempt another approach in a few minutes. "
            "Please ensure your seatbelts are fastened. "
            "This is a standard safety procedure and is nothing to be concerned about. "
            "We will land shortly. Thank you."
        ),
    },
    # ── 고도 변경 (난기류) ─────────────────────────────────────────────
    {
        "scenario":    "turbulence_altitude_change",
        "instruction": "난기류 회피를 위한 고도 변경을 승객에게 안내하세요.",
        "input_ko":    "상황: 난기류 회피 고도 변경, 항공편: {flight}",
        "output_ko":   (
            "승객 여러분, 전방 기상 상황으로 인해 잠시 난기류 구간을 통과할 예정입니다. "
            "안전을 위해 좌석 벨트 착용 신호등이 켜질 예정이오니, 자리로 돌아가 "
            "좌석 벨트를 착용해 주시기 바랍니다. 기내 이동 자제를 부탁드립니다."
        ),
        "output_en":   (
            "Attention passengers, we are approaching an area of turbulence ahead. "
            "For your safety, the fasten seatbelt sign will be illuminated shortly. "
            "Please return to your seats and fasten your seatbelts immediately. "
            "We ask that you refrain from moving around the cabin until the seatbelt sign is turned off. "
            "Thank you for your cooperation."
        ),
    },
    # ── 도착지 변경 (ALTERNATE) ────────────────────────────────────────
    {
        "scenario":    "alternate_airport_diversion",
        "instruction": "목적지 변경(다이버전)을 승객에게 안내하세요.",
        "input_ko":    "상황: 목적지 {orig_dest} → 대체 공항 {alt_dest}, 원인: {reason}",
        "output_ko":   (
            "승객 여러분께 중요한 안내를 드립니다. "
            "목적지 {orig_dest}의 기상 악화로 인해 대체 공항 {alt_dest}에 착륙할 예정입니다. "
            "착륙 후 상황을 지속 파악하여 신속하게 안내드리겠으며, "
            "불편을 드려 대단히 죄송합니다. 추가 지원이 필요하신 승객께서는 "
            "착륙 후 승무원에게 말씀해 주십시오."
        ),
        "output_en":   (
            "Ladies and gentlemen, we have an important announcement. "
            "Due to deteriorating weather conditions at {orig_dest}, "
            "we will be diverting to our alternate airport, {alt_dest}. "
            "We sincerely apologize for this inconvenience. "
            "After landing, we will provide you with further information regarding your onward journey. "
            "Please do not hesitate to speak with our cabin crew if you require assistance."
        ),
    },
    # ── 비상 착륙 ─────────────────────────────────────────────────────
    {
        "scenario":    "emergency_landing",
        "instruction": "비상 착륙 상황을 침착하게 승객에게 안내하세요.",
        "input_ko":    "상황: 비상 착륙, 원인: {reason}, 항공편: {flight}",
        "output_ko":   (
            "승객 여러분, 침착하게 들어주십시오. "
            "안전상의 이유로 현재 가장 가까운 공항에 비상 착륙할 예정입니다. "
            "좌석 벨트를 단단히 착용하시고, 앞 좌석 등받이의 안전 카드를 다시 확인해 주십시오. "
            "승무원의 지시에 따라 주시면 안전하게 도착할 수 있습니다. "
            "조종사와 전 승무원이 여러분의 안전을 위해 최선을 다하고 있습니다."
        ),
        "output_en":   (
            "Ladies and gentlemen, please listen carefully. "
            "For safety reasons, we will be making an emergency landing at the nearest suitable airport. "
            "Please fasten your seatbelts tightly and review the safety card in the seat pocket in front of you. "
            "Follow all instructions from our cabin crew. "
            "The flight deck and cabin crew are fully trained for this situation "
            "and are doing everything possible to ensure your safety. "
            "Please remain calm."
        ),
    },
    # ── 의료 상황 ─────────────────────────────────────────────────────
    {
        "scenario":    "medical_emergency",
        "instruction": "기내 의료 응급상황 발생 시 의료 전문가 협조 요청 방송을 작성하세요.",
        "input_ko":    "상황: 기내 의료 응급, 항공편: {flight}",
        "output_ko":   (
            "탑승객 여러분께 안내 말씀을 드립니다. "
            "현재 기내에 의료 지원이 필요한 상황이 발생하였습니다. "
            "의사, 간호사, 또는 의료 전문가이신 분께서는 가까운 승무원에게 알려주시기 바랍니다. "
            "협조해 주신 분의 신원은 철저히 보호됩니다. 감사합니다."
        ),
        "output_en":   (
            "Ladies and gentlemen, we have a passenger on board who requires medical attention. "
            "If there is a doctor, nurse, or any medical professional on board, "
            "please identify yourself to the nearest flight attendant. "
            "Your identity and involvement will be kept confidential. "
            "We greatly appreciate your assistance. Thank you."
        ),
    },
]

FLIGHT_NUMBERS = [f"KE{n}" for n in range(601, 660)] + \
                 [f"OZ{n}" for n in range(201, 250)] + \
                 [f"AA{n}" for n in range(100, 150)]
DELAY_OPTIONS   = [10, 15, 20, 30, 45, 60, 90, 120]
REASON_OPTIONS  = ["기상 악화", "기계 점검", "관제 지연", "연결편 대기", "공항 혼잡"]
REASON_EN       = ["weather conditions", "maintenance check", "ATC delay", "connecting passengers", "airport congestion"]
AIRPORTS_DEST   = ["ICN", "NRT", "HKG", "SIN", "LHR", "CDG", "LAX", "JFK"]
AIRPORTS_ALT    = ["PUS", "GMP", "FUK", "KIX", "NGO", "TPE"]


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
)
def call_gpt4_announcement(client, scenario: str, context_ko: str) -> dict:
    """GPT-4로 승객 안내 방송 한/영 생성."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": (
                "You are an expert aviation cabin crew trainer generating passenger announcement scripts. "
                "Generate both Korean (formal, polite) and English versions. "
                "Return JSON: {\"korean\": \"...\", \"english\": \"...\"}"
            )},
            {"role": "user", "content": (
                f"Scenario: {scenario}\n"
                f"Context (Korean): {context_ko}\n"
                "Generate a bilingual passenger announcement. "
                "Korean should be formal 경어체. English should be professional airline standard."
            )},
        ],
        temperature=0.65,
        max_tokens=600,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    return result


def generate_template_announcements(n: int) -> list[dict]:
    """템플릿 기반 승객 안내문 생성."""
    records = []
    while len(records) < n:
        tmpl   = random.choice(ANNOUNCEMENT_TEMPLATES)
        flight = random.choice(FLIGHT_NUMBERS)
        delay  = random.choice(DELAY_OPTIONS)
        ri     = random.randrange(len(REASON_OPTIONS))

        fill_ko = {
            "flight":     flight,
            "delay":      delay,
            "reason":     REASON_OPTIONS[ri],
            "orig_dest":  random.choice(AIRPORTS_DEST),
            "alt_dest":   random.choice(AIRPORTS_ALT),
        }
        fill_en = {**fill_ko, "reason": REASON_EN[ri]}

        try:
            out_ko = tmpl["output_ko"].format(**fill_ko)
            out_en = tmpl["output_en"].format(**fill_en)
            inp    = tmpl["input_ko"].format(**fill_ko)
        except KeyError:
            out_ko = tmpl["output_ko"]
            out_en = tmpl["output_en"]
            inp    = f"항공편: {flight}"

        # Alpaca 형식 — 한국어 output
        records.append({
            "type":        "passenger_ann",
            "instruction": tmpl["instruction"],
            "input":       inp,
            "output":      out_ko,
            "output_en":   out_en,
            "scenario":    tmpl["scenario"],
            "source":      "template",
        })

        if len(records) >= n:
            break

        # 영어 instruction 버전도 추가 (데이터 다양화)
        if random.random() < 0.4:
            records.append({
                "type":        "passenger_ann",
                "instruction": tmpl["instruction"].replace("한국어와 영어로", "in English"),
                "input":       inp,
                "output":      out_en,
                "output_ko":   out_ko,
                "scenario":    tmpl["scenario"],
                "source":      "template_en",
            })

    return records[:n]


def main(args: argparse.Namespace) -> None:
    print("=" * 65)
    print("  SkyOps Intelligence — 승객 안내문 한/영 페어 생성")
    print("=" * 65)

    target     = args.target
    use_api    = not args.no_api
    if use_api:
        n_template = int(target * 0.85)
        n_api      = target - n_template
        print(f"  목표: {target:,}건 (템플릿 {n_template:,} + GPT-4 {n_api:,})")
    else:
        n_template = target
        n_api      = 0
        print(f"  목표: {target:,}건 (템플릿만)")

    # 템플릿 생성
    print(f"\n▶ 템플릿 기반 생성: {n_template:,}건")
    records = generate_template_announcements(n_template)
    print(f"   ✅ {len(records):,}건")

    # GPT-4 증강
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
                print(f"\n▶ GPT-4 생성: {n_api}건")
                for i in range(n_api):
                    tmpl   = random.choice(ANNOUNCEMENT_TEMPLATES)
                    flight = random.choice(FLIGHT_NUMBERS)
                    context_ko = f"{tmpl['scenario']} — 항공편 {flight}"
                    try:
                        result = call_gpt4_announcement(client, tmpl["scenario"], context_ko)
                        api_records.append({
                            "type":        "passenger_ann",
                            "instruction": tmpl["instruction"],
                            "input":       context_ko,
                            "output":      result.get("korean", ""),
                            "output_en":   result.get("english", ""),
                            "scenario":    tmpl["scenario"],
                            "source":      "gpt4",
                        })
                        if (i + 1) % 20 == 0:
                            print(f"   [{i+1}/{n_api}]")
                        time.sleep(0.3)
                    except Exception as e:
                        print(f"   ⚠️  API 오류 ({i}): {e}")
            except ImportError:
                print("   ⚠️  openai 미설치")
        else:
            print("   ⚠️  OPENAI_API_KEY 없음")

    all_records = records + api_records
    random.shuffle(all_records)
    if len(all_records) > target:
        all_records = all_records[:target]

    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n✅ 완료: {len(all_records):,}건 → {OUT_JSONL}")
    print("\n다음 단계: python llm_data/build_alpaca_dataset.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="승객 안내문 한/영 페어 생성")
    parser.add_argument("--target",  type=int, default=5000,
                        help="생성 목표 수 (기본 5000)")
    parser.add_argument("--no-api",  action="store_true",
                        help="GPT-4 API 없이 템플릿만 사용")
    main(parser.parse_args())
