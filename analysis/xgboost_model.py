"""
SkyOps Intelligence — 5주차 XGBoost 모델
==========================================
XGBoost + Optuna HPO + 5-Fold CV + MLflow

실행:
  # 1. 패키지 설치
  pip install -r analysis/requirements_ml.txt

  # 2. (선택) Baseline 먼저 실행
  python analysis/baseline_model.py

  # 3. XGBoost 모델 실행
  python analysis/xgboost_model.py
  python analysis/xgboost_model.py --trials 50    # Optuna 탐색 횟수
  python analysis/xgboost_model.py --no-optuna    # HPO 없이 기본 파라미터로 빠르게

  # 4. MLflow UI 확인
  mlflow ui --backend-store-uri mlruns/

출력:
  data/models/xgboost_best.pkl
  data/results/xgboost_metrics.csv
  data/results/feature_importance.csv
  data/figures/09_feature_importance.png
  data/figures/10_model_comparison.png
"""

from __future__ import annotations

import argparse
import pickle
import sys
import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, StandardScaler

warnings.filterwarnings("ignore")

# ── 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
PROCESSED    = DATA_DIR / "processed"
MODELS_DIR   = DATA_DIR / "models"
RESULTS_DIR  = DATA_DIR / "results"
FIG_DIR      = DATA_DIR / "figures"
for d in (MODELS_DIR, RESULTS_DIR, FIG_DIR):
    d.mkdir(parents=True, exist_ok=True)

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

# XGBoost는 Ordinal Encoding 사용 (OHE 대비 속도·메모리 우수)
def build_xgb_preprocessor() -> ColumnTransformer:
    num_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
    ])
    cat_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("oe",      OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
    ])
    return ColumnTransformer([
        ("num", num_pipe, NUMERIC_FEATURES),
        ("cat", cat_pipe, CATEGORICAL_FEATURES),
    ], remainder="drop")


# ── 데이터 로드 ────────────────────────────────────────────────────────
def load_splits():
    for name in ("train", "val", "test"):
        if not (PROCESSED / f"{name}.csv").exists():
            print(f"❌ data/processed/{name}.csv 없음")
            sys.exit(1)
    train = pd.read_csv(PROCESSED / "train.csv", low_memory=False)
    val   = pd.read_csv(PROCESSED / "val.csv",   low_memory=False)
    test  = pd.read_csv(PROCESSED / "test.csv",  low_memory=False)
    print(f"✅ 데이터 로드: train={len(train):,} / val={len(val):,} / test={len(test):,}")
    return train, val, test


def prepare_xy(df: pd.DataFrame):
    avail_num = [c for c in NUMERIC_FEATURES    if c in df.columns]
    avail_cat = [c for c in CATEGORICAL_FEATURES if c in df.columns]
    X = df[avail_num + avail_cat].copy()
    y = pd.to_numeric(df[TARGET], errors="coerce")
    mask = y.notna()
    return X[mask], y[mask]


# ── 평가 지표 ──────────────────────────────────────────────────────────
def compute_metrics(y_true, y_pred, split: str = "val") -> dict:
    rmse = root_mean_squared_error(y_true, y_pred)
    mae  = mean_absolute_error(y_true, y_pred)
    r2   = r2_score(y_true, y_pred)
    acc  = ((y_true > 15) == (y_pred > 15)).mean()
    return {
        "split": split,
        "rmse":           round(float(rmse), 4),
        "mae":            round(float(mae),  4),
        "r2":             round(float(r2),   4),
        "delay_accuracy": round(float(acc),  4),
    }


