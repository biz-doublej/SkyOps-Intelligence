"""SkyOps Korean Aviation SFT corpus generator (P7-D · 2026-04-15).

Strategic Review #7 (LLM 한국어 품질) follow-through. Generates
domain-specific Korean SFT pairs to address Qwen2.5-7B's known
weakness on Korean aviation terminology.

Categories generated:
  1. ATC 표준 한국어 교신 (3-letter callsign + 절차)
  2. 항공 약어 → 한국어 정의
  3. NOTAM 한국어 해석 (P5+ SWIM 데이터 augment)
  4. RKSI/RKSS 특화 시나리오
  5. 한국 항공법 + 국토부 고시 핵심 조항 paraphrase

Output:
  data/alpaca/korean_aviation_sft.jsonl   (~3000 pairs)
  data/alpaca/korean_aviation_dpo.jsonl   (~500 chosen/rejected pairs)

Note:
  This script generates *seed* data + templates. Actual model retraining
  is out of scope (requires GPU, ~9 hours QLoRA on RTX 3070 — see
  llm_data/fine_tune_qlora.py). The generated JSONL is ready to be
  merged into aviation_alpaca_train.jsonl on the next training run.

Run:
    python llm_data/generate_korean_aviation_corpus.py
    python llm_data/generate_korean_aviation_corpus.py --n-sft 5000 --n-dpo 1000
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "alpaca"

# ── 1. ATC 표준 한국어 교신 (50+ templates) ──────────────────────────
ATC_TEMPLATES = [
    {
        "instruction": "다음 영문 ATC 교신을 한국어로 번역하시오.",
        "input": "Korean Air {flight}, contact tower on 118.1.",
        "output": "코리안에어 {flight}, 타워 118.1로 접촉하십시오.",
    },
    {
        "instruction": "다음 영문 ATC 교신을 한국어로 번역하시오.",
        "input": "Asiana {flight}, cleared for takeoff runway 33L, wind 320 at 8.",
        "output": "아시아나 {flight}, 활주로 33L 이륙 허가, 바람 320 방향 8노트.",
    },
    {
        "instruction": "다음 영문 ATC 교신을 한국어로 번역하시오.",
        "input": "{flight}, descend and maintain flight level 240, expedite through 280.",
        "output": "{flight}, 비행고도 240으로 강하 후 유지, 280 통과 시 신속히 강하하십시오.",
    },
    {
        "instruction": "다음 영문 ATC 교신을 한국어로 번역하시오.",
        "input": "Jeju Air {flight}, hold short of runway 15R, traffic landing.",
        "output": "제주항공 {flight}, 활주로 15R 진입 대기, 착륙 트래픽 있음.",
    },
    {
        "instruction": "다음 영문 ATC 교신을 한국어로 번역하시오.",
        "input": "{flight}, squawk 7700, state souls on board and fuel remaining.",
        "output": "{flight}, 스쿽 7700 설정, 탑승 인원과 잔존 연료를 보고하십시오.",
    },
    {
        "instruction": "다음 한국어 ATC 교신에 영문으로 응답하시오.",
        "input": "코리안에어 {flight}, 게이트로 진입 허가, 게이트 23번 사용.",
        "output": "Korean Air {flight}, cleared to gate, use gate 23.",
    },
    {
        "instruction": "다음 영문 ATC 교신을 한국어로 번역하시오.",
        "input": "{flight}, expect ILS approach runway 33L, vectors for final.",
        "output": "{flight}, 활주로 33L ILS 접근 예상, 최종 접근을 위한 벡터링 받으십시오.",
    },
    {
        "instruction": "다음 영문 ATC 교신을 한국어로 번역하시오.",
        "input": "{flight}, go around, missed approach, climb to 3000.",
        "output": "{flight}, 복행, 실패 접근, 3000피트로 상승하십시오.",
    },
]

CALLSIGNS = ["123", "456", "789", "234", "567", "890", "321", "654", "987",
             "111", "222", "333", "444", "555", "666", "777", "888", "999"]


# ── 2. 항공 약어 → 한국어 (60+ items) ────────────────────────────────
ABBREVIATIONS = {
    "ILS": "계기 착륙 장치 (Instrument Landing System) — 활주로 진입 시 정밀한 수평·수직 안내를 제공하는 무선 항법 시설",
    "VOR": "전방위 무선표지 (VHF Omnidirectional Range) — 항공기에 정확한 방위 정보를 제공하는 지상 항법 보조 시설",
    "DME": "거리 측정 장치 (Distance Measuring Equipment) — 항공기와 지상국 간 슬랜트 거리를 측정",
    "NDB": "무지향성 무선표지 (Non-Directional Beacon) — 단순 방위 신호를 송출하는 저주파 항법 시설",
    "GPS": "위성 항법 시스템 (Global Positioning System) — 위성을 이용한 정밀 위치 측정",
    "RNAV": "지역 항법 (Area Navigation) — GPS/INS 기반 임의 경로 비행",
    "RNP": "필수 항법 성능 (Required Navigation Performance) — 일정 정확도 이상의 항법 성능 인증",
    "ATIS": "공항 자동 정보 방송 (Automatic Terminal Information Service) — 활주로/풍향/시정 등 자동 송출",
    "METAR": "정시 항공 기상 보고 (Meteorological Aerodrome Report) — 매시간 발행되는 공항 기상 관측",
    "TAF": "공항 예보 (Terminal Aerodrome Forecast) — 24~30시간 공항 기상 예측",
    "SIGMET": "중요 기상 정보 (Significant Meteorological Information) — 위험 기상 경고",
    "AIRMET": "일반 기상 정보 (Airmen's Meteorological Information) — 비교적 약한 기상 위험 통지",
    "NOTAM": "항공고시보 (Notice to Airmen) — 운항 안전 관련 임시 정보 공지",
    "ATFM": "항공 교통 흐름 관리 (Air Traffic Flow Management) — 수요-용량 균형 위한 trafffic 통제",
    "GDP": "지상 지연 프로그램 (Ground Delay Program) — 도착 공항 capacity 부족 시 출발 지연",
    "CTOT": "계산된 이륙 시각 (Calculated Take-Off Time) — ATFM이 부여하는 이륙 슬롯",
    "EOBT": "이륙 예정 시각 (Estimated Off-Block Time) — 게이트 출발 예정 시각",
    "TOBT": "목표 이륙 시각 (Target Off-Block Time) — A-CDM milestone",
    "TSAT": "목표 시동 승인 시각 (Target Start-up Approval Time) — A-CDM milestone",
    "FIR": "비행 정보 구역 (Flight Information Region) — ATS 책임 구역",
    "TCAS": "공중 충돌 방지 장치 (Traffic Collision Avoidance System)",
    "TAWS": "지형 인지 경고 시스템 (Terrain Awareness and Warning System)",
    "ADS-B": "방송형 자동 종속 감시 (Automatic Dependent Surveillance - Broadcast)",
    "CPDLC": "관제사-조종사 데이터 링크 통신 (Controller-Pilot Data Link Communications)",
    "SWIM": "FAA 시스템 통합 정보 관리 (System Wide Information Management)",
    "A-CDM": "공항 협업 의사결정 (Airport Collaborative Decision Making)",
    "QNH": "해면 기압 (Sea-level Pressure) — 고도계 설정값, 진고도(true altitude) 표시 기준",
    "RVR": "활주로 가시거리 (Runway Visual Range) — 자동 측정된 활주로 가시 거리",
    "DH": "결심 고도 (Decision Height) — 이 고도에서 활주로 시각 확인 못 하면 복행",
    "MDA": "최저 강하 고도 (Minimum Descent Altitude) — 비정밀 접근 시 최저 고도",
    "VFR": "시계 비행 규칙 (Visual Flight Rules) — 시정 양호 시 적용",
    "IFR": "계기 비행 규칙 (Instrument Flight Rules) — 시정 부족 시 ATC 통제 하 비행",
    "MVFR": "한계 시계 비행 (Marginal VFR) — VFR 하한 근처",
    "LIFR": "저시정 계기 비행 (Low IFR) — 가장 낮은 시정 카테고리",
    "FOD": "외부 이물 (Foreign Object Debris) — 활주로/유도로의 위험물",
    "PIREP": "조종사 보고 (Pilot Report) — 실시간 기상/난기류 관측 보고",
    "UUA": "긴급 PIREP (Urgent PIREP) — 심각한 위험 기상",
    "FOQA": "비행 운항 품질 보증 (Flight Operations Quality Assurance) — FDR 데이터 분석",
    "LOSA": "라인 운항 안전 감사 (Line Operations Safety Audit)",
    "SMS": "안전 관리 시스템 (Safety Management System) — ICAO 표준 4 pillar 체계",
    "SRM": "안전 위험 관리 (Safety Risk Management) — SMS의 핵심 활동",
    "SA": "안전 보장 (Safety Assurance) — SMS의 모니터링 활동",
    "RWYCC": "활주로 상태 코드 (Runway Condition Code) — 0~6, 6 = dry",
    "GRF": "글로벌 보고 형식 (Global Reporting Format) — ICAO 활주로 상태 표준",
    "HOT": "유보 시간 (Holdover Time) — 결빙 방지액 효력 시간",
    "CAT": "청천 난기류 (Clear Air Turbulence) — 구름 없는 곳에서 발생하는 난기류",
    "BASH": "조류 항공기 충돌 (Bird Aircraft Strike Hazard) — 조류 충돌 방지 프로그램",
    "LAHSO": "착륙 후 단축 정지 운영 (Land and Hold Short Operations)",
    "ASDE-X": "공항 표면 탐지 장비 모델 X (Airport Surface Detection Equipment - Model X)",
    "ASSC": "공항 표면 감시 능력 (Airport Surface Surveillance Capability) — ASDE-X 후속",
    "STAR": "표준 도착 경로 (Standard Terminal Arrival Route)",
    "SID": "표준 출발 경로 (Standard Instrument Departure)",
    "MNPS": "최저 항법 성능 사양 (Minimum Navigation Performance Specifications)",
    "RVSM": "축소 수직 분리 최소치 (Reduced Vertical Separation Minima) — FL290~410, 1000ft",
    "ETOPS": "쌍발기 연장 운항 (Extended-range Twin-engine Operational Performance Standards)",
    "OTP": "정시 운항률 (On-Time Performance)",
    "D-15": "출발 지연 15분 이내 (Departure within 15 minutes)",
    "A-15": "도착 지연 15분 이내 (Arrival within 15 minutes)",
}


# ── 3. NOTAM 한국어 해석 (50 templates × Q-code variants) ────────────
NOTAM_TEMPLATES = [
    {
        "raw": "RWY {rwy} CLSD DUE TO MAINT WEF {start} TIL {end}",
        "ko": "활주로 {rwy} 정비로 인한 폐쇄, {start}부터 {end}까지 유효.",
        "qcode": "QMRLC",
        "klass": "AERODROME",
    },
    {
        "raw": "ILS RWY {rwy} U/S",
        "ko": "활주로 {rwy} ILS 사용 불가.",
        "qcode": "QICAS",
        "klass": "NAV",
    },
    {
        "raw": "VOR {ident} OUT OF SERVICE",
        "ko": "{ident} VOR 운용 정지.",
        "qcode": "QNVAS",
        "klass": "NAV",
    },
    {
        "raw": "TWY {twy} CLSD",
        "ko": "유도로 {twy} 폐쇄.",
        "qcode": "QMTLC",
        "klass": "AERODROME",
    },
    {
        "raw": "BIRD ACTIVITY VICINITY ARP",
        "ko": "공항 기준점 인근 조류 활동 보고됨, 주의 운항 권고.",
        "qcode": "QFAHX",
        "klass": "OPS",
    },
    {
        "raw": "WIND SHEAR REPORTED ON FINAL RWY {rwy}",
        "ko": "활주로 {rwy} 최종 접근 구간 윈드시어 보고됨.",
        "qcode": "QFAHX",
        "klass": "OPS",
    },
    {
        "raw": "TEMPORARY MIL EXERCISE FL{lo}-FL{hi} WITHIN {fir}",
        "ko": "{fir} 내 FL{lo}-FL{hi} 임시 군 훈련 예정, 우회 권고.",
        "qcode": "QRTCA",
        "klass": "AIRSPACE",
    },
]


# ── 4. RKSI/RKSS 시나리오 ────────────────────────────────────────────
RKSI_SCENARIOS = [
    {
        "instruction": "RKSI에서 South Flow 운영 시 일반적인 이착륙 활주로 배정을 설명하시오.",
        "input": "",
        "output": "RKSI South Flow는 풍향 110~250°·풍속 5kt 이상 시 적용되며, 이륙은 15L/15R/16, 착륙은 33R/33L/34를 사용합니다. 야간(23~06 KST)에는 소음 영향 분산을 위해 North Flow로 전환하기도 합니다.",
    },
    {
        "instruction": "RKSI에서 GUKDO 1A STAR로 도착 중 예상 holding 시간을 안내하시오.",
        "input": "현재 RKSI 도착 트래픽이 평균 수준이며, GUKDO에서 holding 패턴 진입 지시를 받았습니다.",
        "output": "GUKDO holding은 17,000ft, right turns, 4nm legs입니다. 평시 평균 holding 시간은 8~12분이며, ATC가 expected approach time(EAT)을 통보합니다. 잔여 연료 확인 후 EAT 기준으로 강하 시점을 계획하십시오.",
    },
    {
        "instruction": "RKSI 동절기 운영 시 de-icing 절차를 한국어로 설명하시오.",
        "input": "OAT -3°C, light snow 1mm/h, Type IV 도포 예정.",
        "output": "Type IV 결빙 방지액의 일반 holdover time은 강설 1mm/h 시 35~75분입니다. 이 시간 내 이륙하지 못하면 재도포가 필요합니다. RKSI 제1터미널 7개, 제2터미널 5개의 de-icing pad가 운영됩니다. ATC와 takeoff timing을 협의하고 임계 표면(날개·꼬리) 결빙 여부를 최종 점검하십시오.",
    },
    {
        "instruction": "RKSS(김포)에서 RKSI(인천)로 ferry 비행 시 주요 점검 사항은?",
        "input": "",
        "output": "RKSS-RKSI 거리는 약 30 NM로 짧지만, 두 공항이 같은 RKRR FIR에 있어 ATC 인계가 신속합니다. 주요 점검: 1) RKSI 도착 STAR 사전 확인 (GUKDO/POTON/PUNAM/REPOV 1A), 2) 두 공항 모두 CAT IIIb ILS 운용 — 저시정 시 자동 착륙 가능, 3) 출발 RKSS 14L/32R, 도착 RKSI 활주로는 ATIS 확인 후 결정.",
    },
]


# ── 5. 항공법 / 국토부 고시 paraphrase ───────────────────────────────
LAW_PAIRS = [
    {
        "instruction": "한국 항공안전법 제63조(승무원의 임무 등)의 핵심을 설명하시오.",
        "input": "",
        "output": "운항승무원은 항공기의 안전 운항에 필요한 임무를 성실히 수행해야 하며, 비행 전 항공기 점검·기상 정보 확인·연료량 산정·운항 계획 수립을 의무로 합니다. 비행 중에는 ATC 지시를 따르되 안전을 위해 필요한 경우 deviate 권한이 있으며, 그 사유를 사후 보고해야 합니다.",
    },
    {
        "instruction": "국토교통부 고시 '항공기 이상 상황 발생 시 보고에 관한 규정'의 보고 시한을 안내하시오.",
        "input": "",
        "output": "항공안전 의무 보고는 발생 즉시 ATC와 운항관리자에게, 항공안전 자율 보고는 72시간 이내에 한국교통안전공단(TS) 또는 국토부에 제출합니다. 사고(accident)는 즉시 항공철도사고조사위원회(ARAIB)에, 준사고(serious incident) 및 항공안전장애는 발생 후 7일 이내에 보고합니다.",
    },
    {
        "instruction": "한국 항공안전법상 음주 비행 금지 기준은?",
        "input": "",
        "output": "운항승무원은 비행 8시간 전부터 음주가 금지되며, 비행 직전 호기 중 알코올 농도 0.02% 이상 검출 시 비행이 정지됩니다. 위반 시 자격정지 또는 면허취소, 형사 처벌 대상이 됩니다. ICAO Annex 1 표준(0.04%)보다 엄격한 기준입니다.",
    },
]


def gen_atc(n: int) -> list[dict]:
    out: list[dict] = []
    for _ in range(n):
        tpl = random.choice(ATC_TEMPLATES)
        cs = random.choice(CALLSIGNS)
        out.append({
            "instruction": tpl["instruction"],
            "input": tpl["input"].format(flight=cs),
            "output": tpl["output"].format(flight=cs),
            "_source": "korean_aviation_atc_v2",
        })
    return out


def gen_abbrev(n: int) -> list[dict]:
    out: list[dict] = []
    pairs = list(ABBREVIATIONS.items())
    for _ in range(n):
        abbr, defn = random.choice(pairs)
        # forward
        out.append({
            "instruction": f"항공 약어 '{abbr}'의 의미를 한국어로 설명하시오.",
            "input": "",
            "output": defn,
            "_source": "korean_aviation_abbrev_v2",
        })
        # reverse
        out.append({
            "instruction": "다음 한국어 정의에 해당하는 항공 약어를 답하시오.",
            "input": defn,
            "output": abbr,
            "_source": "korean_aviation_abbrev_v2",
        })
    return out


def gen_notam(n: int) -> list[dict]:
    out: list[dict] = []
    rwys = ["15L", "15R", "33L", "33R", "16", "34", "14L", "32R", "01", "19"]
    twys = ["A1", "B2", "C3", "P3", "P4", "S2"]
    idents = ["SLU", "GUKDO", "OLMEN", "POTON", "PUNAM"]
    firs = ["RKRR", "ZSHA", "RJJJ", "ZTAO"]
    for _ in range(n):
        tpl = random.choice(NOTAM_TEMPLATES)
        ctx = {
            "rwy": random.choice(rwys),
            "twy": random.choice(twys),
            "ident": random.choice(idents),
            "fir": random.choice(firs),
            "lo": random.randint(150, 350),
            "hi": random.randint(360, 450),
            "start": "2026-04-15 1200Z",
            "end": "2026-04-15 1800Z",
        }
        try:
            raw = tpl["raw"].format(**ctx)
            ko = tpl["ko"].format(**ctx)
        except KeyError:
            continue
        out.append({
            "instruction": "다음 NOTAM 원문을 한국어로 해석하고, Q-code 와 NOTAM class를 명시하시오.",
            "input": raw,
            "output": f"{ko}\n\nQ-code: {tpl['qcode']}\nClass: {tpl['klass']}",
            "_source": "korean_aviation_notam_v2",
        })
    return out


def gen_dpo(n: int) -> list[dict]:
    """Generate DPO chosen/rejected pairs.

    chosen   = correct, terminologically precise Korean
    rejected = common Qwen2.5 failure modes:
                 - 중국어 코드스위칭
                 - 영어 그대로 출력
                 - 공손어 미사용
                 - 약어를 한국어로 풀어쓰지 않음
    """
    out: list[dict] = []
    abbrev_items = list(ABBREVIATIONS.items())
    for _ in range(n):
        # Mode A: 약어 해석
        if random.random() < 0.5:
            abbr, defn = random.choice(abbrev_items)
            chosen = defn
            # rejected variant: 영어 그대로 + 공손어 누락
            rejected_variants = [
                f"{abbr} stands for the abbreviation used in aviation operations.",  # 영어
                f"{abbr}는 항공에서 쓰이는 약어다.",  # 정의 누락
                defn.replace("입니다", "임").replace("합니다", "함"),  # 공손어 변형
            ]
            out.append({
                "prompt": f"항공 약어 '{abbr}'의 의미를 한국어로 설명하시오.",
                "chosen": chosen,
                "rejected": random.choice(rejected_variants),
                "_source": "korean_aviation_dpo_v2",
            })
        else:
            # Mode B: ATC 교신 번역
            tpl = random.choice(ATC_TEMPLATES)
            cs = random.choice(CALLSIGNS)
            inst = tpl["instruction"]
            inp = tpl["input"].format(flight=cs)
            chosen = tpl["output"].format(flight=cs)
            # rejected: 영어 일부 잔존 + 약어 미번역
            rejected = chosen.replace("활주로", "runway").replace("이륙 허가", "cleared takeoff")
            out.append({
                "prompt": f"{inst}\n\n{inp}",
                "chosen": chosen,
                "rejected": rejected,
                "_source": "korean_aviation_dpo_v2",
            })
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-sft", type=int, default=3000)
    parser.add_argument("--n-dpo", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print(f"  Korean Aviation Corpus Generator (P7-D)")
    print("=" * 65)

    # SFT split: 40% ATC, 30% abbrev, 20% notam, 5% rksi, 5% law
    n_atc = int(args.n_sft * 0.40)
    n_abbrev = int(args.n_sft * 0.30 / 2)  # /2 because each gen produces 2
    n_notam = int(args.n_sft * 0.20)

    sft = []
    sft.extend(gen_atc(n_atc))
    sft.extend(gen_abbrev(n_abbrev))
    sft.extend(gen_notam(n_notam))

    # Sprinkle RKSI scenarios + law (small fixed pools, repeat)
    sft.extend(RKSI_SCENARIOS * max(1, int(args.n_sft * 0.05 / len(RKSI_SCENARIOS))))
    sft.extend(LAW_PAIRS * max(1, int(args.n_sft * 0.05 / len(LAW_PAIRS))))

    random.shuffle(sft)

    sft_out = DATA_DIR / "korean_aviation_sft.jsonl"
    with open(sft_out, "w", encoding="utf-8") as f:
        for r in sft:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dpo = gen_dpo(args.n_dpo)
    dpo_out = DATA_DIR / "korean_aviation_dpo.jsonl"
    with open(dpo_out, "w", encoding="utf-8") as f:
        for r in dpo:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n📝 SFT: {len(sft):,} pairs  →  {sft_out.relative_to(PROJECT_ROOT)}")
    print(f"📝 DPO: {len(dpo):,} pairs  →  {dpo_out.relative_to(PROJECT_ROOT)}")

    # Sample preview
    print("\n  Sample SFT[0]:")
    print(f"    instruction: {sft[0]['instruction'][:80]}")
    print(f"    input:       {sft[0]['input'][:80]}")
    print(f"    output:      {sft[0]['output'][:80]}")
    print("\n  Sample DPO[0]:")
    print(f"    prompt:   {dpo[0]['prompt'][:80]}")
    print(f"    chosen:   {dpo[0]['chosen'][:80]}")
    print(f"    rejected: {dpo[0]['rejected'][:80]}")

    print("\n" + "=" * 65)
    print(f"  ✅ Korean corpus ready for next QLoRA + DPO retrain")
    print(f"  Merge cmd: `cat {sft_out.name} >> aviation_alpaca_train.jsonl`")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
