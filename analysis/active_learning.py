"""
SkyOps Intelligence — Active Learning Feedback Analysis (P3 · 2026-04-14)
==========================================================================
Strategic Review 3번 병목 — analyst feedback loop의 첫 소비자.

`data/analyst_feedback/feedback.jsonl` 을 읽어 다음을 집계:
  - Label 분포 (true_positive / false_positive / uncertain)
  - FP rate (False Positive / (TP + FP))
  - Weekly trend (최근 12주 히스토그램)
  - Labeler별 활동
  - 시사점 → 자동 권고 (Next Actions)

출력:
  data/results/active_learning_report.json
  data/results/active_learning_report.md

실행:
  python analysis/active_learning.py
  python analysis/active_learning.py --since 2026-01-01
  python analysis/active_learning.py --feedback custom/path.jsonl

향후 연결 (P4+):
  - FP rate 높은 anomaly_type → CEP threshold 재튜닝
  - Uncertain 비율 높으면 classifier 개선 작업 우선순위
  - Active learning query strategy (uncertainty sampling)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FEEDBACK_FILE = DATA_DIR / "analyst_feedback" / "feedback.jsonl"
RESULTS_DIR = DATA_DIR / "results"
JSON_OUT = RESULTS_DIR / "active_learning_report.json"
MD_OUT = RESULTS_DIR / "active_learning_report.md"

VALID_LABELS = {"true_positive", "false_positive", "uncertain"}

# 권고 임계값
FP_RATE_WARN = 0.3      # FP rate > 30% → CEP threshold 재튜닝
FP_RATE_CRIT = 0.5      # FP rate > 50% → 즉시 조치
UNCERTAIN_WARN = 0.2    # Uncertain > 20% → classifier 개선 필요


def _parse_datetime(s: str):
    if not s:
        return None
    # ISO 8601 with timezone
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def load_feedback(path: Path) -> list[dict]:
    if not path.exists():
        print(f"⚠️  Feedback 파일 없음: {path}")
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parse 실패 line {i}: {e}")
    return records


def filter_by_date(records: list[dict], since: datetime | None) -> list[dict]:
    if since is None:
        return records
    out = []
    for r in records:
        ts = _parse_datetime(r.get("labeled_at"))
        if ts is None or ts >= since:
            out.append(r)
    return out


def analyze(records: list[dict]) -> dict:
    """Compute aggregate statistics."""
    n = len(records)
    if n == 0:
        return {
            "total": 0,
            "date_range": None,
            "label_distribution": {},
            "fp_rate": None,
            "uncertain_rate": None,
            "weekly_trend": {},
            "top_labelers": [],
            "per_label_by_week": {},
            "recommendations": ["No feedback yet — start labeling via POST /anomaly/feedback"],
        }

    # Label distribution
    labels = [r.get("label", "unknown") for r in records]
    label_dist = Counter(labels)

    # FP rate
    tp = label_dist.get("true_positive", 0)
    fp = label_dist.get("false_positive", 0)
    fp_rate = fp / (tp + fp) if (tp + fp) > 0 else None

    # Uncertain rate
    uncertain = label_dist.get("uncertain", 0)
    uncertain_rate = uncertain / n if n > 0 else None

    # Weekly histogram (ISO week key "YYYY-Www")
    weekly: Counter = Counter()
    per_label_by_week: dict[str, Counter] = defaultdict(Counter)
    dates = []
    for r in records:
        ts = _parse_datetime(r.get("labeled_at"))
        if ts is None:
            continue
        dates.append(ts)
        iso = ts.isocalendar()
        wk = f"{iso.year}-W{iso.week:02d}"
        weekly[wk] += 1
        per_label_by_week[wk][r.get("label", "unknown")] += 1

    # Keep only latest 12 weeks
    weekly_sorted = sorted(weekly.items())[-12:]
    weekly_dict = dict(weekly_sorted)

    # Labelers
    labelers = Counter(r.get("labeled_by", "anonymous") for r in records)
    top_labelers = labelers.most_common(5)

    # Date range
    if dates:
        date_range = {
            "min": min(dates).isoformat(),
            "max": max(dates).isoformat(),
            "span_days": (max(dates) - min(dates)).days,
        }
    else:
        date_range = None

    # Recommendations
    recs = []
    if fp_rate is not None and fp_rate > FP_RATE_CRIT:
        recs.append(
            f"🔴 CRITICAL: FP rate {fp_rate:.1%} > {FP_RATE_CRIT:.0%} "
            f"→ CEP threshold / Isolation Forest contamination 즉시 재튜닝"
        )
    elif fp_rate is not None and fp_rate > FP_RATE_WARN:
        recs.append(
            f"🟡 WARN: FP rate {fp_rate:.1%} > {FP_RATE_WARN:.0%} "
            f"→ anomaly rule threshold 재검토 권장"
        )
    if uncertain_rate is not None and uncertain_rate > UNCERTAIN_WARN:
        recs.append(
            f"🟡 Uncertain rate {uncertain_rate:.1%} > {UNCERTAIN_WARN:.0%} "
            f"→ classifier 개선 (ML phase classifier, Active learning loop) 우선순위 상향"
        )
    if n < 20:
        recs.append(
            f"📊 Feedback 표본 부족 (n={n}) → 최소 50건 이상 수집 후 재분석 권장"
        )
    if not recs:
        recs.append("✅ 현재 피드백 기준 이상 없음 (FP rate/uncertain rate 모두 목표 범위)")

    return {
        "total": n,
        "date_range": date_range,
        "label_distribution": {k: int(v) for k, v in label_dist.items()},
        "fp_rate": round(fp_rate, 4) if fp_rate is not None else None,
        "uncertain_rate": round(uncertain_rate, 4) if uncertain_rate is not None else None,
        "weekly_trend": weekly_dict,
        "top_labelers": [{"labeler": lb, "count": cnt} for lb, cnt in top_labelers],
        "per_label_by_week": {
            wk: dict(counter) for wk, counter in per_label_by_week.items()
        },
        "recommendations": recs,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# SkyOps Active Learning Report",
        "",
        f"- **Generated**: {datetime.now(timezone.utc).isoformat()}",
        f"- **Total feedback**: {report['total']}",
    ]

    if report["date_range"]:
        dr = report["date_range"]
        lines.append(f"- **Date range**: {dr['min']} ~ {dr['max']} ({dr['span_days']}일)")
    else:
        lines.append("- **Date range**: N/A")

    if report["fp_rate"] is not None:
        lines.append(f"- **FP rate**: {report['fp_rate']:.1%}")
    if report["uncertain_rate"] is not None:
        lines.append(f"- **Uncertain rate**: {report['uncertain_rate']:.1%}")
    lines.append("")

    # Label distribution
    lines.append("## Label Distribution")
    if report["label_distribution"]:
        lines.append("")
        lines.append("| Label | Count | % |")
        lines.append("|-------|-------|---|")
        total = report["total"]
        for label, count in sorted(report["label_distribution"].items()):
            pct = count / total * 100 if total > 0 else 0
            lines.append(f"| {label} | {count} | {pct:.1f}% |")
    else:
        lines.append("_(empty)_")
    lines.append("")

    # Weekly trend
    lines.append("## Weekly Trend (최근 12주)")
    if report["weekly_trend"]:
        lines.append("")
        lines.append("| Week | Count |")
        lines.append("|------|-------|")
        for wk, cnt in sorted(report["weekly_trend"].items()):
            lines.append(f"| {wk} | {cnt} |")
    else:
        lines.append("_(no weekly data)_")
    lines.append("")

    # Top labelers
    lines.append("## Top Labelers")
    if report["top_labelers"]:
        lines.append("")
        lines.append("| Labeler | Count |")
        lines.append("|---------|-------|")
        for entry in report["top_labelers"]:
            lines.append(f"| {entry['labeler']} | {entry['count']} |")
    else:
        lines.append("_(no labelers)_")
    lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    for rec in report["recommendations"]:
        lines.append(f"- {rec}")
    lines.append("")

    # Next Steps
    lines += [
        "## 향후 연동 (P4+)",
        "",
        "- **Active Learning query strategy**: uncertainty sampling → 라벨링 요청 queue",
        "- **Per anomaly_type FP rate**: type별 false positive 비율 추적 → CEP threshold 튜닝",
        "- **Monthly Isolation Forest 재학습**: label된 데이터로 contamination 재조정",
        "- **ML phase classifier**: heuristic 대체 (feedback으로 레이블 수집)",
        "",
        "## 참고",
        "",
        "- Feedback 엔드포인트: `POST /anomaly/feedback` (`serving/routers/anomaly.py`)",
        "- 저장 위치: `data/analyst_feedback/feedback.jsonl`",
        "- Strategic Review 3번 병목 · [[2026-04-14 Strategic Review]]",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="SkyOps analyst feedback analysis")
    parser.add_argument("--feedback", type=Path, default=FEEDBACK_FILE,
                        help="Path to feedback.jsonl (default: data/analyst_feedback/feedback.jsonl)")
    parser.add_argument("--since", type=str, default=None,
                        help="Filter records since ISO date (e.g. 2026-01-01)")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    print("=" * 65)
    print("  SkyOps Active Learning — Feedback Analysis")
    print("=" * 65)
    print(f"Input: {args.feedback}")

    records = load_feedback(args.feedback)
    print(f"Loaded {len(records)} feedback records")

    since = None
    if args.since:
        since = _parse_datetime(args.since + "T00:00:00+00:00") or _parse_datetime(args.since)
        if since:
            records = filter_by_date(records, since)
            print(f"Filtered to {len(records)} records since {since.date()}")

    report = analyze(records)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "active_learning_report.json"
    md_path = args.output_dir / "active_learning_report.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(report))

    print(f"\n💾 JSON: {json_path}")
    print(f"💾 Markdown: {md_path}")
    print("\n" + "─" * 65)
    print("Summary")
    print("─" * 65)
    print(f"  Total:           {report['total']}")
    if report["fp_rate"] is not None:
        print(f"  FP rate:         {report['fp_rate']:.1%}")
    if report["uncertain_rate"] is not None:
        print(f"  Uncertain rate:  {report['uncertain_rate']:.1%}")
    print(f"  Label dist:      {report['label_distribution']}")
    print()
    print("Recommendations:")
    for rec in report["recommendations"]:
        print(f"  • {rec}")
    print("=" * 65)


if __name__ == "__main__":
    main()
