"""
SkyOps Intelligence — Post-hoc Quantile Regression for CQR (P4+ · 2026-04-15)
=============================================================================
Strategic Review 2번 병목 심화 — P1 Conformal (symmetric abs residual)에서
**Conformalized Quantile Regression**으로 이행하여 asymmetric intervals 확보.

기존 XGBoost point-estimate 모델은 건드리지 않고, low/high quantile을
predicting하는 sklearn GradientBoostingRegressor 두 개를 별도로 학습한다.
이어서 analysis/conformal_calibration.py --mode cqr 가 MAPIE
ConformalizedQuantileRegressor로 래핑·calibrate.

Retrain 없이 경량 sidecar 학습 (2 모델, 각 ~15분 on 337K train sample 기준).

실행:
    python analysis/quantile_regression.py --alpha 0.1

입력:
    data/processed/train.csv (temporal split from prepare_dataset.py)
    xgboost_model.py 의 preprocessor (pipeline_preprocessor)

출력:
    data/models/quantile_lower.pkl
    data/models/quantile_upper.pkl
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
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED = DATA_DIR / "processed"
MODELS_DIR = DATA_DIR / "models"
XGB_PATH = MODELS_DIR / "xgboost_best.pkl"
LOWER_OUT = MODELS_DIR / "quantile_lower.pkl"
UPPER_OUT = MODELS_DIR / "quantile_upper.pkl"


def load_xgb_pipeline():
    if not XGB_PATH.exists():
        print(f"❌ {XGB_PATH} 없음. analysis/xgboost_model.py 먼저 실행.")
        sys.exit(1)
    with open(XGB_PATH, "rb") as f:
        obj = pickle.load(f)
    if isinstance(obj, dict) and "model" in obj:
        return obj.get("pipeline_preprocessor"), obj["model"]
    return None, obj


def load_train(sample_frac: float | None = None):
    path = PROCESSED / "train.csv"
    if not path.exists():
        print(f"❌ {path} 없음")
        sys.exit(1)
    df = pd.read_csv(path, low_memory=False)
    if sample_frac and 0 < sample_frac < 1:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)
    print(f"✅ Train 로드: {len(df):,} rows (sample_frac={sample_frac})")
    return df


def main():
    parser = argparse.ArgumentParser(description="Post-hoc Quantile Regression for CQR")
    parser.add_argument("--alpha", type=float, default=0.1,
                        help="Total miscoverage (0.1 = 90% interval; quantiles at alpha/2 and 1-alpha/2)")
    parser.add_argument("--sample-frac", type=float, default=0.3,
                        help="Train data subsample fraction (default 0.3 for speed; 1.0 for full)")
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=5)
    args = parser.parse_args()

    low_q = args.alpha / 2
    high_q = 1 - args.alpha / 2
    confidence_level = 1 - args.alpha

    print("=" * 65)
    print(f"  Post-hoc Quantile Regression (alpha={args.alpha}, CL={confidence_level:.0%})")
    print(f"  Low quantile: {low_q:.3f}, High quantile: {high_q:.3f}")
    print("=" * 65)

    # 1. Load XGBoost pipeline to reuse preprocessor
    preprocessor, _xgb = load_xgb_pipeline()

    # 2. Load train data + feature names from xgboost_model
    sys.path.insert(0, str(PROJECT_ROOT / "analysis"))
    from xgboost_model import NUMERIC_FEATURES, CATEGORICAL_FEATURES, TARGET

    train_df = load_train(args.sample_frac)

    avail_num = [c for c in NUMERIC_FEATURES if c in train_df.columns]
    avail_cat = [c for c in CATEGORICAL_FEATURES if c in train_df.columns]
    X_train = train_df[avail_num + avail_cat].copy()
    y_train = pd.to_numeric(train_df[TARGET], errors="coerce")
    mask = y_train.notna()
    X_train, y_train = X_train[mask], y_train[mask]

    X_prep = preprocessor.transform(X_train) if preprocessor is not None else X_train.values
    print(f"   X shape: {X_prep.shape}, y shape: {y_train.shape}")

    # 3. Train low quantile regressor
    print(f"\n🔧 Low quantile regressor (q={low_q:.3f}) 학습...")
    t0 = time.time()
    q_low = GradientBoostingRegressor(
        loss="quantile",
        alpha=low_q,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=0.05,
        random_state=42,
        verbose=0,
    )
    q_low.fit(X_prep, y_train)
    low_time = time.time() - t0
    print(f"   ✅ {low_time:.1f}초")

    # 4. Train high quantile regressor
    print(f"\n🔧 High quantile regressor (q={high_q:.3f}) 학습...")
    t0 = time.time()
    q_high = GradientBoostingRegressor(
        loss="quantile",
        alpha=high_q,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=0.05,
        random_state=42,
        verbose=0,
    )
    q_high.fit(X_prep, y_train)
    high_time = time.time() - t0
    print(f"   ✅ {high_time:.1f}초")

    # 5. Sanity check — on train set
    lower_pred = q_low.predict(X_prep)
    upper_pred = q_high.predict(X_prep)
    in_interval = ((y_train.values >= lower_pred) & (y_train.values <= upper_pred)).mean()
    avg_width_train = float(np.mean(upper_pred - lower_pred))
    print(f"\n📊 Train-set coverage (before CQR calibration): {in_interval:.4f} (target {confidence_level:.2f})")
    print(f"   Train-set avg interval width:                   {avg_width_train:.2f} min")

    # 6. Save
    def _save(model, path: Path, label: str, train_time: float):
        artifact = {
            "model": model,
            "quantile": low_q if label == "lower" else high_q,
            "alpha": args.alpha,
            "label": label,
            "n_estimators": args.n_estimators,
            "max_depth": args.max_depth,
            "sample_frac": args.sample_frac,
            "train_time_sec": round(train_time, 1),
            "train_samples": int(len(y_train)),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(path, "wb") as f:
            pickle.dump(artifact, f)
        print(f"   💾 {path}  ({path.stat().st_size / 1024:.0f} KB)")

    print()
    _save(q_low, LOWER_OUT, "lower", low_time)
    _save(q_high, UPPER_OUT, "upper", high_time)

    print("\n" + "=" * 65)
    print("  ✅ Quantile Regression 완료")
    print("  다음 단계: python analysis/conformal_calibration.py --mode cqr")
    print("=" * 65)


if __name__ == "__main__":
    main()
