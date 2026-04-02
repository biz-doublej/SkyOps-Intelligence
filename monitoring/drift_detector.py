"""
SkyOps Intelligence — EvidentlyAI 데이터 드리프트 감지
Reference data (훈련셋 통계) 와 Current data (최신 수집분) 를 비교한다.

사용 가능한 두 가지 모드:
  1. text_drift  — 텍스트 길이·어휘·도메인 키워드 분포 비교 (경량, 외부 LLM 불필요)
  2. tabular_drift — flight 지연 feature 수치 드리프트 (EvidentlyAI 풀 리포트)

Usage:
    python monitoring/drift_detector.py
    python monitoring/drift_detector.py --mode text   --output data/eval/drift_report.json
    python monitoring/drift_detector.py --mode tabular --output data/eval/drift_report.json
    python monitoring/drift_detector.py --simulate-drift   # 드리프트 강제 시뮬레이션
"""

import argparse
import json
import math
import re
import statistics
from datetime import datetime
from pathlib import Path


# ── 텍스트 통계 계산 ──────────────────────────────────────────────────────────
DOMAIN_KEYWORDS = [
    "이상", "anomaly", "지연", "delay", "교신", "관제", "ATC", "callsign",
    "squawk", "altitude", "heading", "FAR", "ICAO", "turbulence", "복행",
]


def text_stats(jsonl_path: Path) -> dict:
    """instruction+output 텍스트의 통계 지표 계산."""
    lengths, kw_counts, vocab = [], [], set()

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec  = json.loads(line)
            text = rec.get("instruction", "") + " " + rec.get("output", "")
            tokens = text.split()
            lengths.append(len(tokens))
            kw_counts.append(sum(1 for kw in DOMAIN_KEYWORDS if kw.lower() in text.lower()))
            vocab.update(t.lower() for t in tokens)

    if not lengths:
        return {}

    return {
        "n":            len(lengths),
        "len_mean":     round(statistics.mean(lengths), 2),
        "len_stdev":    round(statistics.stdev(lengths) if len(lengths) > 1 else 0, 2),
        "kw_mean":      round(statistics.mean(kw_counts), 4),
        "vocab_size":   len(vocab),
    }


def _js_divergence(p_counts: dict, q_counts: dict) -> float:
    """Jensen-Shannon Divergence (0=동일, 1=완전 다름)."""
    all_keys = set(p_counts) | set(q_counts)
    p_total  = max(sum(p_counts.values()), 1)
    q_total  = max(sum(q_counts.values()), 1)

    def kl(a, m):
        return sum(
            (a.get(k, 0) / p_total) * math.log((a.get(k, 0) / p_total + 1e-12) / (m + 1e-12))
            for k in all_keys
            if a.get(k, 0) > 0
        )

    p_norm = {k: p_counts.get(k, 0) / p_total for k in all_keys}
    q_norm = {k: q_counts.get(k, 0) / q_total for k in all_keys}
    m_norm = {k: (p_norm[k] + q_norm[k]) / 2 for k in all_keys}

    jsd = 0.5 * sum(
        p_norm[k] * math.log(p_norm[k] / m_norm[k] + 1e-12) +
        q_norm[k] * math.log(q_norm[k] / m_norm[k] + 1e-12)
        for k in all_keys
        if p_norm[k] > 0 or q_norm[k] > 0
    )
    return max(0.0, min(1.0, jsd))


def keyword_freq(jsonl_path: Path) -> dict[str, int]:
    freq = {kw: 0 for kw in DOMAIN_KEYWORDS}
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            text = json.loads(line).get("instruction", "") + json.loads(line).get("output", "")
            for kw in DOMAIN_KEYWORDS:
                if kw.lower() in text.lower():
                    freq[kw] += 1
    return freq


# ── 텍스트 드리프트 감지 ──────────────────────────────────────────────────────
def detect_text_drift(ref_path: Path, cur_path: Path,
                      threshold: float = 0.15) -> dict:
    ref_stats = text_stats(ref_path)
    cur_stats = text_stats(cur_path)

    if not cur_stats:
        return {"drift_detected": False, "reason": "current data empty", "details": {}}

    # 길이 분포 변화 (z-score 방식)
    len_z  = abs(cur_stats["len_mean"] - ref_stats["len_mean"]) / max(ref_stats["len_stdev"], 1)

    # 키워드 빈도 JS Divergence
    ref_kw = keyword_freq(ref_path)
    cur_kw = keyword_freq(cur_path)
    jsd    = _js_divergence(ref_kw, cur_kw)

    # 어휘 다양성 변화율
    vocab_drift = abs(cur_stats["vocab_size"] - ref_stats["vocab_size"]) / max(ref_stats["vocab_size"], 1)

    drift_detected = (len_z > 2.0) or (jsd > threshold) or (vocab_drift > 0.3)

    details = {
        "ref_len_mean":   ref_stats["len_mean"],
        "cur_len_mean":   cur_stats["len_mean"],
        "len_z_score":    round(len_z, 3),
        "keyword_jsd":    round(jsd, 4),
        "vocab_drift":    round(vocab_drift, 4),
        "ref_n":          ref_stats["n"],
        "cur_n":          cur_stats["n"],
    }
    signals = []
    if len_z > 2.0:       signals.append(f"텍스트 길이 z-score={len_z:.2f}")
    if jsd > threshold:   signals.append(f"키워드 분포 JSD={jsd:.4f}")
    if vocab_drift > 0.3: signals.append(f"어휘 다양성 변화={vocab_drift:.2%}")

    return {
        "drift_detected": drift_detected,
        "signals":        signals,
        "details":        details,
    }


