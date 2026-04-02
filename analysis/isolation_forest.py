"""
SkyOps Intelligence — 6주차 Isolation Forest 이상 탐지
=======================================================
비지도 학습 기반 항공편 이상 탐지 + CEP 룰 앙상블

실행:
  python analysis/isolation_forest.py                  # 기본 (오프라인 배치)
  python analysis/isolation_forest.py --stream          # Redis 스트리밍 시뮬레이션
  python analysis/isolation_forest.py --contamination 0.03
  python analysis/isolation_forest.py --samples 50000  # 빠른 테스트

사전 조건:
  python analysis/prepare_dataset.py  (data/processed/ 필요)

출력:
  data/models/isolation_forest.pkl
  data/figures/16_if_anomaly_score_dist.png  (이상 점수 분포)
  data/figures/17_if_precision_recall.png    (임계값 튜닝 곡선)
  data/figures/18_if_feature_scatter.png     (이상/정상 산점도)
  data/figures/19_if_cep_ensemble.png        (CEP 앙상블 결과)
  data/results/if_anomaly_report.csv         (이상 항공편 목록)
  data/results/if_threshold_metrics.csv      (임계값별 P/R/F1)
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)

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

# ── 이상 탐지용 Feature 선택 ──────────────────────────────────────────
# 연속형 수치 feature 중 이상 징후를 잘 반영하는 변수만 사용
IF_FEATURES = [
    "dep_hour", "dep_dayofweek",
    "distance_miles", "sched_elapsed_min",
    "prev_dep_delay_min", "prev_arr_delay_min", "is_prev_delayed",
    "origin_hourly_departures", "dest_hourly_arrivals",
    "dep_month_weather_score",
    "origin_weather_hist_delay", "dest_weather_hist_delay",
    "carrier_hist_delay", "origin_hist_delay",
    "dest_hist_delay", "route_hist_delay",
]

TARGET = "dep_delay_min"

# 이상 판정 기준: 실제 15분 초과 지연 = 레이블 1 (평가용)
DELAY_THRESHOLD_MIN = 15

# CEP 룰 앙상블 가중치
CEP_WEIGHT = 0.4   # CEP 룰 기여도
IF_WEIGHT  = 0.6   # Isolation Forest 기여도


# ── 데이터 로드 ────────────────────────────────────────────────────────
def load_data(samples: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """train.csv, test.csv 로드. samples: 테스트용 행 수 제한."""
    for name in ("train", "test"):
        p = PROCESSED / f"{name}.csv"
        if not p.exists():
            print(f"❌ {p} 없음. python analysis/prepare_dataset.py 실행 후 재시도")
            sys.exit(1)

    train = pd.read_csv(PROCESSED / "train.csv", low_memory=False)
    test  = pd.read_csv(PROCESSED / "test.csv",  low_memory=False)

    if samples:
        train = train.sample(min(samples, len(train)), random_state=42)
        test  = test.sample(min(samples // 4, len(test)),  random_state=42)

    print(f"✅ 데이터 로드: train={len(train):,} / test={len(test):,}")
    return train, test


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series | None]:
    """Feature 추출 + 레이블 생성."""
    avail = [c for c in IF_FEATURES if c in df.columns]
    X = df[avail].copy()
    y = None
    if TARGET in df.columns:
        delay = pd.to_numeric(df[TARGET], errors="coerce")
        y = (delay > DELAY_THRESHOLD_MIN).astype(int)  # 1=이상(지연), 0=정상
    return X, y


# ── Isolation Forest 학습 ─────────────────────────────────────────────
def build_pipeline(contamination: float) -> Pipeline:
    """전처리 + IsolationForest 파이프라인 구성."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
        ("model",   IsolationForest(
            contamination=contamination,
            n_estimators=200,
            max_samples="auto",
            max_features=1.0,
            bootstrap=False,
            n_jobs=-1,
            random_state=42,
        )),
    ])


def train_model(X_train: pd.DataFrame, contamination: float) -> Pipeline:
    print(f"\n▶ Isolation Forest 학습 (contamination={contamination})")
    t0 = time.time()
    pipe = build_pipeline(contamination)
    pipe.fit(X_train)
    elapsed = time.time() - t0
    print(f"   ✅ 학습 완료 — {elapsed:.1f}초, 샘플 {len(X_train):,}건")
    return pipe