def run_manual_xgb_cv(X, y, params: dict, n_splits: int = 5) -> dict:
    """XGBoost 수동 K-Fold CV.

    scikit-learn / xgboost 버전 조합에 따라 `cross_validate()`가
    estimator tag 처리에서 실패할 수 있어, fold 루프를 직접 수행합니다.
    또한 fold별로 전처리를 다시 학습해 데이터 누설을 방지합니다.
    """
    try:
        import xgboost as xgb
    except ImportError:
        print("❌ pip install xgboost")
        sys.exit(1)

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    rmse_scores: list[float] = []
    mae_scores: list[float] = []
    r2_scores: list[float] = []

    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)

    for train_idx, val_idx in kf.split(X, y):
        X_fold_train = X.iloc[train_idx]
        X_fold_val   = X.iloc[val_idx]
        y_fold_train = y.iloc[train_idx]
        y_fold_val   = y.iloc[val_idx]

        preprocessor = build_xgb_preprocessor()
        X_fold_train_prep = preprocessor.fit_transform(X_fold_train)
        X_fold_val_prep   = preprocessor.transform(X_fold_val)

        model = xgb.XGBRegressor(
            **params,
            tree_method="hist",
            eval_metric="rmse",
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
        model.fit(X_fold_train_prep, y_fold_train, verbose=False)

        pred = model.predict(X_fold_val_prep)
        rmse_scores.append(float(root_mean_squared_error(y_fold_val, pred)))
        mae_scores.append(float(mean_absolute_error(y_fold_val, pred)))
        r2_scores.append(float(r2_score(y_fold_val, pred)))

    return {
        "cv_rmse_mean": round(float(np.mean(rmse_scores)), 4),
        "cv_rmse_std":  round(float(np.std(rmse_scores)),  4),
        "cv_mae_mean":  round(float(np.mean(mae_scores)),  4),
        "cv_mae_std":   round(float(np.std(mae_scores)),   4),
        "cv_r2_mean":   round(float(np.mean(r2_scores)),   4),
        "cv_r2_std":    round(float(np.std(r2_scores)),    4),
    }


# ── Optuna HPO ────────────────────────────────────────────────────────
def run_optuna(X_train, y_train, n_trials: int = 30) -> dict:
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except ImportError as e:
        print(f"❌ {e} — pip install optuna xgboost")
        sys.exit(1)

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators":        trial.suggest_int("n_estimators", 200, 1000),
            "max_depth":           trial.suggest_int("max_depth", 4, 10),
            "learning_rate":       trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample":           trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree":    trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight":    trial.suggest_int("min_child_weight", 1, 20),
            "reg_alpha":           trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
            "reg_lambda":          trial.suggest_float("reg_lambda", 1e-4, 10.0, log=True),
        }
        cv_metrics = run_manual_xgb_cv(X_train, y_train, params, n_splits=3)
        return cv_metrics["cv_rmse_mean"]

    print(f"\n🔍 Optuna HPO 시작 ({n_trials}회 탐색)...")
    t0 = time.time()
    study = optuna.create_study(
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=42),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5),
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    best = study.best_params
    print(f"   ✅ 완료: {time.time()-t0:.0f}초 | Best RMSE≈{study.best_value:.2f}분")
    print(f"   Best Params: {best}")
    return best


# ── 5-Fold Cross Validation ───────────────────────────────────────────
def run_cross_validation(X_train, y_train, best_params: dict) -> dict:
    print("\n📊 5-Fold Cross Validation 수행 중...")
    cv_metrics = run_manual_xgb_cv(X_train, y_train, best_params, n_splits=5)
    print(f"  RMSE: {cv_metrics['cv_rmse_mean']:.2f} ± {cv_metrics['cv_rmse_std']:.2f}분")
    print(f"  MAE:  {cv_metrics['cv_mae_mean']:.2f} ± {cv_metrics['cv_mae_std']:.2f}분")
    print(f"  R²:   {cv_metrics['cv_r2_mean']:.4f} ± {cv_metrics['cv_r2_std']:.4f}")
    return cv_metrics