# ── Tabular drift (EvidentlyAI) ───────────────────────────────────────────────
def detect_tabular_drift(ref_csv: Path, cur_csv: Path, output_path: Path) -> dict:
    """EvidentlyAI DataDriftPreset 사용 (pandas + evidently 필요)."""
    try:
        import pandas as pd
        from evidently.report import Report
        from evidently.metric_preset import DataDriftPreset

        ref_df = pd.read_csv(ref_csv)
        cur_df = pd.read_csv(cur_csv)

        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=ref_df, current_data=cur_df)

        # HTML 리포트 저장
        html_path = output_path.parent / "drift_report.html"
        report.save_html(str(html_path))
        print(f"[drift] HTML 리포트: {html_path}")

        result = report.as_dict()
        share_drifted = result["metrics"][0]["result"]["share_of_drifted_columns"]
        drift_detected = share_drifted > 0.3

        return {
            "drift_detected":       drift_detected,
            "share_drifted_cols":   round(share_drifted, 4),
            "html_report":          str(html_path),
        }

    except ImportError:
        print("[drift] evidently 미설치 → text_drift 모드로 fallback")
        return {}


# ── 시뮬레이션 모드 ────────────────────────────────────────────────────────────
def simulate_drift(train_path: Path, output_path: Path) -> dict:
    """드리프트 강제 시뮬레이션 — 일부 레코드를 변형하여 current 생성."""
    import random, tempfile
    random.seed(99)

    records = []
    with open(train_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # 임의 300건 선택 후 output 길이를 절반으로 줄임 (분포 변형)
    modified = []
    for rec in random.sample(records, min(300, len(records))):
        r = dict(rec)
        r["output"] = rec["output"][:len(rec["output"])//2]
        modified.append(r)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl",
                                    delete=False, encoding="utf-8") as tmp:
        for rec in modified:
            tmp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        tmp_path = Path(tmp.name)

    result = detect_text_drift(train_path, tmp_path, threshold=0.05)
    tmp_path.unlink(missing_ok=True)
    return result


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode",           default="text",
                        choices=["text", "tabular"],
                        help="드리프트 감지 모드")
    parser.add_argument("--ref",            default="data/alpaca/aviation_alpaca_train.jsonl",
                        help="Reference (기준) 데이터 경로")
    parser.add_argument("--current",        default=None,
                        help="Current 데이터 경로 (없으면 ref 의 최신 파일과 비교)")
    parser.add_argument("--ref-csv",        default="data/processed/train_features.csv")
    parser.add_argument("--cur-csv",        default="data/processed/latest_features.csv")
    parser.add_argument("--output",         default="data/eval/drift_report.json")
    parser.add_argument("--threshold",      type=float, default=0.15,
                        help="JSD 드리프트 임계값 (기본 0.15)")
    parser.add_argument("--simulate-drift", action="store_true",
                        help="드리프트 강제 시뮬레이션 모드")
    args = parser.parse_args()

    base        = Path(__file__).parent.parent
    output_path = base / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.simulate_drift:
        print("[drift] 시뮬레이션 모드")
        result = simulate_drift(base / args.ref, output_path)
    elif args.mode == "tabular":
        result = detect_tabular_drift(
            base / args.ref_csv,
            base / args.cur_csv,
            output_path,
        )
        if not result:
            # fallback to text drift
            cur = base / (args.current or args.ref)
            result = detect_text_drift(base / args.ref, cur, args.threshold)
    else:
        cur = base / (args.current or args.ref)
        print(f"[drift] ref={base / args.ref}")
        print(f"[drift] cur={cur}")
        result = detect_text_drift(base / args.ref, cur, args.threshold)

    # 타임스탬프 + 저장
    result["timestamp"] = datetime.utcnow().isoformat() + "Z"
    result["mode"]      = args.mode

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"드리프트 감지: {'⚠️  YES' if result['drift_detected'] else '✅  NO'}")
    if result.get("signals"):
        for s in result["signals"]:
            print(f"  • {s}")
    for k, v in result.get("details", {}).items():
        print(f"  {k:22s}: {v}")
    print(f"\n=> {output_path}")


if __name__ == "__main__":
    main()
