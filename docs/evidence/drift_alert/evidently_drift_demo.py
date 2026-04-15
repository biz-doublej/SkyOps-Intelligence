"""SkyOps drift alert demo — Evidently + Slack (P8-E · 2026-04-15).

Synthesizes training vs production feature distributions with controlled
drift, runs Evidently DataDriftPreset, captures the resulting report,
and demonstrates the alerting path.

Produces evidence:
  docs/evidence/drift_alert/report.html      # Evidently interactive
  docs/evidence/drift_alert/report.json      # machine-readable
  docs/evidence/drift_alert/alert_payload.json  # would-be Slack webhook

Run:
    python docs/evidence/drift_alert/evidently_drift_demo.py
    python docs/evidence/drift_alert/evidently_drift_demo.py --psi-threshold 0.15

Integrate with monitoring/drift_detector.py for production use.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

EVID_DIR = Path(__file__).resolve().parent
REPORT_HTML = EVID_DIR / "report.html"
REPORT_JSON = EVID_DIR / "report.json"
ALERT_FILE = EVID_DIR / "alert_payload.json"


def synthesize(n: int = 5000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Training (reference) vs production (drifted) feature distributions."""
    rng = np.random.default_rng(42)

    # Reference — nominal training distribution
    ref = pd.DataFrame({
        "dep_hour": rng.integers(0, 24, n),
        "distance_miles": rng.normal(800, 400, n).clip(50, 5000),
        "prev_dep_delay_min": rng.exponential(5, n).clip(0, 120),
        "origin_hourly_departures": rng.normal(25, 10, n).clip(5, 60),
        "carrier_hist_delay": rng.normal(8, 3, n).clip(0, 30),
        "rotation_depth": rng.integers(0, 5, n),
        "is_weekend": rng.choice([0, 1], n, p=[0.71, 0.29]),
    })

    # Production — drift introduced:
    # - hour shifted toward peak (simulating schedule change)
    # - distance heavier right tail (fleet change → more wide-body)
    # - prev_dep_delay higher mean (operational degradation)
    # - hourly_departures lower (fewer operators)
    drifted = pd.DataFrame({
        "dep_hour": np.clip(rng.integers(0, 24, n) + rng.choice([0, 4, 8], n, p=[0.4, 0.4, 0.2]), 0, 23),
        "distance_miles": rng.normal(1200, 600, n).clip(50, 8000),   # drift
        "prev_dep_delay_min": rng.exponential(10, n).clip(0, 180),   # drift
        "origin_hourly_departures": rng.normal(18, 8, n).clip(3, 50),  # drift
        "carrier_hist_delay": rng.normal(9, 3, n).clip(0, 35),        # mild drift
        "rotation_depth": rng.integers(0, 5, n),                      # stable
        "is_weekend": rng.choice([0, 1], n, p=[0.71, 0.29]),          # stable
    })
    return ref, drifted


def run_report(ref: pd.DataFrame, prod: pd.DataFrame) -> dict:
    """Run Evidently DataDrift — degrades to naive PSI if lib unavailable."""
    try:
        from evidently.report import Report  # type: ignore
        from evidently.metric_preset import DataDriftPreset  # type: ignore
        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=ref, current_data=prod)
        report.save_html(str(REPORT_HTML))
        res = report.as_dict()
        with open(REPORT_JSON, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2, default=str)
        return res
    except ImportError:
        # Fallback — manual PSI per column
        print("ℹ️ Evidently 미설치 — naive PSI 로 대체 (`pip install evidently` 권장)")
        metrics = []
        for col in ref.columns:
            psi = _psi(ref[col], prod[col])
            metrics.append({"column": col, "psi": psi, "drift": psi > 0.2})
        drift_rate = sum(1 for m in metrics if m["drift"]) / len(metrics)
        fake_report = {
            "metrics": metrics,
            "dataset_drift": drift_rate > 0.5,
            "drift_share": drift_rate,
            "method": "naive_psi_fallback",
        }
        with open(REPORT_JSON, "w", encoding="utf-8") as f:
            json.dump(fake_report, f, ensure_ascii=False, indent=2)
        REPORT_HTML.write_text(
            "<html><body><h1>Evidently not installed</h1>"
            f"<pre>{json.dumps(fake_report, indent=2)}</pre></body></html>",
            encoding="utf-8",
        )
        return fake_report


