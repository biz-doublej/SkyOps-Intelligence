"""
SkyOps Intelligence — 4주차 Train/Validation/Test 분할 + CSV 저장
===================================================================
비율: 7 : 1.5 : 1.5  (시간 순서 유지 — 시계열 데이터 원칙)

실행:
  python analysis/prepare_dataset.py

출력:
  data/processed/train.csv      (70%)
  data/processed/val.csv        (15%)
  data/processed/test.csv       (15%)
  data/processed/dataset_info.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ── 경로 설정 ──────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FEATURES_PATH = PROCESSED_DIR / "features.parquet"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ── 분할 비율 ──────────────────────────────────────────────────────────
TRAIN_RATIO = 0.70
VAL_RATIO   = 0.15
TEST_RATIO  = 0.15

# ── 사용할 Feature 컬럼 (데이터 누설 컬럼 제외) ──────────────────────
FEATURE_COLS = [
    # 시간 관련
    "dep_hour", "dep_minute", "dep_dayofweek", "dep_month",
    "dep_dayofyear", "is_weekend",
    # 공항/노선
    "origin", "dest", "route", "distance_miles",
    # 항공사 + 기체
    "carrier_code", "tail_number",       # P1 Rotation PoC · 2026-04-14
    # 운항 계획
    "sched_elapsed_min", "dep_block",
    # Cascade Delay
    "prev_dep_delay_min", "prev_arr_delay_min", "is_prev_delayed",
    # Rotation (P1 · 2026-04-14)
    "rotation_depth", "prev_leg_arr_delay_min",
    "scheduled_turnaround_min", "actual_turnaround_min",
    "is_first_leg_of_day",
    # 혼잡도
    "origin_hourly_departures", "dest_hourly_arrivals",
    # 기상 이력
    "dep_month_weather_score",
    "origin_weather_hist_delay", "dest_weather_hist_delay",
    # 통계 인코딩
    "carrier_hist_delay", "origin_hist_delay",
    "dest_hist_delay", "route_hist_delay",
]

TARGET_COL   = "dep_delay_min"       # 회귀 타깃 (분)
BINARY_COL   = "is_delayed"          # 이진 분류 타깃 (>15분 = 1)
DELAY_THRESHOLD = 15                 # 지연 정의 기준 (분)


# ── 데이터 로드 ────────────────────────────────────────────────────────
def load_features() -> pd.DataFrame:
    if not FEATURES_PATH.exists():
        print(f"❌ 파일 없음: {FEATURES_PATH}")
        print("   먼저 실행하세요: python analysis/feature_engineering.py")
        sys.exit(1)

    print(f"📂 Feature 데이터 로드: {FEATURES_PATH}")
    df = pd.read_parquet(FEATURES_PATH)
    print(f"   {len(df):,}행 × {df.shape[1]}컬럼")
    return df


# ── 시간 순서 기반 분할 ────────────────────────────────────────────────
def temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    시계열 데이터는 랜덤 분할이 아닌 시간 순서 분할을 사용합니다.
    미래 데이터로 과거를 예측하는 데이터 누설(leakage)을 방지합니다.

    Train: 앞 70%  (1월 ~ 9월 초 수준)
    Val:   중간 15% (9월 초 ~ 10월 말 수준)
    Test:  뒤 15%  (11월 ~ 12월)
    """
    df = df.sort_values("fl_date").reset_index(drop=True)

    n = len(df)
    train_end = int(n * TRAIN_RATIO)
    val_end   = int(n * (TRAIN_RATIO + VAL_RATIO))

    train = df.iloc[:train_end].copy()
    val   = df.iloc[train_end:val_end].copy()
    test  = df.iloc[val_end:].copy()

    return train, val, test


# ── 이진 분류 타깃 추가 ───────────────────────────────────────────────
def add_binary_target(df: pd.DataFrame) -> pd.DataFrame:
    df[BINARY_COL] = (df[TARGET_COL] > DELAY_THRESHOLD).astype(int)
    return df


# ── Feature / Target 분리 및 저장 ─────────────────────────────────────
def save_split(df: pd.DataFrame, name: str) -> None:
    # 사용 가능한 Feature 컬럼만 선택
    available = [c for c in FEATURE_COLS if c in df.columns]
    missing   = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        print(f"   ⚠️  누락된 Feature: {missing}")

    # 저장 컬럼: 메타 + Feature + 타깃
    save_cols = ["fl_date", "carrier_code", "origin", "dest"] + available + [TARGET_COL, BINARY_COL]
    save_cols = list(dict.fromkeys(save_cols))  # 중복 제거
    save_cols = [c for c in save_cols if c in df.columns]

    out = PROCESSED_DIR / f"{name}.csv"
    df[save_cols].to_csv(out, index=False, encoding="utf-8")
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"   💾 {out} — {len(df):,}행 ({size_mb:.1f} MB)")


