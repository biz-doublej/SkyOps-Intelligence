"""
SkyOps Intelligence — 6주차 SHAP Feature Importance 분석
=========================================================
XGBoost 모델의 예측 근거를 SHAP으로 해석합니다.

실행:
  python analysis/shap_analysis.py
  python analysis/shap_analysis.py --samples 2000   # 빠른 샘플 실행

사전 조건:
  python analysis/xgboost_model.py  (또는 --no-optuna 로 빠르게)

출력:
  data/figures/11_shap_summary.png
  data/figures/12_shap_bar.png
  data/figures/13_shap_waterfall_delay.png    (지연 사례 설명)
  data/figures/14_shap_waterfall_ontime.png   (정시 사례 설명)
  data/figures/15_shap_dependence_top3.png    (상위 3개 feature 의존도)
  data/results/shap_feature_importance.csv
  data/results/shap_top10_interpretation.md   (상위 10개 해석 문서)
"""

from __future__ import annotations

import argparse
import pickle
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
PROCESSED    = DATA_DIR / "processed"
MODELS_DIR   = DATA_DIR / "models"
RESULTS_DIR  = DATA_DIR / "results"
FIG_DIR      = DATA_DIR / "figures"
for d in (RESULTS_DIR, FIG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── Feature 정의 (xgboost_model.py 와 동일) ───────────────────────────
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
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "dep_delay_min"

FEATURE_KR = {
    "dep_hour":                  "출발 시간(시)",
    "dep_minute":                "출발 분(분)",
    "dep_dayofweek":             "출발 요일",
    "dep_month":                 "출발 월",
    "dep_dayofyear":             "연중 출발일",
    "is_weekend":                "주말 여부",
    "distance_miles":            "운항 거리(마일)",
    "sched_elapsed_min":         "예정 비행시간",
    "prev_dep_delay_min":        "직전편 출발지연",
    "prev_arr_delay_min":        "직전편 도착지연",
    "is_prev_delayed":           "직전편 지연여부",
    "origin_hourly_departures":  "출발공항 혼잡도",
    "dest_hourly_arrivals":      "도착공항 혼잡도",
    "dep_month_weather_score":   "월별 기상위험도",
    "origin_weather_hist_delay": "출발공항 기상이력",
    "dest_weather_hist_delay":   "도착공항 기상이력",
    "carrier_hist_delay":        "항공사 이력지연",
    "origin_hist_delay":         "출발공항 이력지연",
    "dest_hist_delay":           "도착공항 이력지연",
    "route_hist_delay":          "노선 이력지연",
    "carrier_code":              "항공사 코드",
    "origin":                    "출발공항",
    "dest":                      "도착공항",
}


# ── 모델 & 데이터 로드 ─────────────────────────────────────────────────
def load_model_and_data(samples: int | None = None):
    model_path = MODELS_DIR / "xgboost_best.pkl"
    if not model_path.exists():
        print("❌ XGBoost 모델 없음. 먼저 실행하세요:")
        print("   python analysis/xgboost_model.py --no-optuna")
        sys.exit(1)

    with open(model_path, "rb") as f:
        saved = pickle.load(f)

    preprocessor = saved["pipeline_preprocessor"]
    model        = saved["model"]

    test_df = pd.read_csv(PROCESSED / "test.csv", low_memory=False)
    avail   = [c for c in ALL_FEATURES if c in test_df.columns]
    X_test  = test_df[avail].copy()
    y_test  = pd.to_numeric(test_df[TARGET], errors="coerce")
    mask    = y_test.notna()
    X_test, y_test = X_test[mask], y_test[mask]

    if samples and samples < len(X_test):
        idx    = np.random.RandomState(42).choice(len(X_test), samples, replace=False)
        X_test = X_test.iloc[idx].reset_index(drop=True)
        y_test = y_test.iloc[idx].reset_index(drop=True)

    X_prep = preprocessor.transform(X_test)
    # feature 이름 재구성
    num_names = [c for c in NUMERIC_FEATURES    if c in avail]
    cat_names = [c for c in CATEGORICAL_FEATURES if c in avail]
    feat_names = num_names + cat_names

    print(f"✅ 테스트 데이터: {len(X_test):,}행 | Feature: {len(feat_names)}개")
    return model, preprocessor, X_test, X_prep, y_test, feat_names


# ── SHAP 계산 ──────────────────────────────────────────────────────────
def compute_shap(model, X_prep, feat_names: list[str]):
    try:
        import shap
    except ImportError:
        print("❌ pip install shap")
        sys.exit(1)

    print("\n🔬 SHAP 값 계산 중...")
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_prep)
    base_value  = float(explainer.expected_value)
    print(f"   Base value (평균 예측): {base_value:.2f}분")

    shap_df = pd.DataFrame(shap_values, columns=feat_names)
    return explainer, shap_values, shap_df, base_value


