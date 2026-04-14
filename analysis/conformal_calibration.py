"""
SkyOps Intelligence — Conformal Prediction Calibrator
======================================================
P1 · Strategic Review 2번 병목 — uncertainty-aware inference

MAPIE 1.3 SplitConformalRegressor (prefit 모드) 기반 split conformal prediction.
기존에 훈련된 xgboost_best.pkl을 그대로 사용하고, val.csv를 calibration set으로
삼아 non-conformity score의 empirical quantile을 계산한다. 분포 가정 없이
marginal coverage를 보장하는 prediction interval을 제공한다.

실행:
  python analysis/conformal_calibration.py --alpha 0.1   # 90% confidence
  python analysis/conformal_calibration.py --alpha 0.05  # 95% confidence

생성 아티팩트:
  data/models/conformal_calibrator.pkl
    {
        "scr": SplitConformalRegressor (conformalized),
        "alpha": 0.1,
        "confidence_level": 0.9,
        "calibration_samples": 72308,
        "calibration_rmse": 24.60,
        "empirical_coverage": 0.9012,   # on val set (self-test)
        "model_version": "xgboost_best.pkl (sha256 prefix)",
        "calibrated_at": "2026-04-14T...",
    }

검증:
  pickle.load → .predict_interval(X) 호출 가능해야 함
  lower <= point <= upper 성립 확인
"""

from __future__ import annotations

import argparse
import hashlib
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from mapie.regression import SplitConformalRegressor
from sklearn.metrics import root_mean_squared_error

# ── 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
PROCESSED    = DATA_DIR / "processed"
MODELS_DIR   = DATA_DIR / "models"
XGB_PATH     = MODELS_DIR / "xgboost_best.pkl"
OUT_PATH     = MODELS_DIR / "conformal_calibrator.pkl"
OUT_PATH_CQR = MODELS_DIR / "conformal_calibrator_cqr.pkl"  # P4+

# ── 학습된 XGBoost 로드 ──────────────────────────────────────────────
def load_xgb_pipeline() -> tuple:
    if not XGB_PATH.exists():
        print(f"❌ {XGB_PATH} 없음. analysis/xgboost_model.py 먼저 실행.")
        sys.exit(1)
    with open(XGB_PATH, "rb") as f:
        obj = pickle.load(f)
    # xgboost_model.py는 {"pipeline_preprocessor", "model"} dict로 저장
    if isinstance(obj, dict) and "model" in obj:
        return obj.get("pipeline_preprocessor"), obj["model"]
    # fallback — raw model인 경우
    return None, obj