def _psi(ref_col: pd.Series, prod_col: pd.Series, n_bins: int = 10) -> float:
    """Population Stability Index."""
    eps = 1e-6
    if ref_col.dtype.kind in "iuf":
        bins = np.quantile(ref_col, np.linspace(0, 1, n_bins + 1))
        bins[0] -= eps; bins[-1] += eps
        ref_counts, _ = np.histogram(ref_col, bins=bins)
        prod_counts, _ = np.histogram(prod_col, bins=bins)
    else:
        categories = pd.concat([ref_col, prod_col]).unique()
        ref_counts = np.array([(ref_col == c).sum() for c in categories])
        prod_counts = np.array([(prod_col == c).sum() for c in categories])
    ref_pct = ref_counts / (ref_counts.sum() + eps) + eps
    prod_pct = prod_counts / (prod_counts.sum() + eps) + eps
    return float(((prod_pct - ref_pct) * np.log(prod_pct / ref_pct)).sum())


def build_alert(report: dict, psi_threshold: float) -> dict:
    """Convert drift report → Slack-compatible alert payload."""
    dataset_drift = report.get("dataset_drift",
                               report.get("metrics", [{}])[0].get("result", {}).get("dataset_drift", False))
    drifted_cols = []
    # Evidently v0.4+ format
    for m in report.get("metrics", []):
        res = m.get("result", m)  # fallback
        for col_info in res.get("drift_by_columns", {}).values() or []:
            if isinstance(col_info, dict) and col_info.get("drift_detected"):
                drifted_cols.append(col_info.get("column_name", "?"))
        # naive fallback shape
        if "column" in m and m.get("drift"):
            drifted_cols.append(m["column"])

    severity = "CRITICAL" if len(drifted_cols) >= 3 else \
               "WARNING" if drifted_cols else "INFO"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "skyops-delay-model",
        "severity": severity,
        "title": f"Feature drift detected ({len(drifted_cols)} columns)",
        "drifted_columns": drifted_cols,
        "psi_threshold": psi_threshold,
        "action_recommended": [
            "Check recent data source changes (ATFM schedule / fleet)",
            "Run `make al-report` to see analyst feedback trend",
            "Consider triggering `analysis/xgboost_model.py --trials 30` retrain",
            "If CRITICAL: pause canary rollout, revert to stable model",
        ],
        "runbook": "docs/runbooks/model_retrain.md",
        "slack_payload": {
            "text": f":warning: *SkyOps drift alert* ({severity})",
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn",
                    "text": f"*{len(drifted_cols)} features drifted*: {', '.join(drifted_cols[:5])}"}},
                {"type": "section", "text": {"type": "mrkdwn",
                    "text": "Runbook: <https://github.com/biz-doublej/SkyOps-Intelligence/blob/dev/docs/runbooks/model_retrain.md|model_retrain.md>"}}
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--psi-threshold", type=float, default=0.2)
    parser.add_argument("--n", type=int, default=5000)
    args = parser.parse_args()

    print("=" * 65)
    print("  SkyOps drift alert demo (P8-E)")
    print("=" * 65)

    ref, prod = synthesize(args.n)
    print(f"📊 reference n={len(ref)}  production n={len(prod)}")

    report = run_report(ref, prod)
    print(f"💾 {REPORT_JSON.relative_to(Path.cwd())}")
    print(f"💾 {REPORT_HTML.relative_to(Path.cwd())}")

    alert = build_alert(report, args.psi_threshold)
    with open(ALERT_FILE, "w", encoding="utf-8") as f:
        json.dump(alert, f, ensure_ascii=False, indent=2)
    print(f"💾 {ALERT_FILE.relative_to(Path.cwd())}")

    print(f"\n🚨 Alert severity: {alert['severity']}")
    print(f"    Drifted columns: {alert['drifted_columns'] or '(none)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
