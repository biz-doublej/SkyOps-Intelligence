"""
SkyOps Intelligence — 도메인 벤치마크 평가셋 구성
aviation_alpaca_test.jsonl (700건) 에서 4개 유형을 샘플링해
500건 benchmark_eval.jsonl 을 생성한다.

Usage:
    python evaluation/build_benchmark.py
    python evaluation/build_benchmark.py --input data/alpaca/aviation_alpaca_test.jsonl \
                                          --output data/eval/benchmark_eval.jsonl --n 500
"""

import argparse
import json
import random
import re
from pathlib import Path
from collections import defaultdict

SEED = 42

# 유형 감지 키워드 (instruction 기준)
TYPE_PATTERNS = {
    "anomaly":      re.compile(r"(이상|anomaly|탐지|감지|경고|velocity|altitude|fuel)", re.I),
    "announcement": re.compile(r"(안내|announcement|지연|착륙|복행|비상|turbulence|diversion)", re.I),
    "regulation":   re.compile(r"(규정|regulation|FAR|ICAO|FAA|AIM|절차|procedure)", re.I),
    "atc":          re.compile(r"(교신|ATC|관제|callsign|squawk|heading|altitude|clearance)", re.I),
}

TARGET_PER_TYPE = {
    "anomaly":      125,
    "announcement": 125,
    "regulation":   125,
    "atc":          125,
}


def detect_type(item: dict) -> str:
    text = (item.get("instruction", "") + " " + item.get("input", "")).lower()
    for t, pat in TYPE_PATTERNS.items():
        if pat.search(text):
            return t
    return "regulation"  # fallback


def build_benchmark(input_path: Path, output_path: Path, n: int) -> None:
    random.seed(SEED)
    records = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # 유형별 버킷 분류
    buckets: dict[str, list] = defaultdict(list)
    for rec in records:
        buckets[detect_type(rec)].append(rec)

    print(f"총 test 레코드: {len(records)}")
    for t, items in buckets.items():
        print(f"  {t:14s}: {len(items):4d}건")

    # 각 유형에서 샘플링 — 빈 버킷의 잔여 쿼터를 다른 유형에 재배분
    selected = []
    remaining_budget = 0
    first_pass = {}
    for t, target in TARGET_PER_TYPE.items():
        pool = buckets[t]
        k = min(target, len(pool))
        first_pass[t] = (pool, k, target - k)   # (pool, allocated, leftover)
        remaining_budget += target - k

    # 잔여 쿼터를 풀이 남은 유형에 비례 배분
    for t, (pool, k, _) in first_pass.items():
        extra = 0
        if remaining_budget > 0 and len(pool) > k:
            extra = min(remaining_budget, len(pool) - k)
            remaining_budget -= extra
        final_k = k + extra
        selected.extend(random.sample(pool, final_k))
        print(f"  {t:14s}: {final_k}건 선택")

    # n보다 많으면 추가 trim
    random.shuffle(selected)
    selected = selected[:n]

    # benchmark id + type 필드 추가
    output_records = []
    for i, item in enumerate(selected):
        item_type = detect_type(item)
        output_records.append({
            "id":          f"eval_{i:04d}",
            "type":        item_type,
            "instruction": item["instruction"],
            "input":       item.get("input", ""),
            "reference":   item["output"],   # gold answer
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in output_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n=> {output_path}  ({len(output_records)}건 저장)")

    # 통계 파일
    stats = {
        "total":        len(output_records),
        "by_type":      {t: sum(1 for r in output_records if r["type"] == t)
                         for t in TARGET_PER_TYPE},
        "source_file":  str(input_path),
        "seed":         SEED,
    }
    stats_path = output_path.parent / "benchmark_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"=> {stats_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="data/alpaca/aviation_alpaca_test.jsonl")
    parser.add_argument("--output", default="data/eval/benchmark_eval.jsonl")
    parser.add_argument("--n",      type=int, default=500)
    args = parser.parse_args()

    base = Path(__file__).parent.parent
    build_benchmark(
        input_path  = base / args.input,
        output_path = base / args.output,
        n           = args.n,
    )