# ── 이상 점수 계산 ────────────────────────────────────────────────────
def get_scores_and_labels(pipe: Pipeline, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    score_samples() → 음수 anomaly score (낮을수록 이상).
    decision_function() → 양/음 경계 (음수 = 이상).
    predict() → -1 (이상) / 1 (정상).
    """
    scores   = pipe.score_samples(X)         # 낮을수록 이상
    pred_raw = pipe.predict(X)               # -1 or 1
    pred_bin = (pred_raw == -1).astype(int)  # 1=이상, 0=정상
    return scores, pred_bin


# ── 임계값 튜닝 ───────────────────────────────────────────────────────
def tune_threshold(
    scores: np.ndarray,
    y_true: np.ndarray,
    percentiles: np.ndarray | None = None,
) -> pd.DataFrame:
    """
    다양한 score 임계값에서 Precision / Recall / F1 계산.
    (임계값 이하 점수 → 이상으로 판정)
    """
    if percentiles is None:
        percentiles = np.arange(1, 20)  # 1%~19% 오염률 범위

    rows = []
    for p in percentiles:
        thresh = np.percentile(scores, p)
        pred   = (scores <= thresh).astype(int)
        prec   = precision_score(y_true, pred, zero_division=0)
        rec    = recall_score(y_true, pred, zero_division=0)
        f1     = f1_score(y_true, pred, zero_division=0)
        rows.append({
            "percentile": p,
            "threshold":  round(thresh, 6),
            "precision":  round(prec, 4),
            "recall":     round(rec, 4),
            "f1":         round(f1, 4),
            "n_detected": int(pred.sum()),
        })

    df = pd.DataFrame(rows)
    best = df.loc[df["f1"].idxmax()]
    print(f"\n📐 최적 임계값 (F1 기준):")
    print(f"   Percentile={best['percentile']:.0f}%  "
          f"Threshold={best['threshold']:.4f}  "
          f"Precision={best['precision']:.4f}  "
          f"Recall={best['recall']:.4f}  "
          f"F1={best['f1']:.4f}")
    return df


# ── CEP 룰 기반 이상 스코어 ──────────────────────────────────────────
def cep_anomaly_score(df: pd.DataFrame) -> np.ndarray:
    """
    항공편 지연 데이터에서 CEP 룰을 근사 적용해 0~1 스코어를 반환합니다.

    실제 실시간 환경에서는 flink_processor.py + cep_rules.py 가 처리하지만,
    배치 평가에서는 아래 대리 룰(surrogate rules)을 사용합니다:

    Rule 1 (연쇄 지연) — prev_dep_delay_min > 30분
    Rule 2 (기상 고위험) — dep_month_weather_score > 0.7
    Rule 3 (경로 혼잡)   — origin_hourly_departures > 90th percentile
    """
    scores = np.zeros(len(df))

    if "prev_dep_delay_min" in df.columns:
        prev_delay = pd.to_numeric(df["prev_dep_delay_min"], errors="coerce").fillna(0)
        scores += (prev_delay > 30).astype(float) * 0.5

    if "dep_month_weather_score" in df.columns:
        weather = pd.to_numeric(df["dep_month_weather_score"], errors="coerce").fillna(0)
        scores += (weather > weather.quantile(0.90)).astype(float) * 0.3

    if "origin_hourly_departures" in df.columns:
        congestion = pd.to_numeric(df["origin_hourly_departures"], errors="coerce").fillna(0)
        scores += (congestion > congestion.quantile(0.90)).astype(float) * 0.2

    return np.clip(scores, 0, 1)


def ensemble_score(
    if_scores: np.ndarray,
    cep_scores: np.ndarray,
) -> np.ndarray:
    """
    IF 정규화 점수 + CEP 스코어를 가중 평균하여 최종 앙상블 점수 계산.
    최종 점수: 높을수록 이상 (0~1 범위).
    """
    # IF score: 낮을수록 이상 → 반전 후 0~1 정규화
    if_min, if_max = if_scores.min(), if_scores.max()
    if_norm = 1.0 - (if_scores - if_min) / (if_max - if_min + 1e-9)
    return IF_WEIGHT * if_norm + CEP_WEIGHT * cep_scores


# ── 시각화 ────────────────────────────────────────────────────────────
def plot_score_distribution(
    if_scores: np.ndarray,
    y_true: np.ndarray,
    out_path: Path,
) -> None:
    """그림 16: IF 이상 점수 분포 (정상 vs 지연)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Isolation Forest — Anomaly Score Distribution", fontsize=14, y=1.01)

    # 전체 분포
    ax = axes[0]
    ax.hist(if_scores, bins=60, color="#4A90D9", alpha=0.8, edgecolor="white", linewidth=0.4)
    p5 = np.percentile(if_scores, 5)
    ax.axvline(p5, color="#E74C3C", linestyle="--", linewidth=1.5, label=f"5th pct ({p5:.3f})")
    ax.set_xlabel("Anomaly Score (낮을수록 이상)")
    ax.set_ylabel("Count")
    ax.set_title("전체 분포")
    ax.legend(fontsize=9)

    # 레이블 별 분포
    ax2 = axes[1]
    for label, color, name in [(0, "#2ECC71", "정상"), (1, "#E74C3C", "지연(>15분)")]:
        ax2.hist(if_scores[y_true == label], bins=60, alpha=0.65,
                 color=color, edgecolor="white", linewidth=0.3, label=name)
    ax2.set_xlabel("Anomaly Score")
    ax2.set_ylabel("Count")
    ax2.set_title("정상 vs 지연 분포 비교")
    ax2.legend(fontsize=9)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"   💾 {out_path.name}")