# ── 최종 모델 학습 + MLflow 로깅 ──────────────────────────────────────
def train_final_model(
    X_train, y_train,
    X_val,   y_val,
    X_test,  y_test,
    best_params: dict,
    cv_metrics: dict,
) -> Pipeline:
    try:
        import xgboost as xgb
        import mlflow
        import mlflow.xgboost
    except ImportError as e:
        print(f"❌ {e}")
        sys.exit(1)

    preprocessor = build_xgb_preprocessor()

    model = xgb.XGBRegressor(
        **best_params,
        tree_method="hist",
        eval_metric="rmse",
        early_stopping_rounds=30,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )

    pipeline = Pipeline([("preprocessor", preprocessor), ("model", model)])

    print("\n🚀 최종 모델 학습 중...")
    t0 = time.time()

    # early stopping을 위해 eval_set 직접 지정
    pipeline[:-1].fit(X_train)
    X_train_prep = pipeline[:-1].transform(X_train)
    X_val_prep   = pipeline[:-1].transform(X_val)

    model.fit(
        X_train_prep, y_train,
        eval_set=[(X_val_prep, y_val)],
        verbose=False,
    )
    fit_sec = time.time() - t0

    train_m = compute_metrics(y_train, model.predict(X_train_prep), "train")
    val_m   = compute_metrics(y_val,   model.predict(X_val_prep),   "val")
    X_test_prep = pipeline[:-1].transform(X_test)
    test_m  = compute_metrics(y_test,  model.predict(X_test_prep),  "test")

    print(f"  학습 시간: {fit_sec:.1f}초")
    for split, m in [("Train", train_m), ("Val", val_m), ("Test", test_m)]:
        print(
            f"  [{split:5s}] RMSE={m['rmse']:7.2f}분 | "
            f"MAE={m['mae']:7.2f}분 | R²={m['r2']:.4f} | "
            f"DelayAcc={m['delay_accuracy']:.4f}"
        )

    # MLflow 로깅
    # Windows local paths should be passed as file:// URIs for MLflow.
    mlflow.set_tracking_uri((PROJECT_ROOT / "mlruns").as_uri())
    mlflow.set_experiment("SkyOps-XGBoost")
    with mlflow.start_run(run_name="XGBoost_Optuna_5CV"):
        mlflow.log_params(best_params)
        mlflow.log_params({"fit_sec": fit_sec})
        for k, v in cv_metrics.items():
            mlflow.log_metric(k, v)
        for split_m in (train_m, val_m, test_m):
            pfx = split_m["split"]
            for k, v in split_m.items():
                if k != "split":
                    mlflow.log_metric(f"{pfx}_{k}", v)
        mlflow.xgboost.log_model(model, artifact_path="xgboost_model")
    print("   📊 MLflow 로깅 완료")

    # 모델 저장
    model_path = MODELS_DIR / "xgboost_best.pkl"
    with open(model_path, "wb") as f:
        pickle.dump({"pipeline_preprocessor": pipeline[:-1], "model": model}, f)
    print(f"   💾 모델 저장: {model_path}")

    # 결과 저장
    results = []
    for m in (train_m, val_m, test_m):
        results.append({"model": "XGBoost_Optuna", "fit_sec": fit_sec, **cv_metrics, **m})
    pd.DataFrame(results).to_csv(RESULTS_DIR / "xgboost_metrics.csv", index=False)

    return pipeline, model


# ── Feature Importance 시각화 ─────────────────────────────────────────
def plot_feature_importance(model, top_n: int = 20) -> None:
    try:
        import seaborn as sns
        sns.set_theme(style="whitegrid")
    except ImportError:
        pass

    importances = model.feature_importances_
    # feature 이름 재구성 (num + cat 순서)
    feat_names = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    n = min(len(importances), len(feat_names))
    importance_df = (
        pd.DataFrame({"feature": feat_names[:n], "importance": importances[:n]})
        .sort_values("importance", ascending=False)
        .head(top_n)
    )

    importance_df.to_csv(RESULTS_DIR / "feature_importance.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(
        importance_df["feature"][::-1],
        importance_df["importance"][::-1],
        color="steelblue", edgecolor="white",
    )
    ax.set_xlabel("Feature Importance (gain)")
    ax.set_title(f"XGBoost Top {top_n} Feature Importance", fontweight="bold")
    ax.bar_label(ax.containers[0], fmt="%.4f", padding=2, fontsize=8)

    plt.tight_layout()
    out = FIG_DIR / "09_feature_importance.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"   💾 {out}")


