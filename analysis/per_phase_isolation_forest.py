"""
SkyOps Intelligence — Per-phase Isolation Forest (P5+ · 2026-04-15)
=====================================================================
Strategic Review 3번 병목 — "Phase-aware hierarchical anomaly detection".
단일 IF 모델 대신 **비행 단계별 7개 IF 모델**을 따로 학습. 각 phase의
정상 분포가 다르므로 contamination도 독립적으로 튜닝.

Inputs:
  - data/models/ml_phase_classifier.pkl  (Task 2에서 학습)
  - data/raw/flights.csv                (원본 flight features)

Phases: TAXI, TAKEOFF, CLIMB, CRUISE, DESCENT, APPROACH, LANDING

각 phase별 학습:
  1. synthesize_phase_samples() 로 phase 해당 샘플 생성
  2. IF 학습 (contamination = 0.05 기본)
  3. data/models/isolation_forest_<PHASE>.pkl 저장

Serving 측에서는 predict 시:
  phase = ml_phase_classifier.predict(record)
  if_model = load(f"isolation_forest_{phase}.pkl")
  score = if_model.decision_function(record)

실행:
    python analysis/per_phase_isolation_forest.py --n-samples 50000

출력:
    data/models/isolation_forest_{TAXI,TAKEOFF,CLIMB,CRUISE,DESCENT,APPROACH,LANDING}.pkl
    data/results/per_phase_if_report.json
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = DATA_DIR / "models"
RESULTS_DIR = DATA_DIR / "results"
RAW_CSV = DATA_DIR / "raw" / "flights.csv"

sys.path.insert(0, str(PROJECT_ROOT / "analysis"))
from ml_phase_classifier import synthesize_phase_samples

PHASES = ["TAXI", "TAKEOFF", "CLIMB", "CRUISE", "DESCENT", "APPROACH", "LANDING"]

# Phase별 contamination (도메인 heuristic)
# TAXI는 단순해서 낮게, CRUISE는 anomaly 가능성 중간, APPROACH/LANDING은 주의 요망
PHASE_CONTAMINATION = {
    "TAXI":     0.02,   # 이상률 낮음
    "TAKEOFF":  0.03,
    "CLIMB":    0.04,
    "CRUISE":   0.05,   # 기본
    "DESCENT":  0.04,
    "APPROACH": 0.06,   # 사고 빈발 구간
    "LANDING":  0.06,
}


def main():
    parser = argparse.ArgumentParser(description="Per-phase Isolation Forest training")
    parser.add_argument("--n-samples", type=int, default=50_000,
                        help="Base rows from flights.csv (각 phase당 샘플수와 같음)")
    parser.add_argument("--n-estimators", type=int, default=100)
    args = parser.parse_args()

    print("=" * 65)
    print(f"  Per-phase Isolation Forest (n_samples={args.n_samples:,}/phase)")
    print("=" * 65)

    if not RAW_CSV.exists():
        print(f"❌ {RAW_CSV} 없음")
        sys.exit(1)

    # 1. Load flights
    print("📂 Loading flights.csv...")
    df = pd.read_csv(RAW_CSV, low_memory=False, nrows=args.n_samples)
    print(f"   {len(df):,} rows")

    # 2. Generate phase samples (7 × n_samples)
    print("🔧 Synthesizing phase samples...")
    samples = synthesize_phase_samples(df)
    print(f"   Total: {len(samples):,}")

    feature_cols = ["on_ground", "baro_altitude", "velocity", "vertical_rate",
                    "distance_miles", "air_time_min"]

    # 3. Train 7 models
    report = {
        "phases": {},
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "base_flight_rows": int(len(df)),
    }

    for phase in PHASES:
        phase_rows = samples[samples["_phase"] == phase]
        if len(phase_rows) < 100:
            print(f"⚠️  {phase}: 샘플 부족 ({len(phase_rows)})")
            continue
        X = phase_rows[feature_cols].values
        contam = PHASE_CONTAMINATION[phase]

        print(f"\n🎯 {phase:10s} (n={len(X):>7,}, contamination={contam})...")
        t0 = time.time()
        model = IsolationForest(
            n_estimators=args.n_estimators,
            contamination=contam,
            max_samples="auto",
            random_state=42,
            n_jobs=-1,
            verbose=0,
        )
        model.fit(X)
        fit_sec = time.time() - t0

        # Self-evaluation (on same data — sanity check only)
        pred = model.predict(X)
        anomaly_rate = float((pred == -1).mean())
        scores = model.decision_function(X)
        print(f"   ✅ {fit_sec:.1f}초 | anomaly rate: {anomaly_rate:.3%} | "
              f"mean score: {scores.mean():+.4f} (std {scores.std():.4f})")

        # Save
        out = MODELS_DIR / f"isolation_forest_{phase}.pkl"
        artifact = {
            "model": model,
            "phase": phase,
            "contamination": contam,
            "features": feature_cols,
            "n_estimators": args.n_estimators,
            "n_samples": int(len(X)),
            "fit_time_sec": round(fit_sec, 1),
            "self_anomaly_rate": round(anomaly_rate, 4),
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(out, "wb") as f:
            pickle.dump(artifact, f)

        report["phases"][phase] = {
            "contamination": contam,
            "n_samples": int(len(X)),
            "fit_time_sec": round(fit_sec, 1),
            "self_anomaly_rate": round(anomaly_rate, 4),
            "score_mean": float(round(scores.mean(), 4)),
            "score_std": float(round(scores.std(), 4)),
            "model_path": str(out.relative_to(PROJECT_ROOT)),
        }

    # 4. Summary report
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "per_phase_if_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Report: {report_path}")

    print("\n" + "=" * 65)
    print(f"  ✅ Per-phase IF 학습 완료 ({len(report['phases'])}개 phase 모델)")
    print("=" * 65)


if __name__ == "__main__":
    main()
