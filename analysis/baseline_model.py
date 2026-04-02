"""
SkyOps Intelligence — 5주차 Baseline 모델
==========================================
LinearRegression / RandomForest 기준치 측정 + MLflow 로깅

실행:
  pip install -r analysis/requirements_ml.txt
  python analysis/baseline_model.py

출력:
  mlruns/                    (MLflow 실험 결과)
  data/models/baseline_lr.pkl
  data/models/baseline_rf.pkl
  data/results/baseline_metrics.csv
"""

from __future__ import annotations

import json
import pickle
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, root_mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer

warnings.filterwarnings("ignore")

# ── 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
PROCESSED    = DATA_DIR / "processed"
MODELS_DIR   = DATA_DIR / "models"
RESULTS_DIR  = DATA_DIR / "results"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Feature 정의 ──────────────────────────────────────────────────────
NUMERIC_FEATURES = [
    "dep_hour", "dep_minute", "dep_dayofweek", "dep_month",
    "dep_dayofyear", "is_weekend",
    "distance_miles", "sched_elapsed_min",
    "prev_dep_delay_min", "prev_arr_delay_min", "is_prev_delayed",
    "origin_hourly_departures", "dest_hourly_arrivals",
    "dep_month_weather_score",
    "origin_weather_hist_delay", "dest_weather_hist_delay",
    "carrier_hist_delay", "origin_hist_delay",
    "dest_hist_delay", "route_hist_delay",
]

CATEGORICAL_FEATURES = ["carrier_code", "origin", "dest"]

TARGET = "dep_delay_min"


# ── 데이터 로드 ────────────────────────────────────────────────────────
def load_splits() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for name in ("train", "val", "test"):
        path = PROCESSED / f"{name}.csv"
        if not path.exists():
            print(f"❌ {path} 없음. python analysis/prepare_dataset.py 실행 후 재시도")
            sys.exit(1)

    train = pd.read_csv(PROCESSED / "train.csv", low_memory=False)
    val   = pd.read_csv(PROCESSED / "val.csv",   low_memory=False)
    test  = pd.read_csv(PROCESSED / "test.csv",  low_memory=False)
    print(f"✅ 데이터 로드: train={len(train):,} / val={len(val):,} / test={len(test):,}")
    return train, val, test


def prepare_xy(df: pd.DataFrame):
    avail_num = [c for c in NUMERIC_FEATURES  if c in df.columns]
    avail_cat = [c for c in CATEGORICAL_FEATURES if c in df.columns]
    X = df[avail_num + avail_cat].copy()
    y = pd.to_numeric(df[TARGET], errors="coerce")
    mask = y.notna()
    return X[mask], y[mask]


# ── 전처리 파이프라인 빌더 ─────────────────────────────────────────────
def build_preprocessor() -> ColumnTransformer:
    num_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
    ])
    cat_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("ohe",     OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    avail_num = NUMERIC_FEATURES   # ColumnTransformer가 실제 데이터 기준으로 처리
    avail_cat = CATEGORICAL_FEATURES
    return ColumnTransformer([
        ("num", num_pipe, avail_num),
        ("cat", cat_pipe, avail_cat),
    ], remainder="drop")


# ── 평가 지표 계산 ─────────────────────────────────────────────────────
def compute_metrics(y_true, y_pred, split: str = "val") -> dict:
    rmse = root_mean_squared_error(y_true, y_pred)
    mae  = mean_absolute_error(y_true, y_pred)
    r2   = r2_score(y_true, y_pred)
    # 이진 분류 지표 (>15분 지연)
    y_bin_true = (y_true > 15).astype(int)
    y_bin_pred = (y_pred > 15).astype(int)
    acc = (y_bin_true == y_bin_pred).mean()
    return {
        "split": split,
        "rmse": round(rmse, 4),
        "mae":  round(mae,  4),
        "r2":   round(r2,   4),
        "delay_accuracy": round(acc, 4),
    }


def print_metrics(name: str, metrics: dict) -> None:
    print(
        f"  [{name:20s}] {metrics['split']:5s} | "
        f"RMSE={metrics['rmse']:7.2f}분 | "
        f"MAE={metrics['mae']:7.2f}분 | "
        f"R²={metrics['r2']:6.4f} | "
        f"DelayAcc={metrics['delay_accuracy']:.4f}"
    )


# ── MLflow 로깅 ───────────────────────────────────────────────────────
def log_to_mlflow(
    run_name: str,
    params: dict,
    train_metrics: dict,
    val_metrics: dict,
    model,
    experiment_name: str = "SkyOps-Baseline",
) -> None:
    try:
        import mlflow
        mlflow.set_tracking_uri((PROJECT_ROOT / "mlruns").as_uri())
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=run_name):
            mlflow.log_params(params)
            for k, v in train_metrics.items():
                if k != "split":
                    mlflow.log_metric(f"train_{k}", v)
            for k, v in val_metrics.items():
                if k != "split":
                    mlflow.log_metric(f"val_{k}", v)
            mlflow.sklearn.log_model(model, artifact_path="model")
        print(f"   📊 MLflow 로깅 완료: {run_name}")
    except Exception as e:
        print(f"   ⚠️  MLflow 로깅 실패 (무시): {e}")