# ── 01. SHAP Summary Plot (bee-swarm) ─────────────────────────────────
def plot_summary(shap_values, X_prep, feat_names: list[str]) -> None:
    try:
        import shap
    except ImportError:
        return

    kr_names = [FEATURE_KR.get(f, f) for f in feat_names]

    fig, ax = plt.subplots(figsize=(10, 9))
    shap.summary_plot(
        shap_values, X_prep,
        feature_names=kr_names,
        show=False, plot_size=None,
        color_bar_label="Feature 값 (정규화)",
    )
    plt.title("SHAP Summary Plot — 출발 지연 예측 Feature 영향도",
              fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()
    out = FIG_DIR / "11_shap_summary.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   💾 {out}")


# ── 02. SHAP Bar Plot (평균 절대값) ───────────────────────────────────
def plot_bar_importance(shap_values, feat_names: list[str], top_n: int = 15) -> pd.DataFrame:
    mean_abs = np.abs(shap_values).mean(axis=0)
    imp_df = (
        pd.DataFrame({"feature": feat_names, "mean_abs_shap": mean_abs})
        .sort_values("mean_abs_shap", ascending=False)
        .head(top_n)
    )
    imp_df["feature_kr"] = imp_df["feature"].map(lambda x: FEATURE_KR.get(x, x))

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(
        imp_df["feature_kr"][::-1],
        imp_df["mean_abs_shap"][::-1],
        color="steelblue", edgecolor="white",
    )
    ax.bar_label(ax.containers[0], fmt="%.3f", padding=3, fontsize=9)
    ax.set_xlabel("평균 |SHAP| 값 (분)")
    ax.set_title(f"SHAP Feature Importance Top {top_n}", fontweight="bold")
    plt.tight_layout()
    out = FIG_DIR / "12_shap_bar.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"   💾 {out}")

    # CSV 저장
    full_imp = (
        pd.DataFrame({"feature": feat_names, "mean_abs_shap": mean_abs})
        .sort_values("mean_abs_shap", ascending=False)
    )
    full_imp["feature_kr"] = full_imp["feature"].map(lambda x: FEATURE_KR.get(x, x))
    out_csv = RESULTS_DIR / "shap_feature_importance.csv"
    full_imp.to_csv(out_csv, index=False)
    print(f"   💾 {out_csv}")
    return imp_df


# ── 03. SHAP Waterfall Plot ────────────────────────────────────────────
def plot_waterfall(
    explainer,
    shap_values,
    X_prep,
    y_test: pd.Series,
    feat_names: list[str],
    base_value: float,
) -> None:
    try:
        import shap
    except ImportError:
        return

    kr_names = [FEATURE_KR.get(f, f) for f in feat_names]

    # 가장 지연이 심한 사례 & 정시 사례 선택
    preds  = explainer.model.predict(X_prep)
    delay_idx  = int(np.argmax(preds))     # 예측 지연 최대
    ontime_idx = int(np.argmin(np.abs(preds)))  # 예측 0분에 가장 가까운

    for idx, label, fname in [
        (delay_idx,  "지연 사례 (최대 예측 지연)", "13_shap_waterfall_delay.png"),
        (ontime_idx, "정시 사례 (예측 지연 ≈ 0분)", "14_shap_waterfall_ontime.png"),
    ]:
        explanation = shap.Explanation(
            values=shap_values[idx],
            base_values=base_value,
            data=X_prep[idx],
            feature_names=kr_names,
        )
        fig, ax = plt.subplots(figsize=(11, 7))
        shap.waterfall_plot(explanation, max_display=15, show=False)
        plt.title(
            f"SHAP Waterfall — {label}\n"
            f"실제: {y_test.iloc[idx]:.0f}분 | 예측: {preds[idx]:.0f}분",
            fontsize=11, fontweight="bold",
        )
        plt.tight_layout()
        out = FIG_DIR / fname
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"   💾 {out}")


# ── 04. SHAP Dependence Plot (상위 3개 Feature) ───────────────────────
def plot_dependence(shap_values, X_prep, feat_names: list[str], top3: list[str]) -> None:
    try:
        import shap
    except ImportError:
        return

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, feat in zip(axes, top3):
        if feat not in feat_names:
            continue
        fi = feat_names.index(feat)
        ax.scatter(
            X_prep[:, fi], shap_values[:, fi],
            c=shap_values[:, fi], cmap="coolwarm",
            alpha=0.3, s=8, linewidths=0,
        )
        ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
        ax.set_xlabel(FEATURE_KR.get(feat, feat))
        ax.set_ylabel("SHAP 값 (분)")
        ax.set_title(f"{FEATURE_KR.get(feat, feat)}\n의존도 플롯", fontweight="bold")

    plt.suptitle("SHAP Dependence Plot — 상위 3개 Feature", fontsize=13, fontweight="bold")
    plt.tight_layout()
    out = FIG_DIR / "15_shap_dependence_top3.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"   💾 {out}")


