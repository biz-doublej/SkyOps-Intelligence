"""
SkyOps Intelligence — 7주차 Step 8: Alpaca 포맷 최종 데이터셋 빌드 (~95K건)
============================================================================
모든 소스 데이터를 Alpaca instruction-following 포맷으로 통합합니다.

소스 합산:
  ATC 코퍼스 (Whisper)     → ~15K건  (instruction: 교신 분류/해석)
  규정 QA (GPT-4)          → ~25K건
  절차 QA (GPT-4)          → ~20K건
  비상 상황 QA (GPT-4)     → ~10K건
  용어 정의 QA (GPT-4)     →  ~5K건
  이상 탐지 NL 설명        → ~10K건
  승객 안내문 한/영        →  ~5K건
  ─────────────────────────────────
  총계                     → ~90K건 (목표 ~95K)

Alpaca 포맷:
  {
    "instruction": "...",  # 태스크 지시문
    "input":       "...",  # 컨텍스트 (없으면 "")
    "output":      "..."   # 기대 출력
  }

실행:
  python llm_data/build_alpaca_dataset.py
  python llm_data/build_alpaca_dataset.py --validate

출력:
  data/alpaca/aviation_alpaca_train.jsonl   (~85%)
  data/alpaca/aviation_alpaca_val.jsonl     (~10%)
  data/alpaca/aviation_alpaca_test.jsonl    (~5%)
  data/alpaca/dataset_stats.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

# ── 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
QA_DIR       = PROJECT_ROOT / "data" / "qa"
ATC_CORPUS   = PROJECT_ROOT / "data" / "liveatc" / "atc_corpus.jsonl"
ALPACA_DIR   = PROJECT_ROOT / "data" / "alpaca"
ALPACA_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_PATH   = ALPACA_DIR / "aviation_alpaca_train.jsonl"
VAL_PATH     = ALPACA_DIR / "aviation_alpaca_val.jsonl"
TEST_PATH    = ALPACA_DIR / "aviation_alpaca_test.jsonl"
STATS_PATH   = ALPACA_DIR / "dataset_stats.json"

# ── Split 비율 ─────────────────────────────────────────────────────────
TRAIN_RATIO = 0.85
VAL_RATIO   = 0.10
TEST_RATIO  = 0.05

# ── ATC 코퍼스 → Alpaca 변환 템플릿 ──────────────────────────────────
ATC_INSTRUCTION_TEMPLATES = [
    "다음 ATC 교신 텍스트를 분석하고 관제사가 항공기에 내린 지시 사항을 요약하세요.",
    "다음 항공 교신 내용에서 항공기 콜사인, 지시 고도, 허가 내용을 추출하세요.",
    "아래 ATC 교신을 한국어로 번역하고 핵심 지시 사항을 정리하세요.",
    "다음 관제 교신의 이상 여부를 판단하고 표준 절차와의 차이점을 설명하세요.",
    "아래 ATC 교신에서 사용된 ICAO 표준 절차 구문을 식별하고 설명하세요.",
    "다음 교신 텍스트에서 비정상 상황의 징후가 있는지 분석하세요.",
    "ATC 교신 내용을 기반으로 해당 항공기의 비행 단계(이륙/순항/착륙)를 판단하세요.",
]

QA_INSTRUCTION_OVERRIDE = {
    "regulation_qa": None,   # 원본 유지
    "procedure_qa":  None,
    "emergency_qa":  None,
    "terminology_qa": None,
}


def load_jsonl(path: Path) -> list[dict]:
    """JSONL 파일 로드."""
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def atc_to_alpaca(record: dict) -> dict | None:
    """ATC 코퍼스 레코드 → Alpaca 포맷."""
    text = record.get("text", "").strip()
    if not text or len(text.split()) < 8:
        return None
    instruction = random.choice(ATC_INSTRUCTION_TEMPLATES)
    # 간단한 output 생성 (ATC 코퍼스는 self-supervised로 사용)
    output = (
        f"교신 내용 분석: {text[:200]}{'...' if len(text) > 200 else ''}\n"
        f"주요 내용: 항공 교신 텍스트로, 관제 지시 및 조종사 응답 내용을 포함합니다."
    )
    return {
        "instruction": instruction,
        "input":       text,
        "output":      output,
        "source":      "atc_corpus",
        "type":        "atc_comprehension",
    }


def qa_to_alpaca(record: dict) -> dict | None:
    """QA 레코드 → Alpaca 포맷."""
    q = record.get("question", "").strip()
    a = record.get("answer", "").strip()
    if not q or not a:
        return None
    return {
        "instruction": q,
        "input":       "",
        "output":      a,
        "source":      record.get("source", "qa"),
        "type":        record.get("type", "qa"),
    }


def anomaly_to_alpaca(record: dict) -> dict | None:
    """이상 탐지 NL 레코드 → Alpaca 포맷."""
    inst = record.get("instruction", "").strip()
    inp  = record.get("input", "").strip()
    out  = record.get("output", "").strip()
    if not inst or not out:
        return None
    return {
        "instruction": inst,
        "input":       inp,
        "output":      out,
        "source":      record.get("source", "anomaly"),
        "type":        record.get("type", "anomaly_nl"),
    }


def passenger_to_alpaca(record: dict) -> dict | None:
    """승객 안내문 레코드 → Alpaca 포맷."""
    inst = record.get("instruction", "").strip()
    inp  = record.get("input", "").strip()
    out  = record.get("output", "").strip()
    if not inst or not out:
        return None
    return {
        "instruction": inst,
        "input":       inp,
        "output":      out,
        "source":      record.get("source", "passenger_ann"),
        "type":        "passenger_announcement",
    }


def validate_record(record: dict) -> bool:
    """Alpaca 레코드 유효성 검증."""
    if not isinstance(record.get("instruction"), str):
        return False
    if not isinstance(record.get("input"), str):
        return False
    if not isinstance(record.get("output"), str):
        return False
    if len(record["instruction"].strip()) < 5:
        return False
    if len(record["output"].strip()) < 10:
        return False
    return True


def save_jsonl(records: list[dict], path: Path) -> None:
    """레코드 리스트를 JSONL로 저장."""
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            # 저장 시 source/type 필드 제거 (학습용 최소화)
            out = {
                "instruction": r["instruction"],
                "input":       r["input"],
                "output":      r["output"],
            }
            f.write(json.dumps(out, ensure_ascii=False) + "\n")


def main(args: argparse.Namespace) -> None:
    print("=" * 65)
    print("  SkyOps Intelligence — Alpaca 데이터셋 빌드")
    print("=" * 65)

    all_records: list[dict] = []
    source_counts: dict[str, int] = {}

    # 1. ATC 코퍼스
    atc_raw = load_jsonl(ATC_CORPUS)
    atc_records = [r for raw in atc_raw if (r := atc_to_alpaca(raw)) is not None]
    all_records.extend(atc_records)
    source_counts["atc_corpus"] = len(atc_records)
    print(f"  ATC 코퍼스:      {len(atc_records):>7,}건")

    # 2. QA 통합본
    qa_all = load_jsonl(QA_DIR / "all_qa.jsonl")
    qa_records = [r for raw in qa_all if (r := qa_to_alpaca(raw)) is not None]
    all_records.extend(qa_records)
    source_counts["qa"] = len(qa_records)
    print(f"  QA 데이터:       {len(qa_records):>7,}건")

    # 3. 이상 탐지 NL
    anomaly_raw = load_jsonl(QA_DIR / "anomaly_nl.jsonl")
    anomaly_records = [r for raw in anomaly_raw if (r := anomaly_to_alpaca(raw)) is not None]
    all_records.extend(anomaly_records)
    source_counts["anomaly_nl"] = len(anomaly_records)
    print(f"  이상 탐지 NL:    {len(anomaly_records):>7,}건")

    # 4. 승객 안내문
    pax_raw = load_jsonl(QA_DIR / "passenger_ann.jsonl")
    pax_records = [r for raw in pax_raw if (r := passenger_to_alpaca(raw)) is not None]
    all_records.extend(pax_records)
    source_counts["passenger_ann"] = len(pax_records)
    print(f"  승객 안내문:     {len(pax_records):>7,}건")

    print(f"\n  합계:            {len(all_records):>7,}건")

    if len(all_records) == 0:
        print("\n⚠️  데이터가 없습니다. 이전 단계 스크립트를 먼저 실행하세요:")
        print("  python llm_data/generate_anomaly_nl.py --no-api")
        print("  python llm_data/generate_passenger_ann.py --no-api")
        sys.exit(1)

    # 유효성 검증
    if args.validate:
        valid = [r for r in all_records if validate_record(r)]
        invalid_count = len(all_records) - len(valid)
        print(f"\n  유효성 검증: {invalid_count}건 제거 → {len(valid):,}건 유효")
        all_records = valid

    # 셔플
    random.seed(42)
    random.shuffle(all_records)

    # Train / Val / Test 분할
    n_total = len(all_records)
    n_train = int(n_total * TRAIN_RATIO)
    n_val   = int(n_total * VAL_RATIO)

    train_data = all_records[:n_train]
    val_data   = all_records[n_train:n_train + n_val]
    test_data  = all_records[n_train + n_val:]

    # 저장
    print(f"\n▶ 데이터셋 저장")
    save_jsonl(train_data, TRAIN_PATH)
    save_jsonl(val_data,   VAL_PATH)
    save_jsonl(test_data,  TEST_PATH)

    print(f"  Train: {len(train_data):>7,}건 → {TRAIN_PATH.name}")
    print(f"  Val:   {len(val_data):>7,}건 → {VAL_PATH.name}")
    print(f"  Test:  {len(test_data):>7,}건 → {TEST_PATH.name}")

    # 통계 저장
    type_counts = Counter(r.get("type", "unknown") for r in all_records)
    stats = {
        "total": n_total,
        "train": len(train_data),
        "val":   len(val_data),
        "test":  len(test_data),
        "source_counts": source_counts,
        "type_counts":   dict(type_counts),
        "avg_instruction_len": round(
            sum(len(r["instruction"].split()) for r in all_records) / max(n_total, 1), 1
        ),
        "avg_output_len": round(
            sum(len(r["output"].split()) for r in all_records) / max(n_total, 1), 1
        ),
    }
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Alpaca 데이터셋 빌드 완료!")
    print(f"   총 {n_total:,}건 | Train {len(train_data):,} / Val {len(val_data):,} / Test {len(test_data):,}")
    print(f"   통계: {STATS_PATH}")
    print("\n다음 단계:")
    print("  python llm_data/fine_tune_qlora.py --preflight-only")
    print("  python llm_data/fine_tune_qlora.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alpaca 데이터셋 빌드")
    parser.add_argument("--validate", action="store_true",
                        help="유효성 검증 후 불량 레코드 제거")
    main(parser.parse_args())
