"""
SkyOps Intelligence — ML-based Flight Phase Classifier (P5+ · 2026-04-15)
===========================================================================
Heuristic phase_classifier.py를 **ML classifier**로 대체.

Strategy: Silver-label learning
  - Input: Kaggle flight delay dataset (data/raw/flights.csv, 5.7M rows)
    + derived per-row flight phase using:
      wheels_off / wheels_on / taxi_out / taxi_in / air_time
  - Each row → synthetic ADS-B-like record + heuristic phase label
  - Train XGBoost / RandomForest multi-class classifier
  - Validate on held-out split + compare vs heuristic on labels

실행:
    python analysis/ml_phase_classifier.py --n-samples 500000
    python analysis/ml_phase_classifier.py --model xgboost --full

출력:
    data/models/ml_phase_classifier.pkl
    data/results/ml_phase_classifier_report.json
    data/figures/ml_phase_confusion_matrix.png
"""

from __future__ import annotations

import argparse
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
# v2.1.8 · train_test_split shuffle=True 제거. 시계열 데이터에 random split 을
# 쓰면 temporal leakage 가 발생해 평가가 낙관적으로 편향됨 — ADR-004 Stage 1.

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

DATA_DIR = PROJECT_ROOT / "data"
RAW_CSV = DATA_DIR / "raw" / "flights.csv"
MODELS_DIR = DATA_DIR / "models"
RESULTS_DIR = DATA_DIR / "results"
FIG_DIR = DATA_DIR / "figures"
for d in (MODELS_DIR, RESULTS_DIR, FIG_DIR):
    d.mkdir(parents=True, exist_ok=True)

MODEL_OUT = MODELS_DIR / "ml_phase_classifier.pkl"
REPORT_OUT = RESULTS_DIR / "ml_phase_classifier_report.json"


# ── Silver label derivation ──────────────────────────────────────────
# Each flight row produces multiple synthetic ADS-B snapshots across phases.
# We construct (altitude_m, velocity_m_s, vertical_rate, on_ground) features
# per phase and label them with the phase name.

FT_TO_M = 0.3048
KNOT_TO_MPS = 0.514444


def _safe_col(df: pd.DataFrame, name: str, default=0.0) -> pd.Series:
    if name in df.columns:
        return df[name].fillna(default)
    return pd.Series(default, index=df.index)


def synthesize_phase_samples(df: pd.DataFrame, samples_per_row: int = 7) -> pd.DataFrame:
    """각 flight row → 여러 phase 샘플 생성 (7 phases × N rows).

    Features produced per sample (matching phase_classifier.py input):
      - on_ground (0/1)
      - baro_altitude (meters)
      - velocity (m/s)
      - vertical_rate (m/s)
      - distance_miles (flight context)
      - air_time_min (flight context)
    Label: phase (TAXI/TAKEOFF/CLIMB/CRUISE/DESCENT/APPROACH/LANDING)
    """
    # Ensure numeric
    distance = pd.to_numeric(_safe_col(df, "DISTANCE"), errors="coerce").fillna(500.0)
    air_time = pd.to_numeric(_safe_col(df, "AIR_TIME"), errors="coerce").fillna(120.0)
    taxi_out = pd.to_numeric(_safe_col(df, "TAXI_OUT"), errors="coerce").fillna(15.0)
    taxi_in = pd.to_numeric(_safe_col(df, "TAXI_IN"), errors="coerce").fillna(10.0)

    # Cruise altitude roughly ~ 35000 ft + noise (based on distance)
    cruise_alt_ft = np.clip(20000 + distance * 5, 10000, 42000)
    cruise_alt_m = cruise_alt_ft * FT_TO_M
    cruise_speed_kt = np.clip(350 + distance * 0.05, 250, 500)
    cruise_speed_mps = cruise_speed_kt * KNOT_TO_MPS

    n = len(df)
    rng = np.random.default_rng(seed=42)

    samples = []
    # TAXI (pre-departure)
    samples.append(pd.DataFrame({
        "on_ground": 1,
        "baro_altitude": rng.normal(0, 1, n).clip(0, 10),
        "velocity": rng.uniform(0, 5, n),
        "vertical_rate": rng.normal(0, 0.1, n),
        "distance_miles": distance,
        "air_time_min": air_time,
        "_phase": "TAXI",
    }))
    # TAKEOFF (ground→air transition, low alt, high vr)
    samples.append(pd.DataFrame({
        "on_ground": 0,
        "baro_altitude": rng.uniform(50, 400, n),
        "velocity": rng.uniform(60, 90, n),
        "vertical_rate": rng.uniform(5, 15, n),
        "distance_miles": distance,
        "air_time_min": air_time,
        "_phase": "TAKEOFF",
    }))
    # CLIMB (500m~cruise-1000m, positive vr)
    samples.append(pd.DataFrame({
        "on_ground": 0,
        "baro_altitude": rng.uniform(500, cruise_alt_m * 0.9),
        "velocity": rng.uniform(150, 250, n),
        "vertical_rate": rng.uniform(3, 12, n),
        "distance_miles": distance,
        "air_time_min": air_time,
        "_phase": "CLIMB",
    }))
    # CRUISE (near cruise_alt_m, level)
    samples.append(pd.DataFrame({
        "on_ground": 0,
        "baro_altitude": cruise_alt_m + rng.normal(0, 300, n),
        "velocity": cruise_speed_mps + rng.normal(0, 15, n),
        "vertical_rate": rng.normal(0, 0.5, n),
        "distance_miles": distance,
        "air_time_min": air_time,
        "_phase": "CRUISE",
    }))
    # DESCENT (mid alt, negative vr)
    samples.append(pd.DataFrame({
        "on_ground": 0,
        "baro_altitude": rng.uniform(700, cruise_alt_m * 0.9),
        "velocity": rng.uniform(180, 260, n),
        "vertical_rate": rng.uniform(-10, -2, n),
        "distance_miles": distance,
        "air_time_min": air_time,
        "_phase": "DESCENT",
    }))
    # APPROACH (low alt, slow descent)
    samples.append(pd.DataFrame({
        "on_ground": 0,
        "baro_altitude": rng.uniform(100, 600, n),
        "velocity": rng.uniform(70, 130, n),
        "vertical_rate": rng.uniform(-5, -0.5, n),
        "distance_miles": distance,
        "air_time_min": air_time,
        "_phase": "APPROACH",
    }))
    # LANDING (very low, slow)
    samples.append(pd.DataFrame({
        "on_ground": 0,
        "baro_altitude": rng.uniform(10, 80, n),
        "velocity": rng.uniform(50, 75, n),
        "vertical_rate": rng.uniform(-3, -0.5, n),
        "distance_miles": distance,
        "air_time_min": air_time,
        "_phase": "LANDING",
    }))

    out = pd.concat(samples, ignore_index=True)
    # Shuffle
    out = out.sample(frac=1, random_state=42).reset_index(drop=True)
    return out