def compute_model_hash() -> str:
    with open(XGB_PATH, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()[:12]
    return h


# ── Validation data 로드 ─────────────────────────────────────────────
def load_val():
    val_path = PROCESSED / "val.csv"
    if not val_path.exists():
        print(f"❌ {val_path} 없음")
        sys.exit(1)
    df = pd.read_csv(val_path, low_memory=False)
    print(f"✅ Calibration set (val.csv): {len(df):,} rows")
    return df


def prepare_xy(df: pd.DataFrame, numeric_features, categorical_features, target):
    avail_num = [c for c in numeric_features    if c in df.columns]
    avail_cat = [c for c in categorical_features if c in df.columns]
    X = df[avail_num + avail_cat].copy()
    y = pd.to_numeric(df[target], errors="coerce")
    mask = y.notna()
    return X[mask], y[mask]


# ── 메인 ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", type=float, default=0.1,
                        help="Miscoverage level (0.1 = 90% confidence, 0.05 = 95%)")
    parser.add_argument("--mode", choices=["split", "cqr"], default="split",
                        help="Calibration mode: 'split' (symmetric abs residual, P1 default) "
                             "or 'cqr' (Conformalized Quantile Regression, asymmetric, P4+)")
    args = parser.parse_args()

    print("="*65)
    print(f"  SkyOps Intelligence — Conformal Calibrator (mode={args.mode}, alpha={args.alpha})")
    print("="*65)

    # 1. XGBoost pipeline 로드
    preprocessor, xgb_model = load_xgb_pipeline()
    if preprocessor is None:
        print("⚠️  저장된 pipeline에 preprocessor가 없음. raw model만 사용.")

    # 2. Feature 목록은 xgboost_model.py에서 import
    sys.path.insert(0, str(PROJECT_ROOT / "analysis"))
    from xgboost_model import NUMERIC_FEATURES, CATEGORICAL_FEATURES, TARGET

    # 3. Val set 로드 및 전처리
    val_df = load_val()
    X_val, y_val = prepare_xy(val_df, NUMERIC_FEATURES, CATEGORICAL_FEATURES, TARGET)
    print(f"   Calibration X shape: {X_val.shape}, y shape: {y_val.shape}")

    # preprocessor 통한 transform
    if preprocessor is not None:
        X_val_prep = preprocessor.transform(X_val)
    else:
        X_val_prep = X_val.values

    # 4. Calibration RMSE (sanity check)
    y_pred_val = xgb_model.predict(X_val_prep)
    cal_rmse = float(root_mean_squared_error(y_val, y_pred_val))
    print(f"   Calibration RMSE: {cal_rmse:.2f} min")

    # 5. MAPIE calibrator (mode에 따라 split 또는 CQR)
    confidence_level = 1 - args.alpha
    t0 = time.time()

    if args.mode == "split":
        print(f"\n🔧 MAPIE SplitConformalRegressor fit (confidence={confidence_level:.2f})...")
        scr = SplitConformalRegressor(
            estimator=xgb_model,
            confidence_level=confidence_level,
            prefit=True,
            conformity_score="absolute",  # |y - y_hat| — 대칭 interval
        )
        scr.conformalize(X_val_prep, y_val.values)
    else:
        # CQR mode — load quantile_lower.pkl / quantile_upper.pkl
        from mapie.regression import ConformalizedQuantileRegressor

        lower_path = MODELS_DIR / "quantile_lower.pkl"
        upper_path = MODELS_DIR / "quantile_upper.pkl"
        for p in (lower_path, upper_path):
            if not p.exists():
                print(f"❌ {p} 없음. 먼저 python analysis/quantile_regression.py --alpha {args.alpha} 실행.")
                sys.exit(1)
        with open(lower_path, "rb") as f:
            q_lower = pickle.load(f)["model"]
        with open(upper_path, "rb") as f:
            q_upper = pickle.load(f)["model"]

        print(f"\n🔧 MAPIE ConformalizedQuantileRegressor fit (confidence={confidence_level:.2f})...")
        # MAPIE 1.3 expects estimator = list [low, high] or [low, high, mean]
        scr = ConformalizedQuantileRegressor(
            estimator=[q_lower, q_upper, xgb_model],
            confidence_level=confidence_level,
            prefit=True,
        )
        scr.conformalize(X_val_prep, y_val.values)

    fit_sec = time.time() - t0
    print(f"   ✅ conformalize 완료: {fit_sec:.1f}초")

    # 7. Self-test: val set 위에서 coverage 확인
    y_pred, y_interval = scr.predict_interval(X_val_prep), None
    # predict_interval returns tuple (pred, interval) or ndarray depending on version
    result = scr.predict_interval(X_val_prep)
    if isinstance(result, tuple):
        y_pred, y_interval = result
    else:
        # shape (n, 2) — [lower, upper]
        y_interval = result
        y_pred = xgb_model.predict(X_val_prep)

    lower = y_interval[:, 0] if y_interval.ndim == 2 else y_interval[:, 0, 0]
    upper = y_interval[:, 1] if y_interval.ndim == 2 else y_interval[:, 1, 0]

    covered = ((y_val.values >= lower) & (y_val.values <= upper)).mean()
    avg_width = float(np.mean(upper - lower))
    print(f"   Empirical coverage (val self-test): {covered:.4f} (target {confidence_level:.2f})")
    print(f"   Average interval width: {avg_width:.2f} min")

    # 8. 저장
    model_hash = compute_model_hash()
    artifact = {
        "scr": scr,
        "mode": args.mode,  # P4+ (2026-04-15) — "split" 또는 "cqr"
        "alpha": args.alpha,
        "confidence_level": confidence_level,
        "calibration_samples": int(len(y_val)),
        "calibration_rmse": round(cal_rmse, 4),
        "empirical_coverage": round(float(covered), 4),
        "average_interval_width_min": round(avg_width, 4),
        "model_version": f"xgboost_best.pkl#{model_hash}",
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
        "mapie_version": "1.3.0",
        "conformity_score": "absolute" if args.mode == "split" else "quantile",
    }

    # P4+ · mode별 다른 파일에 저장 (split 모드는 기존 경로 유지)
    out_path = OUT_PATH_CQR if args.mode == "cqr" else OUT_PATH
    with open(out_path, "wb") as f:
        pickle.dump(artifact, f)

    size_kb = out_path.stat().st_size / 1024
    print(f"\n💾 저장: {out_path} ({size_kb:.1f} KB)")
    print(f"   Mode: {args.mode}")
    print(f"   Model version: {artifact['model_version']}")
    print(f"   Calibrated at: {artifact['calibrated_at']}")
    print("\n✅ Conformal calibration 완료")
    if args.mode == "cqr":
        print("   CQR artifact: data/models/conformal_calibrator_cqr.pkl")
        print("   (serving은 아직 split 사용. cqr 전환은 common/model_store.py 에서 조정)")
    else:
        print("   다음 단계: serving/api.py에서 ModelStore.conformal() 로드")


if __name__ == "__main__":
    main()