def plot_precision_recall(thresh_df: pd.DataFrame, out_path: Path) -> None:
    """그림 17: 임계값 튜닝 — Precision / Recall / F1 곡선."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(thresh_df["percentile"], thresh_df["precision"],
            marker="o", markersize=4, label="Precision", color="#3498DB")
    ax.plot(thresh_df["percentile"], thresh_df["recall"],
            marker="s", markersize=4, label="Recall",    color="#E74C3C")
    ax.plot(thresh_df["percentile"], thresh_df["f1"],
            marker="^", markersize=4, label="F1 Score",  color="#2ECC71", linewidth=2)

    best_idx = thresh_df["f1"].idxmax()
    best_p   = thresh_df.loc[best_idx, "percentile"]
    best_f1  = thresh_df.loc[best_idx, "f1"]
    ax.axvline(best_p, linestyle="--", color="gray", linewidth=1.2,
               label=f"Best F1 @ {best_p:.0f}%")
    ax.annotate(f"F1={best_f1:.3f}", xy=(best_p, best_f1),
                xytext=(best_p + 0.5, best_f1 - 0.04), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="gray"))

    ax.set_xlabel("Contamination Percentile (%)")
    ax.set_ylabel("Score")
    ax.set_title("Isolation Forest — Threshold Tuning (Precision / Recall / F1)")
    ax.legend(fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"   💾 {out_path.name}")


def plot_feature_scatter(
    X: pd.DataFrame,
    if_scores: np.ndarray,
    pred_bin: np.ndarray,
    out_path: Path,
) -> None:
    """그림 18: 주요 feature 2D 산점도 — 이상/정상 색상 구분."""
    feat_x = "prev_dep_delay_min"
    feat_y = "dep_month_weather_score"
    avail  = [c for c in [feat_x, feat_y] if c in X.columns]
    if len(avail) < 2:
        feat_x, feat_y = X.columns[0], X.columns[1]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Isolation Forest — Feature Scatter (정상 vs 이상)", fontsize=13)

    for ax, (fx, fy) in zip(
        axes,
        [(feat_x, feat_y), ("carrier_hist_delay", "route_hist_delay")],
    ):
        fx_ = fx if fx in X.columns else X.columns[0]
        fy_ = fy if fy in X.columns else X.columns[1]

        xv = pd.to_numeric(X[fx_], errors="coerce").fillna(0).values
        yv = pd.to_numeric(X[fy_], errors="coerce").fillna(0).values

        normal  = pred_bin == 0
        anomaly = pred_bin == 1

        ax.scatter(xv[normal],  yv[normal],  s=6,  alpha=0.3, color="#4A90D9",
                   label=f"정상 ({normal.sum():,})")
        ax.scatter(xv[anomaly], yv[anomaly], s=10, alpha=0.7, color="#E74C3C",
                   marker="x", label=f"이상 ({anomaly.sum():,})")
        ax.set_xlabel(fx_)
        ax.set_ylabel(fy_)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"   💾 {out_path.name}")


def plot_ensemble_result(
    if_scores:   np.ndarray,
    cep_scores:  np.ndarray,
    ens_scores:  np.ndarray,
    y_true:      np.ndarray,
    out_path:    Path,
) -> None:
    """그림 19: CEP + IF 앙상블 점수 분포 및 혼동 행렬."""
    ens_thresh = np.percentile(ens_scores, 85)  # 상위 15% = 이상
    ens_pred   = (ens_scores >= ens_thresh).astype(int)

    fig = plt.figure(figsize=(16, 5))
    gs  = gridspec.GridSpec(1, 3, figure=fig, wspace=0.35)

    # ① 앙상블 점수 분포
    ax1 = fig.add_subplot(gs[0])
    for label, color, name in [(0, "#2ECC71", "정상"), (1, "#E74C3C", "지연(>15분)")]:
        ax1.hist(ens_scores[y_true == label], bins=50, alpha=0.65,
                 color=color, edgecolor="white", linewidth=0.3, label=name)
    ax1.axvline(ens_thresh, linestyle="--", color="gray", linewidth=1.5,
                label=f"임계값 ({ens_thresh:.3f})")
    ax1.set_xlabel("Ensemble Score")
    ax1.set_ylabel("Count")
    ax1.set_title("앙상블 점수 분포")
    ax1.legend(fontsize=8)

    # ② CEP vs IF 산점도
    ax2 = fig.add_subplot(gs[1])
    ax2.scatter(cep_scores[y_true == 0], if_scores[y_true == 0],
                s=5, alpha=0.2, color="#4A90D9", label="정상")
    ax2.scatter(cep_scores[y_true == 1], if_scores[y_true == 1],
                s=5, alpha=0.4, color="#E74C3C", label="지연", marker="x")
    ax2.set_xlabel("CEP Score")
    ax2.set_ylabel("IF Score (raw, 낮을수록 이상)")
    ax2.set_title("CEP vs IF 점수 비교")
    ax2.legend(fontsize=8)

    # ③ 혼동 행렬
    ax3 = fig.add_subplot(gs[2])
    cm  = confusion_matrix(y_true, ens_pred)
    im  = ax3.imshow(cm, interpolation="nearest", cmap="Blues")
    plt.colorbar(im, ax=ax3)
    classes = ["정상", "이상"]
    tick_marks = np.arange(2)
    ax3.set_xticks(tick_marks); ax3.set_xticklabels(classes)
    ax3.set_yticks(tick_marks); ax3.set_yticklabels(classes)
    ax3.set_xlabel("예측"); ax3.set_ylabel("실제")
    ax3.set_title(f"혼동 행렬 (임계값={ens_thresh:.3f})")
    thresh_ = cm.max() / 2.0
    for i in range(2):
        for j in range(2):
            ax3.text(j, i, format(cm[i, j], "d"),
                     ha="center", va="center",
                     color="white" if cm[i, j] > thresh_ else "black",
                     fontsize=12)

    fig.suptitle("CEP + Isolation Forest 앙상블 이상 탐지", fontsize=14, y=1.02)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"   💾 {out_path.name}")

    # 앙상블 분류 리포트
    prec = precision_score(y_true, ens_pred, zero_division=0)
    rec  = recall_score(y_true, ens_pred, zero_division=0)
    f1   = f1_score(y_true, ens_pred, zero_division=0)
    print(f"\n   📊 앙상블 성능 (임계값={ens_thresh:.3f}):")
    print(f"      Precision={prec:.4f}  Recall={rec:.4f}  F1={f1:.4f}")
    print(f"      이상 탐지: {ens_pred.sum():,}건 / 전체 {len(ens_pred):,}건")


# ── 이상 항공편 리포트 ────────────────────────────────────────────────
def save_anomaly_report(
    test_df: pd.DataFrame,
    if_scores: np.ndarray,
    ens_scores: np.ndarray,
    pred_bin: np.ndarray,
    out_path: Path,
) -> None:
    """이상으로 탐지된 항공편 상위 500건을 CSV로 저장."""
    report = test_df.copy().reset_index(drop=True)
    report["if_score"]  = if_scores
    report["ens_score"] = ens_scores
    report["if_flag"]   = pred_bin

    # 이상 판정 상위 500건
    top_anomalies = (
        report[report["if_flag"] == 1]
        .sort_values("ens_score", ascending=False)
        .head(500)
    )

    cols_keep = [c for c in [
        "carrier_code", "origin", "dest", "dep_delay_min",
        "distance_miles", "prev_dep_delay_min",
        "dep_month_weather_score", "carrier_hist_delay",
        "if_score", "ens_score", "if_flag",
    ] if c in top_anomalies.columns]

    top_anomalies[cols_keep].to_csv(out_path, index=False)
    print(f"\n   💾 이상 리포트: {out_path.name} ({len(top_anomalies)}건)")


# ── Redis 스트리밍 시뮬레이션 ─────────────────────────────────────────
def run_stream_simulation(
    pipe: Pipeline,
    test_df: pd.DataFrame,
    n_batches: int = 5,
    batch_size: int = 100,
) -> None:
    """
    Redis 스트리밍 환경을 시뮬레이션합니다.
    실제 환경: flink_processor.py → Redis HASH → isolation_forest.py 읽기
    시뮬레이션: test.csv에서 배치 단위로 Feature 벡터를 읽어 온라인 탐지
    """
    print("\n" + "=" * 55)
    print("  🌊 스트리밍 이상 탐지 시뮬레이션")
    print("=" * 55)

    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True, socket_connect_timeout=1)
        r.ping()
        use_redis = True
        print("  📡 Redis 연결 성공 — 실제 스트리밍 모드")
    except Exception:
        use_redis = False
        print("  📂 Redis 미연결 — 데이터셋 시뮬레이션 모드")

    X_test, y_test = prepare_features(test_df)
    total_detected = 0

    for batch_idx in range(n_batches):
        start = batch_idx * batch_size
        end   = start + batch_size
        X_batch = X_test.iloc[start:end]
        y_batch = y_test.iloc[start:end] if y_test is not None else None

        if len(X_batch) == 0:
            break

        scores   = pipe.score_samples(X_batch)
        pred_bin = (pipe.predict(X_batch) == -1).astype(int)
        n_detect = pred_bin.sum()
        total_detected += n_detect

        # Redis에 이상 이벤트 기록
        if use_redis and n_detect > 0:
            anomaly_indices = np.where(pred_bin == 1)[0]
            for idx in anomaly_indices[:5]:  # 최대 5건만 Redis에 저장
                record = X_batch.iloc[idx].to_dict()
                record["if_score"]  = float(scores[idx])
                record["detected_at"] = int(time.time() * 1000)
                event_key = f"if_anomaly:batch{batch_idx}:idx{idx}"
                r.hset(event_key, mapping={k: str(v) for k, v in record.items()})
                r.expire(event_key, 3600)

        accuracy_str = ""
        if y_batch is not None:
            tp = int(((pred_bin == 1) & (y_batch.values == 1)).sum())
            accuracy_str = f"  (실제 지연={int(y_batch.sum())}건, TP={tp}건)"

        print(f"  배치 {batch_idx+1:02d} | {len(X_batch):3d}건 처리 → "
              f"이상 탐지: {n_detect:3d}건{accuracy_str}")
        time.sleep(0.05)  # 스트림 효과

    print(f"\n  총 탐지: {total_detected}건 / {min(n_batches * batch_size, len(X_test))}건 처리")
    if use_redis:
        print("  📥 이상 이벤트 Redis에 저장 완료 (key: if_anomaly:*)")


# ── 메인 ──────────────────────────────────────────────────────────────
def main(args: argparse.Namespace) -> None:
    print("=" * 65)
    print("  SkyOps Intelligence — Isolation Forest 이상 탐지")
    print("=" * 65)

    # 1. 데이터 로드
    train_df, test_df = load_data(samples=args.samples)
    X_train, _        = prepare_features(train_df)
    X_test,  y_test   = prepare_features(test_df)

    # 2. 모델 학습
    pipe = train_model(X_train, contamination=args.contamination)

    # 3. 모델 저장
    model_path = MODELS_DIR / "isolation_forest.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(pipe, f)
    print(f"   💾 모델 저장: {model_path.name}")

    # 4. 테스트셋 예측
    print("\n▶ 테스트셋 이상 탐지")
    if_scores, pred_bin = get_scores_and_labels(pipe, X_test)
    n_anomaly = pred_bin.sum()
    print(f"   이상 탐지: {n_anomaly:,}건 / {len(pred_bin):,}건 "
          f"({n_anomaly / len(pred_bin) * 100:.1f}%)")

    # 5. CEP 앙상블
    cep_scores = cep_anomaly_score(test_df.reset_index(drop=True))
    ens_scores = ensemble_score(if_scores, cep_scores)

    # 6. 임계값 튜닝 (실제 레이블 사용)
    if y_test is not None and y_test.sum() > 0:
        print("\n▶ 임계값 튜닝")
        thresh_df = tune_threshold(if_scores, y_test.values)
        thresh_csv = RESULTS_DIR / "if_threshold_metrics.csv"
        thresh_df.to_csv(thresh_csv, index=False)
        print(f"   💾 {thresh_csv.name}")
    else:
        thresh_df = None
        print("   ⚠️  레이블 없음 — 임계값 튜닝 스킵")

    # 7. 시각화
    print("\n▶ 시각화 생성")
    y_arr = y_test.values if y_test is not None else np.zeros(len(if_scores), dtype=int)

    plot_score_distribution(
        if_scores, y_arr,
        FIG_DIR / "16_if_anomaly_score_dist.png",
    )
    if thresh_df is not None:
        plot_precision_recall(
            thresh_df,
            FIG_DIR / "17_if_precision_recall.png",
        )
    plot_feature_scatter(
        X_test.reset_index(drop=True), if_scores, pred_bin,
        FIG_DIR / "18_if_feature_scatter.png",
    )
    plot_ensemble_result(
        if_scores, cep_scores, ens_scores, y_arr,
        FIG_DIR / "19_if_cep_ensemble.png",
    )

    # 8. 이상 리포트 저장
    save_anomaly_report(
        test_df.reset_index(drop=True),
        if_scores, ens_scores, pred_bin,
        RESULTS_DIR / "if_anomaly_report.csv",
    )

    # 9. 스트리밍 시뮬레이션 (--stream 플래그)
    if args.stream:
        run_stream_simulation(pipe, test_df)

    # 10. 요약 출력
    print("\n" + "=" * 65)
    print("📋 Isolation Forest 이상 탐지 요약")
    print("=" * 65)
    print(f"  contamination      : {args.contamination}")
    print(f"  학습 샘플 수       : {len(X_train):,}")
    print(f"  테스트 샘플 수     : {len(X_test):,}")
    print(f"  이상 탐지 (IF)     : {pred_bin.sum():,}건 ({pred_bin.mean()*100:.1f}%)")
    ens_thresh = np.percentile(ens_scores, 85)
    ens_flag   = (ens_scores >= ens_thresh).astype(int)
    print(f"  이상 탐지 (앙상블) : {ens_flag.sum():,}건 ({ens_flag.mean()*100:.1f}%)")
    if y_test is not None and y_test.sum() > 0:
        prec = precision_score(y_arr, ens_flag, zero_division=0)
        rec  = recall_score(y_arr, ens_flag, zero_division=0)
        f1   = f1_score(y_arr, ens_flag, zero_division=0)
        print(f"  앙상블 Precision   : {prec:.4f}")
        print(f"  앙상블 Recall      : {rec:.4f}")
        print(f"  앙상블 F1          : {f1:.4f}")

    print("\n📁 출력 파일:")
    outputs = [
        model_path,
        FIG_DIR / "16_if_anomaly_score_dist.png",
        FIG_DIR / "17_if_precision_recall.png",
        FIG_DIR / "18_if_feature_scatter.png",
        FIG_DIR / "19_if_cep_ensemble.png",
        RESULTS_DIR / "if_anomaly_report.csv",
    ]
    if thresh_df is not None:
        outputs.append(RESULTS_DIR / "if_threshold_metrics.csv")
    for p in outputs:
        if p.exists():
            print(f"  ✅ {p.relative_to(PROJECT_ROOT)}")

    print("\n다음 단계: python analysis/shap_analysis.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SkyOps Intelligence — Isolation Forest 이상 탐지"
    )
    parser.add_argument(
        "--contamination", type=float, default=0.05,
        help="예상 오염률 (이상 비율), 기본값 0.05",
    )
    parser.add_argument(
        "--samples", type=int, default=None,
        help="빠른 테스트용 최대 샘플 수 (예: 50000)",
    )
    parser.add_argument(
        "--stream", action="store_true",
        help="Redis 스트리밍 시뮬레이션 실행",
    )
    main(parser.parse_args())