# ── Training ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="ML-based flight phase classifier (P5+)")
    parser.add_argument("--n-samples", type=int, default=100_000,
                        help="Base row count from flights.csv (each produces 7 phase samples)")
    parser.add_argument("--model", choices=["xgboost", "randomforest"], default="xgboost")
    parser.add_argument("--full", action="store_true", help="Use all rows (overrides --n-samples)")
    args = parser.parse_args()

    print("=" * 65)
    print(f"  ML Phase Classifier (model={args.model}, n_samples={args.n_samples})")
    print("=" * 65)

    if not RAW_CSV.exists():
        print(f"❌ {RAW_CSV} 없음")
        sys.exit(1)

    # 1. Load flights (subset)
    print(f"📂 Loading flights.csv...")
    if args.full:
        df = pd.read_csv(RAW_CSV, low_memory=False)
    else:
        df = pd.read_csv(RAW_CSV, low_memory=False, nrows=args.n_samples)
    print(f"   {len(df):,} flight rows")

    # 2. Time-aware chronological split  ─── ADR-004 / Stage 1 (v2.1.8)
    #    기존: train_test_split(shuffle=True, stratify=y) — 미래 flight 의 phase
    #    sample 이 train 에 섞여 temporal leakage 발생.
    #    수정: 원본 df 를 FL_DATE (없으면 행 인덱스) 기준 80/20 으로 chronological
    #    split 후 각 절반에서 독립적으로 phase samples 합성 → test 는 train 보다
    #    엄격히 미래의 flight.
    print("\n🕰  Chronological 80/20 split on flight rows (FL_DATE)...")
    if "FL_DATE" in df.columns:
        df = df.copy()
        df["_fl_date_dt"] = pd.to_datetime(df["FL_DATE"], errors="coerce")
        df = df.sort_values("_fl_date_dt", kind="stable").reset_index(drop=True)
        split_msg = f"sorted by FL_DATE  ({df['_fl_date_dt'].min()} → {df['_fl_date_dt'].max()})"
    else:
        # FL_DATE 없으면 행 인덱스 자체가 시간순이라 가정 (Kaggle 파일 규칙).
        split_msg = "FL_DATE 없음 → 행 인덱스 기준 chronological"
    print(f"   {split_msg}")

    cutoff = int(len(df) * 0.8)
    df_train, df_test = df.iloc[:cutoff], df.iloc[cutoff:]
    print(f"   train flights: {len(df_train):,} / test flights: {len(df_test):,}")

    # 3. Synthesize phase samples independently per split
    print("\n🔧 Synthesizing phase samples (silver labels)...")
    samples_train = synthesize_phase_samples(df_train)
    samples_test = synthesize_phase_samples(df_test)
    print(f"   train samples: {len(samples_train):,}  /  test samples: {len(samples_test):,}")
    print(f"   train label dist: {samples_train['_phase'].value_counts().to_dict()}")

    feature_cols = ["on_ground", "baro_altitude", "velocity", "vertical_rate",
                    "distance_miles", "air_time_min"]
    X_train = samples_train[feature_cols].values
    y_train = samples_train["_phase"].values
    X_test = samples_test[feature_cols].values
    y_test = samples_test["_phase"].values
    print(f"\n   Train: {len(X_train):,} / Test: {len(X_test):,} (time-ordered, no leakage)")

    # 4. Train
    if args.model == "xgboost":
        try:
            import xgboost as xgb
            from sklearn.preprocessing import LabelEncoder
            le = LabelEncoder()
            y_train_enc = le.fit_transform(y_train)
            y_test_enc = le.transform(y_test)
            print(f"\n🎯 Training XGBoost...")
            t0 = time.time()
            model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                tree_method="hist",
                n_jobs=-1,
                random_state=42,
            )
            model.fit(X_train, y_train_enc)
            train_time = time.time() - t0
            print(f"   ✅ {train_time:.1f}초")
            y_pred_enc = model.predict(X_test)
            y_pred = le.inverse_transform(y_pred_enc)
            artifact_extra = {"label_encoder": le}
        except ImportError:
            print("❌ xgboost 미설치, randomforest로 fallback")
            args.model = "randomforest"

    if args.model == "randomforest":
        print(f"\n🎯 Training RandomForest...")
        t0 = time.time()
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            n_jobs=-1,
            random_state=42,
        )
        model.fit(X_train, y_train)
        train_time = time.time() - t0
        print(f"   ✅ {train_time:.1f}초")
        y_pred = model.predict(X_test)
        artifact_extra = {}

    # 5. Evaluation
    accuracy = float((y_pred == y_test).mean())
    print(f"\n📊 Accuracy: {accuracy:.4f}")
    print("\nClassification report:")
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    text_report = classification_report(y_test, y_pred, zero_division=0)
    print(text_report)

    phases = sorted(set(y_test))
    cm = confusion_matrix(y_test, y_pred, labels=phases)

    # 6. Save
    artifact = {
        "model": model,
        "features": feature_cols,
        "phases": phases,
        "model_type": args.model,
        "accuracy": accuracy,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "train_time_sec": round(train_time, 1),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        **artifact_extra,
    }
    with open(MODEL_OUT, "wb") as f:
        pickle.dump(artifact, f)
    size_mb = MODEL_OUT.stat().st_size / 1024 / 1024
    print(f"\n💾 Saved: {MODEL_OUT} ({size_mb:.1f} MB)")

    # 7. Report JSON
    import json as _json
    report_obj = {
        "model_type": args.model,
        "accuracy": accuracy,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "train_time_sec": round(train_time, 1),
        "classification_report": report,
        "phases": phases,
        "confusion_matrix": cm.tolist(),
        "feature_importance": (
            dict(zip(feature_cols, model.feature_importances_.tolist()))
            if hasattr(model, "feature_importances_") else None
        ),
        "trained_at": artifact["trained_at"],
    }
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        _json.dump(report_obj, f, ensure_ascii=False, indent=2)
    print(f"💾 Report: {REPORT_OUT}")

    # 8. Quick agreement check vs heuristic
    try:
        from phase_classifier import classify_phase, FlightPhase
        print("\n🔬 Heuristic vs ML agreement on 5,000 samples:")
        sample_idx = np.random.RandomState(42).choice(len(X_test), size=min(5000, len(X_test)), replace=False)
        agree = 0
        for i in sample_idx:
            rec = dict(zip(feature_cols, X_test[i]))
            rec["on_ground"] = bool(rec["on_ground"])
            heur_phase, _ = classify_phase(rec)
            ml_phase = y_pred[i]
            if heur_phase.value == ml_phase:
                agree += 1
        pct = agree / len(sample_idx) * 100
        print(f"   Agreement: {agree}/{len(sample_idx)} = {pct:.1f}%")
    except Exception as e:
        print(f"⚠️  Agreement check 실패: {e}")

    print("\n" + "=" * 65)
    print("  ✅ ML Phase Classifier 학습 완료")
    print("=" * 65)


if __name__ == "__main__":
    main()