# ── 05. 상위 10개 Feature 해석 문서 ──────────────────────────────────
def save_interpretation_doc(imp_df: pd.DataFrame, base_value: float) -> None:
    lines = [
        "# SkyOps Intelligence — SHAP Feature 해석 (Top 10)",
        "",
        f"> **Base Value (평균 예측 출발 지연): {base_value:.1f}분**",
        "> SHAP 값은 각 Feature가 이 기준치에서 예측을 얼마나 올리거나 내리는지를 나타냅니다.",
        "",
        "| # | Feature | 한국어명 | 평균 |SHAP| (분) | 해석 |",
        "|---|---------|---------|--------------|------|",
    ]

    interpretations = {
        "prev_dep_delay_min":        "직전 편 출발 지연이 클수록 현재 편도 지연 증가 (Cascade Effect)",
        "prev_arr_delay_min":        "직전 편 도착 지연 → 기체 준비 지연 → 현재 편 출발 지연",
        "is_prev_delayed":           "직전 편이 15분 이상 지연됐으면 현재 편 지연 확률 상승",
        "carrier_hist_delay":        "이력상 지연이 잦은 항공사일수록 예측 지연 증가",
        "origin_hist_delay":         "이력상 지연이 많은 출발 공항에서 출발 시 지연 증가",
        "route_hist_delay":          "특정 노선의 이력 지연이 높을수록 해당 편 지연 예측 증가",
        "dest_hist_delay":           "도착 공항의 이력 지연이 높을수록 지연 전파 가능성 증가",
        "origin_hourly_departures":  "출발 시간대 출발 편수가 많을수록 (혼잡) 지연 증가",
        "dep_hour":                  "저녁 시간대(17~21시) 지연이 많고, 새벽(6시 이전)은 적음",
        "dep_month_weather_score":   "겨울(12·1·2월) 및 여름 폭풍 시즌(6·7월)에 지연 증가",
        "sched_elapsed_min":         "장거리 노선일수록 누적 지연 가능성 증가",
        "distance_miles":            "거리가 멀수록 이후 연결편 지연 파급 효과 증가",
        "origin_weather_hist_delay": "기상 지연 이력이 많은 공항에서 출발 시 지연 위험 증가",
        "dest_weather_hist_delay":   "목적지 공항의 기상 이력 지연이 높으면 접근 지연 가능",
        "carrier_code":              "항공사별 운영 효율 차이 반영 (OE 인코딩)",
    }

    for i, (_, row) in enumerate(imp_df.iterrows(), 1):
        feat = row["feature"]
        kr   = row["feature_kr"]
        shap_val = row["mean_abs_shap"]
        interp = interpretations.get(feat, "추가 분석 필요")
        lines.append(f"| {i:2d} | `{feat}` | {kr} | {shap_val:.3f} | {interp} |")

    lines += [
        "",
        "## 주요 인사이트",
        "",
        "1. **Cascade Delay 효과** — 직전 편 지연(`prev_dep_delay_min`, `prev_arr_delay_min`)이",
        "   가장 강력한 예측 인자입니다. 지연은 체인처럼 전파됩니다.",
        "2. **이력 기반 Feature** — 항공사·공항·노선별 이력 지연 평균이 상위권을 차지합니다.",
        "   이는 구조적 지연 패턴이 존재함을 시사합니다.",
        "3. **혼잡도 효과** — 출발 공항의 시간대별 출발 편수가 많을수록 지연이 증가합니다.",
        "4. **기상 위험** — 직접 기상 데이터 없이도 월별 기상 위험 스코어와",
        "   공항 기상 이력만으로 간접 반영이 가능합니다.",
        "5. **시간대 효과** — 저녁 시간대 지연 누적(ripple effect)이 뚜렷합니다.",
    ]

    out = RESULTS_DIR / "shap_top10_interpretation.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"   💾 {out}")


# ── 메인 ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="SkyOps SHAP 분석")
    parser.add_argument("--samples", type=int, default=5000,
                        help="SHAP 계산에 사용할 샘플 수 (기본 5000)")
    args = parser.parse_args()

    print("=" * 65)
    print("  SkyOps Intelligence — SHAP Feature Importance 분석")
    print("=" * 65)

    model, preprocessor, X_test, X_prep, y_test, feat_names = load_model_and_data(args.samples)
    explainer, shap_values, shap_df, base_value = compute_shap(model, X_prep, feat_names)

    steps = [
        ("11 SHAP Summary Plot (bee-swarm)",   lambda: plot_summary(shap_values, X_prep, feat_names)),
        ("12 SHAP Bar Plot (평균 |SHAP|)",      lambda: plot_bar_importance(shap_values, feat_names)),
        ("13·14 Waterfall (지연/정시 사례)",    lambda: plot_waterfall(explainer, shap_values, X_prep, y_test, feat_names, base_value)),
    ]

    imp_df = None
    print()
    for name, func in steps:
        print(f"▶ {name}")
        result = func()
        if result is not None:
            imp_df = result

    # 상위 3개로 Dependence Plot
    if imp_df is not None:
        top3 = imp_df["feature"].tolist()[:3]
        print("▶ 15 SHAP Dependence Plot (Top 3)")
        plot_dependence(shap_values, X_prep, feat_names, top3)
        print("▶ 상위 10개 Feature 해석 문서 저장")
        save_interpretation_doc(imp_df, base_value)

    print(f"\n✅ SHAP 분석 완료! → {FIG_DIR}")
    print("다음 단계: python analysis/isolation_forest.py")


if __name__ == "__main__":
    main()
