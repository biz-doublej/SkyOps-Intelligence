"""
SkyOps Intelligence — Base vs Fine-tuned 성능 비교표 생성
두 개의 eval result JSON 을 받아 Markdown + JSON 비교표를 출력한다.

Usage:
    python evaluation/compare_models.py \
        --base    data/eval/results_qwen_base.json \
        --tuned   data/eval/results_qwen_finetuned.json \
        --output  data/eval/comparison_table.md
"""

import argparse
import json
from pathlib import Path


METRICS = ["bleu_1", "bleu_2", "bleu_4", "rouge_l"]
METRIC_LABEL = {
    "bleu_1":  "BLEU-1",
    "bleu_2":  "BLEU-2",
    "bleu_4":  "BLEU-4",
    "rouge_l": "ROUGE-L",
}


def load_summary(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("summary", data)


def delta_str(base_val: float, tuned_val: float) -> str:
    diff = tuned_val - base_val
    pct  = (diff / max(base_val, 1e-9)) * 100
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:.4f} ({sign}{pct:.1f}%)"


def build_comparison(base_path: Path, tuned_path: Path, output_path: Path) -> None:
    base  = load_summary(base_path)
    tuned = load_summary(tuned_path)

    base_tag  = base.get("tag",  base_path.stem)
    tuned_tag = tuned.get("tag", tuned_path.stem)

    rows = []
    for m in METRICS:
        b = base.get(m, 0.0)
        t = tuned.get(m, 0.0)
        rows.append({
            "metric":     METRIC_LABEL[m],
            "base":       b,
            "tuned":      t,
            "delta":      delta_str(b, t),
            "improved":   t >= b,
        })

    # ── Markdown 출력 ────────────────────────────────────────────────────────
    col_base  = max(len(base_tag),  8)
    col_tuned = max(len(tuned_tag), 16)

    header = (f"| {'지표':8s} | {base_tag:{col_base}s} | "
              f"{tuned_tag:{col_tuned}s} | {'변화량':20s} |")
    sep    = f"|{'-'*10}|{'-'*(col_base+2)}|{'-'*(col_tuned+2)}|{'-'*22}|"

    lines = [
        "## Base vs Fine-tuned 성능 비교",
        "",
        f"- **Base model** : {base_tag}  (n={base.get('n_samples','?')})",
        f"- **Fine-tuned** : {tuned_tag}  (n={tuned.get('n_samples','?')})",
        "",
        header, sep,
    ]
    for r in rows:
        flag = "✅" if r["improved"] else "⬇️"
        lines.append(
            f"| {r['metric']:8s} | {r['base']:{col_base}.4f} | "
            f"{r['tuned']:{col_tuned}.4f} | {flag} {r['delta']:18s} |"
        )

    lines += [
        "",
        "### 해석",
        "",
    ]

    improved = [r for r in rows if r["improved"]]
    degraded = [r for r in rows if not r["improved"]]

    if len(improved) == len(rows):
        lines.append("파인튜닝 후 **모든 지표에서 성능이 향상**되었습니다.")
    elif len(improved) > 0:
        imp_names = ", ".join(r["metric"] for r in improved)
        deg_names = ", ".join(r["metric"] for r in degraded)
        lines.append(f"**{imp_names}** 지표는 향상되었으나, **{deg_names}** 는 소폭 하락했습니다.")
    else:
        lines.append("파인튜닝 후 성능 하락이 확인됩니다. 추가 데이터 확보 또는 하이퍼파라미터 조정이 필요합니다.")

    # BLEU-4 향상률 강조
    bleu4_row = next(r for r in rows if r["metric"] == "BLEU-4")
    if bleu4_row["improved"]:
        pct = (bleu4_row["tuned"] - bleu4_row["base"]) / max(bleu4_row["base"], 1e-9) * 100
        lines.append(f"BLEU-4 기준 **{pct:.1f}% 향상** — 항공 도메인 특화 효과 확인.")

    md_text = "\n".join(lines)
    print(md_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_text + "\n")
    print(f"\n=> {output_path}")

    # JSON 버전도 저장
    json_path = output_path.with_suffix(".json")
    comparison = {
        "base_tag":  base_tag,
        "tuned_tag": tuned_tag,
        "metrics":   rows,
        "base_full": base,
        "tuned_full": tuned,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    print(f"=> {json_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base",   required=True,
                        help="베이스 모델 평가 결과 JSON")
    parser.add_argument("--tuned",  required=True,
                        help="파인튜닝 모델 평가 결과 JSON")
    parser.add_argument("--output", default="data/eval/comparison_table.md")
    args = parser.parse_args()

    base = Path(__file__).parent.parent
    build_comparison(
        base_path   = base / args.base,
        tuned_path  = base / args.tuned,
        output_path = base / args.output,
    )
