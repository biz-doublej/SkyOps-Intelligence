"""
SkyOps Intelligence — DPO chosen/rejected 페어 1K건 구성
항공 도메인 선호도 데이터(DPO) 를 생성한다.

전략:
  chosen  = 고품질 응답 (원본 Alpaca output)
  rejected = 저품질 응답 (규칙 기반 열화 버전)

열화(degradation) 규칙:
  - anomaly : 수치·단위 삭제, FAA 기준 언급 제거, 경고 어조 약화
  - announcement: 정중체 → 비격식체, 편명·시간 정보 제거
  - regulation  : 조항 번호 제거, 추상적 표현으로 대체
  - atc         : 콜사인 / 주파수 / 숫자 제거

Usage:
    python dpo/build_dpo_pairs.py
    python dpo/build_dpo_pairs.py --n 1000 --output data/dpo/dpo_pairs.jsonl
"""

import argparse
import json
import random
import re
from pathlib import Path

SEED = 42


# ── 열화 규칙 ──────────────────────────────────────────────────────────────────
def _degrade_anomaly(text: str) -> str:
    """수치·단위·기준 코드 삭제, 경고 어조 약화"""
    text = re.sub(r"\d+(\.\d+)?\s*(kt|fpm|m|ft|km|nm|sec|초|분|시간|배)", "일정 수치", text)
    text = re.sub(r"FAA\s+AIM[\s\d\-\.]+", "관련 기준", text)
    text = re.sub(r"\[경고\]|\[WARNING\]|즉시|확인 교신 필요|즉각", "", text)
    text = re.sub(r"표준\s+\S+율[^\s]*", "기준값", text)
    return text.strip()


def _degrade_announcement(text: str) -> str:
    """편명 삭제, 정중 어미 → 구어체, 예상 시간 제거"""
    text = re.sub(r"[A-Z]{2}\d{3,4}[A-Z]?\s*편", "항공편", text)
    text = re.sub(r"약\s*\d+\s*분|예상\s*\d+\s*분", "잠시", text)
    text = text.replace("양해해 주시기 바랍니다", "양해 바랍니다")
    text = text.replace("탑승객 여러분", "승객분들")
    text = re.sub(r"안전한\s+비행을\s+위한[^\.。]*[\.。]?", "", text)
    return text.strip()


def _degrade_regulation(text: str) -> str:
    """조항 번호·기관명 제거, 추상적 표현으로 대체"""
    text = re.sub(r"FAR\s+\d+[\.\d]*|AIM\s+[\d\-\.]+|14\s+CFR\s+[\d\.]+", "관련 규정", text)
    text = re.sub(r"ICAO\s+Doc\s+\d+", "국제 기준", text)
    text = re.sub(r"Section\s+[\d\.]+|§\s*[\d\.]+", "해당 조항", text)
    text = re.sub(r"\d+\s*(feet|ft|knots|kt|nm)\b", "해당 수치", text, flags=re.I)
    return text.strip()


def _degrade_atc(text: str) -> str:
    """콜사인·주파수·고도 정보 제거"""
    text = re.sub(r"[A-Z]{2,3}\d{3,4}", "항공기", text)          # callsign
    text = re.sub(r"\d{3}\.\d{1,3}\s*(MHz|mhz)?", "주파수", text)  # freq
    text = re.sub(r"FL\s*\d{2,3}|flight\s+level\s+\d+", "순항고도", text, flags=re.I)
    text = re.sub(r"\d{3,5}\s*(feet|ft)\b", "해당 고도", text, flags=re.I)
    text = re.sub(r"squawk\s+\d{4}", "스쿼크 코드", text, flags=re.I)
    return text.strip()


DEGRADE_FN = {
    "anomaly":      _degrade_anomaly,
    "announcement": _degrade_announcement,
    "regulation":   _degrade_regulation,
    "atc":          _degrade_atc,
}

TYPE_PAT = {
    "anomaly":      re.compile(r"(이상|anomaly|탐지|경고|velocity|altitude|fuel)", re.I),
    "announcement": re.compile(r"(안내|announcement|지연|복행|비상|turbulence)", re.I),
    "regulation":   re.compile(r"(규정|regulation|FAR|ICAO|FAA|AIM|절차)", re.I),
    "atc":          re.compile(r"(교신|ATC|관제|callsign|squawk|heading)", re.I),
}


def detect_type(item: dict) -> str:
    text = (item.get("instruction", "") + " " + item.get("input", "")).lower()
    for t, p in TYPE_PAT.items():
        if p.search(text):
            return t
    return "regulation"


def degrade(text: str, dtype: str) -> str:
    fn = DEGRADE_FN.get(dtype, _degrade_regulation)
    degraded = fn(text)
    # 최소한 원본과 달라야 함 — 변화 없으면 마지막 문장 제거
    if degraded == text or len(degraded) > len(text) * 0.95:
        sentences = re.split(r'(?<=[.。!?])\s+', degraded)
        degraded = " ".join(sentences[:-1]) if len(sentences) > 1 else degraded[:len(degraded)//2]
    return degraded.strip() or "응답을 생성할 수 없습니다."


# ── 메인 ──────────────────────────────────────────────────────────────────────
def build_dpo_pairs(train_path: Path, output_path: Path, n: int) -> None:
    random.seed(SEED)

    records = []
    with open(train_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"학습셋 총 레코드: {len(records)}")
    # output 이 충분히 긴 것만 사용 (20자 이상)
    records = [r for r in records if len(r.get("output", "")) >= 20]
    print(f"  길이 필터 후: {len(records)}")

    # n 건 샘플 (학습셋 초과 방지)
    k = min(n, len(records))
    sampled = random.sample(records, k)

    pairs = []
    for rec in sampled:
        dtype   = detect_type(rec)
        chosen  = rec["output"]
        rejected = degrade(chosen, dtype)
        pairs.append({
            "prompt":   f"### Instruction:\n{rec['instruction']}\n"
                        + (f"### Input:\n{rec['input']}\n" if rec.get("input") else "")
                        + "### Response:\n",
            "chosen":   chosen,
            "rejected": rejected,
            "type":     dtype,
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\n=> {output_path}  ({len(pairs)}건)")

    # 샘플 출력
    print("\n[샘플 페어 #0]")
    ex = pairs[0]
    print(f"  type    : {ex['type']}")
    print(f"  chosen  : {ex['chosen'][:80]}...")
    print(f"  rejected: {ex['rejected'][:80]}...")

    # 통계
    type_cnt = {}
    for p in pairs:
        type_cnt[p["type"]] = type_cnt.get(p["type"], 0) + 1
    print("\n유형 분포:")
    for t, c in sorted(type_cnt.items()):
        print(f"  {t:14s}: {c}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="data/alpaca/aviation_alpaca_train.jsonl")
    parser.add_argument("--output", default="data/dpo/dpo_pairs.jsonl")
    parser.add_argument("--n",      type=int, default=1000)
    args = parser.parse_args()

    base = Path(__file__).parent.parent
    build_dpo_pairs(
        train_path  = base / args.input,
        output_path = base / args.output,
        n           = args.n,
    )