# ── 데이터셋 정보 저장 ────────────────────────────────────────────────
def save_dataset_info(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    total = len(train) + len(val) + len(test)

    def stats(df: pd.DataFrame, name: str) -> list[str]:
        delayed_pct = df.get(BINARY_COL, pd.Series(dtype=int)).mean() * 100
        avg_delay   = df.get(TARGET_COL, pd.Series(dtype=float)).mean()
        date_min    = df["fl_date"].min() if "fl_date" in df.columns else "N/A"
        date_max    = df["fl_date"].max() if "fl_date" in df.columns else "N/A"
        return [
            f"[{name.upper()}]",
            f"  행 수:         {len(df):>10,}  ({len(df)/total*100:.1f}%)",
            f"  기간:          {date_min} ~ {date_max}",
            f"  지연율 (>15분): {delayed_pct:>8.1f}%",
            f"  평균 지연:     {avg_delay:>8.1f}분",
            "",
        ]

    lines = [
        "=" * 60,
        "SkyOps Intelligence — 학습 데이터셋 정보",
        "=" * 60,
        f"총 항공편:   {total:,}편",
        f"Feature 수:  {len([c for c in FEATURE_COLS if c in train.columns])}개",
        f"타깃 (회귀): {TARGET_COL}",
        f"타깃 (분류): {BINARY_COL} (기준: >{DELAY_THRESHOLD}분)",
        f"분할 전략:   시간 순서 (Temporal Split) — 랜덤 아님",
        f"분할 비율:   Train {TRAIN_RATIO:.0%} / Val {VAL_RATIO:.0%} / Test {TEST_RATIO:.0%}",
        "",
        *stats(train, "train"),
        *stats(val,   "validation"),
        *stats(test,  "test"),
        "파일 목록:",
        f"  data/processed/train.csv     {len(train):,}행",
        f"  data/processed/val.csv       {len(val):,}행",
        f"  data/processed/test.csv      {len(test):,}행",
    ]

    out = PROCESSED_DIR / "dataset_info.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📄 데이터셋 정보 저장: {out}")
    print("\n".join(lines[1:9]))


# ── 분포 체크 ──────────────────────────────────────────────────────────
def check_distribution(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    print("\n[분포 균형 확인]")
    print(f"  {'세트':<10} {'지연율':>8} {'평균지연':>10} {'항공편수':>10}")
    print("  " + "-" * 42)
    for name, df in [("Train", train), ("Val", val), ("Test", test)]:
        dr = (df.get(BINARY_COL, pd.Series(dtype=int)) == 1).mean() * 100
        ad = df.get(TARGET_COL, pd.Series(dtype=float)).mean()
        print(f"  {name:<10} {dr:>7.1f}% {ad:>9.1f}분 {len(df):>10,}편")

    # 항공사 분포 체크
    print("\n[항공사별 분포 비교 (Train vs Test)]")
    train_carrier = (train["carrier_code"].value_counts(normalize=True) * 100).round(1)
    test_carrier  = (test["carrier_code"].value_counts(normalize=True) * 100).round(1)
    carrier_df = pd.DataFrame({"train_%": train_carrier, "test_%": test_carrier}).fillna(0)
    carrier_df["diff"] = (carrier_df["train_%"] - carrier_df["test_%"]).abs()
    print(carrier_df.sort_values("train_%", ascending=False).head(10).to_string())


# ── 진입점 ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  SkyOps — Dataset 준비 (Train/Val/Test 분할)")
    print("=" * 60)

    df = load_features()

    # 이진 타깃 추가
    df = add_binary_target(df)

    # 시간 순서 분할
    print("\n▶ 시간 순서 기반 분할 중...")
    train, val, test = temporal_split(df)

    # 분포 확인
    check_distribution(train, val, test)

    # CSV 저장
    print("\n▶ CSV 저장 중...")
    for name, subset in [("train", train), ("val", val), ("test", test)]:
        save_split(subset, name)

    # 정보 파일 저장
    save_dataset_info(train, val, test)

    print(f"\n✅ 완료! 저장 위치: {PROCESSED_DIR}")
    print("다음 단계: 5주차 — XGBoost 모델링")