# ── 모델 정의 ─────────────────────────────────────────────────────────
def get_baseline_models() -> list[tuple[str, object, dict]]:
    """(이름, 모델, 파라미터) 튜플 목록"""
    return [
        (
            "DummyMean",
            DummyRegressor(strategy="mean"),
            {"strategy": "mean"},
        ),
        (
            "LinearRegression",
            LinearRegression(n_jobs=-1),
            {"model": "LinearRegression"},
        ),
        (
            "RidgeRegression",
            Ridge(alpha=1.0),
            {"model": "Ridge", "alpha": 1.0},
        ),
        (
            "RandomForest_100",
            RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_leaf=50,
                n_jobs=-1,
                random_state=42,
            ),
            {
                "model": "RandomForest",
                "n_estimators": 100,
                "max_depth": 10,
                "min_samples_leaf": 50,
            },
        ),
    ]


# ── 메인 ──────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 65)
    print("  SkyOps Intelligence — Baseline 모델")
    print("=" * 65)

    train_df, val_df, test_df = load_splits()
    X_train, y_train = prepare_xy(train_df)
    X_val,   y_val   = prepare_xy(val_df)
    X_test,  y_test  = prepare_xy(test_df)

    preprocessor = build_preprocessor()
    all_metrics: list[dict] = []

    for model_name, estimator, params in get_baseline_models():
        print(f"\n▶ {model_name}")
        t0 = time.time()

        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", estimator),
        ])

        # Fit
        pipeline.fit(X_train, y_train)
        fit_sec = time.time() - t0

        # 평가
        train_m = compute_metrics(y_train, pipeline.predict(X_train), "train")
        val_m   = compute_metrics(y_val,   pipeline.predict(X_val),   "val")
        test_m  = compute_metrics(y_test,  pipeline.predict(X_test),  "test")

        print_metrics(model_name, train_m)
        print_metrics(model_name, val_m)
        print_metrics(model_name, test_m)
        print(f"   ⏱  학습 시간: {fit_sec:.1f}초")

        # MLflow
        log_to_mlflow(model_name, params, train_m, val_m, pipeline)

        # 모델 저장
        model_path = MODELS_DIR / f"baseline_{model_name.lower()}.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(pipeline, f)

        # 결과 수집
        for m in (train_m, val_m, test_m):
            all_metrics.append({"model": model_name, "fit_sec": round(fit_sec, 1), **m})

    # 비교표 저장
    results_df = pd.DataFrame(all_metrics)
    out_path = RESULTS_DIR / "baseline_metrics.csv"
    results_df.to_csv(out_path, index=False)

    # 요약 출력
    print("\n" + "=" * 65)
    print("📋 Baseline 성능 비교 (Val 기준)")
    print("=" * 65)
    val_results = results_df[results_df["split"] == "val"].sort_values("rmse")
    print(val_results[["model", "rmse", "mae", "r2", "delay_accuracy", "fit_sec"]].to_string(index=False))
    print(f"\n💾 결과 저장: {out_path}")
    print("다음 단계: python analysis/xgboost_model.py")


if __name__ == "__main__":
    main()