# ── 모델 비교표 시각화 ────────────────────────────────────────────────
def plot_model_comparison() -> None:
    baseline_path = RESULTS_DIR / "baseline_metrics.csv"
    xgb_path      = RESULTS_DIR / "xgboost_metrics.csv"

    if not baseline_path.exists():
        print("   ⚠️  baseline_metrics.csv 없음 — 비교 차트 생략")
        return

    baseline_df = pd.read_csv(baseline_path)
    xgb_df      = pd.read_csv(xgb_path)

    val_b = baseline_df[baseline_df["split"] == "val"][["model", "rmse", "mae", "r2"]].copy()
    val_x = xgb_df[xgb_df["split"] == "val"][["model", "rmse", "mae", "r2"]].copy()
    all_df = pd.concat([val_b, val_x], ignore_index=True).sort_values("rmse")

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    metrics   = ["rmse", "mae", "r2"]
    titles    = ["RMSE (낮을수록 좋음)", "MAE (낮을수록 좋음)", "R² (높을수록 좋음)"]
    colors    = ["#e74c3c" if "XGBoost" in m else "#3498db" for m in all_df["model"]]

    for ax, metric, title in zip(axes, metrics, titles):
        bars = ax.bar(range(len(all_df)), all_df[metric], color=colors, edgecolor="white")
        ax.set_xticks(range(len(all_df)))
        ax.set_xticklabels(all_df["model"], rotation=25, ha="right", fontsize=8)
        ax.set_title(title, fontweight="bold")
        ax.bar_label(bars, fmt="%.3f", padding=2, fontsize=8)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#3498db", label="Baseline"),
        Patch(facecolor="#e74c3c", label="XGBoost (Optuna)"),
    ]
    fig.legend(handles=legend_elements, loc="upper right", fontsize=9)
    plt.suptitle("모델 성능 비교 (Validation Set)", fontsize=13, fontweight="bold")
    plt.tight_layout()

    out = FIG_DIR / "10_model_comparison.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   💾 {out}")


# ── 기본 파라미터 (--no-optuna 옵션) ──────────────────────────────────
DEFAULT_PARAMS = {
    "n_estimators":     500,
    "max_depth":        7,
    "learning_rate":    0.05,
    "subsample":        0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "reg_alpha":        0.1,
    "reg_lambda":       1.0,
}


# ── 진입점 ─────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="SkyOps XGBoost 모델")
    parser.add_argument("--trials",    type=int, default=30,
                        help="Optuna 탐색 횟수 (기본 30)")
    parser.add_argument("--no-optuna", action="store_true",
                        help="Optuna HPO 건너뛰고 기본 파라미터 사용")
    args = parser.parse_args()

    print("=" * 65)
    print("  SkyOps Intelligence — XGBoost 모델")
    print("=" * 65)

    train_df, val_df, test_df = load_splits()
    X_train, y_train = prepare_xy(train_df)
    X_val,   y_val   = prepare_xy(val_df)
    X_test,  y_test  = prepare_xy(test_df)

    # Optuna HPO
    if args.no_optuna:
        print("\n⏩ Optuna 건너뜀 — 기본 파라미터 사용")
        best_params = DEFAULT_PARAMS.copy()
    else:
        best_params = run_optuna(X_train, y_train, n_trials=args.trials)

    # 5-Fold CV
    cv_metrics = run_cross_validation(X_train, y_train, best_params)

    # 최종 학습
    pipeline, model = train_final_model(
        X_train, y_train,
        X_val,   y_val,
        X_test,  y_test,
        best_params,
        cv_metrics,
    )

    # 시각화
    print("\n📊 시각화 저장 중...")
    plot_feature_importance(model)
    plot_model_comparison()

    print("\n✅ XGBoost 모델링 완료!")
    print("   MLflow UI:  mlflow ui --backend-store-uri mlruns/")
    print("   다음 단계: 6주차 — 이상 탐지 AutoEncoder")


if __name__ == "__main__":
    main()
