"""
SkyOps Intelligence — 4주차 EDA (탐색적 데이터 분석)
=======================================================
Kaggle 2015 Flight Delays Dataset 기반

실행:
  python analysis/eda.py
  python analysis/eda.py --sample 500000   # 빠른 샘플 실행

출력:
  data/figures/01_missing_values.png
  data/figures/02_delay_distribution.png
  data/figures/03_delay_causes_top10.png
  data/figures/04_delay_by_carrier.png
  data/figures/05_delay_by_hour.png
  data/figures/06_delay_by_month.png
  data/figures/07_outlier_boxplot.png
  data/figures/08_correlation_heatmap.png
  data/eda_summary.txt
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 헤드리스 환경 (서버/스크립트) 대응
from matplotlib import font_manager
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

# ── 경로 설정 ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR    = PROJECT_ROOT / "data"
RAW_CSV     = DATA_DIR / "raw" / "flights.csv"
FIG_DIR     = DATA_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ── 스타일 ─────────────────────────────────────────────────────────────
def _configure_plot_font() -> str | None:
    """한글을 지원하는 시스템 폰트를 우선 적용한다."""
    candidate_fonts = [
        "Malgun Gothic",
        "AppleGothic",
        "NanumGothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
    ]
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for font_name in candidate_fonts:
        if font_name in installed:
            return font_name
    return None


KOREAN_FONT = _configure_plot_font()
sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
if KOREAN_FONT:
    plt.rcParams["font.family"] = KOREAN_FONT
    plt.rcParams["font.sans-serif"] = [KOREAN_FONT]
plt.rcParams["axes.unicode_minus"] = False
PALETTE = sns.color_palette("muted")

# ── Kaggle 컬럼 → 내부 이름 매핑 ──────────────────────────────────────
RENAME_MAP = {
    "YEAR":                "year",
    "MONTH":               "month",
    "DAY":                 "day",
    "AIRLINE":             "carrier_code",
    "FLIGHT_NUMBER":       "flight_num",
    "ORIGIN_AIRPORT":      "origin",
    "DESTINATION_AIRPORT": "dest",
    "SCHEDULED_DEPARTURE": "sched_dep_time",
    "DEPARTURE_TIME":      "act_dep_time",
    "DEPARTURE_DELAY":     "dep_delay_min",
    "TAXI_OUT":            "taxi_out_min",
    "WHEELS_OFF":          "wheels_off",
    "WHEELS_ON":           "wheels_on",
    "TAXI_IN":             "taxi_in_min",
    "SCHEDULED_ARRIVAL":   "sched_arr_time",
    "ARRIVAL_TIME":        "act_arr_time",
    "ARRIVAL_DELAY":       "arr_delay_min",
    "CANCELLED":           "cancelled",
    "CANCELLATION_REASON": "cancel_code",
    "DIVERTED":            "diverted",
    "SCHEDULED_TIME":      "sched_elapsed_min",
    "ELAPSED_TIME":        "act_elapsed_min",
    "AIR_TIME":            "air_time_min",
    "DISTANCE":            "distance_miles",
    "AIRLINE_DELAY":       "carrier_delay_min",
    "WEATHER_DELAY":       "weather_delay_min",
    "AIR_SYSTEM_DELAY":    "nas_delay_min",
    "SECURITY_DELAY":      "security_delay_min",
    "LATE_AIRCRAFT_DELAY": "late_aircraft_delay_min",
}

DELAY_CAUSE_COLS = [
    "carrier_delay_min", "weather_delay_min",
    "nas_delay_min", "security_delay_min", "late_aircraft_delay_min",
]

DELAY_CAUSE_LABELS = {
    "carrier_delay_min":       "항공사 귀책",
    "weather_delay_min":       "기상",
    "nas_delay_min":           "국가항공시스템(NAS)",
    "security_delay_min":      "보안",
    "late_aircraft_delay_min": "전편 지연",
}


# ── 데이터 로드 ────────────────────────────────────────────────────────
def load_data(sample_n: int | None = None) -> pd.DataFrame:
    if not RAW_CSV.exists():
        print(f"❌ 데이터 파일 없음: {RAW_CSV}")
        print("   먼저 실행하세요: python analysis/download_dataset.py")
        sys.exit(1)

    print(f"📂 데이터 로드 중: {RAW_CSV}")
    usecols = list(RENAME_MAP.keys())

    if sample_n:
        df = pd.read_csv(RAW_CSV, usecols=usecols, nrows=sample_n, low_memory=False)
        print(f"   샘플: {sample_n:,}행 로드")
    else:
        df = pd.read_csv(RAW_CSV, usecols=usecols, low_memory=False)
        print(f"   전체: {len(df):,}행 로드")

    df.rename(columns=RENAME_MAP, inplace=True)

    # YEAR/MONTH/DAY 조합 → 내부 날짜 컬럼 생성
    df["fl_date"] = pd.to_datetime(df[["year", "month", "day"]], errors="coerce")
    df.drop(columns=["year", "month", "day"], inplace=True)

    # 타입 변환
    for col in ["dep_delay_min", "arr_delay_min"] + DELAY_CAUSE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ── 01. 결측치 분포 시각화 ─────────────────────────────────────────────
def plot_missing_values(df: pd.DataFrame) -> None:
    missing = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
    missing = missing[missing > 0]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(missing.index, missing.values, color=PALETTE[0], edgecolor="white")
    ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=9)
    ax.set_xlabel("결측치 비율 (%)")
    ax.set_title("컬럼별 결측치 비율", fontsize=14, fontweight="bold")
    ax.set_xlim(0, max(missing.values) * 1.15)
    ax.invert_yaxis()

    # 기준선 (10%, 30%)
    for threshold, color in [(10, "orange"), (30, "red")]:
        ax.axvline(threshold, color=color, linestyle="--", alpha=0.6, label=f"{threshold}% 기준")
    ax.legend(fontsize=9)

    plt.tight_layout()
    out = FIG_DIR / "01_missing_values.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"   💾 {out}")

    # 요약 출력
    print(f"\n[결측치 요약]")
    for col, pct in missing.items():
        flag = "⚠️ " if pct > 30 else "   "
        print(f"  {flag}{col:30s}: {pct:5.1f}%")


# ── 02. 도착 지연 분포 ─────────────────────────────────────────────────
def plot_delay_distribution(df: pd.DataFrame) -> None:
    valid = df["arr_delay_min"].dropna()
    # -60 ~ 300분 범위로 클리핑 (이상치 제외한 시각화)
    clipped = valid.clip(-60, 300)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 히스토그램
    axes[0].hist(clipped, bins=80, color=PALETTE[1], edgecolor="white", alpha=0.85)
    axes[0].axvline(0, color="red", linestyle="--", label="기준 (0분)")
    axes[0].axvline(valid.mean(), color="orange", linestyle="--",
                    label=f"평균 {valid.mean():.1f}분")
    axes[0].set_xlabel("도착 지연 (분)")
    axes[0].set_ylabel("편수")
    axes[0].set_title("도착 지연 분포 (-60~+300분)", fontweight="bold")
    axes[0].legend(fontsize=9)
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # 누적 분포 (CDF)
    sorted_vals = np.sort(valid.values)
    cdf = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals)
    axes[1].plot(sorted_vals, cdf, color=PALETTE[2], linewidth=1.5)
    axes[1].set_xlim(-60, 300)
    axes[1].axvline(0, color="red", linestyle="--", alpha=0.7)
    axes[1].axhline(0.8, color="gray", linestyle=":", alpha=0.7, label="80% 분위")
    axes[1].set_xlabel("도착 지연 (분)")
    axes[1].set_ylabel("누적 비율")
    axes[1].set_title("도착 지연 누적 분포 (CDF)", fontweight="bold")
    axes[1].legend(fontsize=9)

    # 통계 박스
    stats_text = (
        f"전체: {len(valid):,}편\n"
        f"지연(>0): {(valid > 0).sum() / len(valid) * 100:.1f}%\n"
        f"중위수: {valid.median():.0f}분\n"
        f"평균: {valid.mean():.1f}분\n"
        f"표준편차: {valid.std():.1f}분"
    )
    axes[0].text(0.97, 0.97, stats_text, transform=axes[0].transAxes,
                 va="top", ha="right", fontsize=8.5,
                 bbox=dict(boxstyle="round", facecolor="white", alpha=0.7))

    plt.tight_layout()
    out = FIG_DIR / "02_delay_distribution.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"   💾 {out}")


# ── 03. 지연 원인 TOP 10 ───────────────────────────────────────────────
def plot_delay_causes(df: pd.DataFrame) -> None:
    # 지연된 항공편만 (arr_delay_min > 0, 취소 제외)
    delayed = df[(df["arr_delay_min"] > 0) & (df["cancelled"] != 1)].copy()

    cause_totals = {}
    cause_counts = {}
    for col in DELAY_CAUSE_COLS:
        cause_totals[DELAY_CAUSE_LABELS[col]] = delayed[col].sum()
        cause_counts[DELAY_CAUSE_LABELS[col]] = (delayed[col] > 0).sum()

    # 총 지연 시간 기준 정렬
    total_s  = pd.Series(cause_totals).sort_values(ascending=True)
    count_s  = pd.Series(cause_counts)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 총 지연 시간
    bars = axes[0].barh(total_s.index, total_s.values / 1e6,
                        color=PALETTE[:len(total_s)][::-1], edgecolor="white")
    axes[0].bar_label(bars, fmt="%.1fM분", padding=3, fontsize=9)
    axes[0].set_xlabel("총 지연 시간 (백만 분)")
    axes[0].set_title("원인별 총 지연 시간", fontweight="bold")

    # 발생 건수
    count_sorted = count_s.reindex(total_s.index)
    bars2 = axes[1].barh(count_sorted.index, count_sorted.values / 1000,
                         color=PALETTE[:len(count_sorted)][::-1], edgecolor="white")
    axes[1].bar_label(bars2, fmt="%.0fK건", padding=3, fontsize=9)
    axes[1].set_xlabel("발생 건수 (천 건)")
    axes[1].set_title("원인별 지연 발생 건수", fontweight="bold")

    for ax in axes:
        ax.set_xlim(right=ax.get_xlim()[1] * 1.2)

    plt.suptitle("항공편 지연 원인 분석 (2015)", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    out = FIG_DIR / "03_delay_causes_top10.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   💾 {out}")


# ── 04. 항공사별 평균 지연 ─────────────────────────────────────────────
def plot_delay_by_carrier(df: pd.DataFrame) -> None:
    carrier_stats = (
        df[df["arr_delay_min"].notna()]
        .groupby("carrier_code")["arr_delay_min"]
        .agg(["mean", "median", "count"])
        .rename(columns={"mean": "avg_delay", "median": "med_delay", "count": "flights"})
        .query("flights >= 1000")
        .sort_values("avg_delay", ascending=False)
        .head(15)
    )

    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(carrier_stats))
    bars = ax.bar(x, carrier_stats["avg_delay"], color=PALETTE[3], edgecolor="white", label="평균")
    ax.scatter(x, carrier_stats["med_delay"], color="red", zorder=5, s=50, label="중위수")
    ax.set_xticks(x)
    ax.set_xticklabels(carrier_stats.index, rotation=0)
    ax.set_ylabel("지연 시간 (분)")
    ax.set_title("항공사별 평균 도착 지연 (1,000편 이상)", fontweight="bold")
    ax.axhline(carrier_stats["avg_delay"].mean(), color="gray", linestyle="--",
               alpha=0.7, label=f"전체 평균 {carrier_stats['avg_delay'].mean():.1f}분")
    ax.legend()
    ax.bar_label(bars, fmt="%.1f", padding=2, fontsize=8.5)

    # 운항 편수 주석
    for i, (_, row) in enumerate(carrier_stats.iterrows()):
        ax.text(i, -3, f"{row['flights']//1000:.0f}K", ha="center", fontsize=8, color="gray")

    plt.tight_layout()
    out = FIG_DIR / "04_delay_by_carrier.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"   💾 {out}")


# ── 05. 시간대별 지연 패턴 ────────────────────────────────────────────
def plot_delay_by_hour(df: pd.DataFrame) -> None:
    df2 = df[df["dep_delay_min"].notna() & df["sched_dep_time"].notna()].copy()
    df2["dep_hour"] = (df2["sched_dep_time"] // 100).astype(int).clip(0, 23)

    hour_stats = df2.groupby("dep_hour")["dep_delay_min"].agg(["mean", "count"])

    fig, ax1 = plt.subplots(figsize=(13, 5))
    ax2 = ax1.twinx()

    ax1.plot(hour_stats.index, hour_stats["mean"], color=PALETTE[0],
             marker="o", linewidth=2, markersize=6, label="평균 출발 지연")
    ax1.fill_between(hour_stats.index, hour_stats["mean"], alpha=0.15, color=PALETTE[0])
    ax1.set_xlabel("출발 예정 시각 (시)")
    ax1.set_ylabel("평균 지연 시간 (분)", color=PALETTE[0])
    ax1.set_xticks(range(0, 24))
    ax1.axhline(0, color="gray", linestyle="--", alpha=0.5)

    ax2.bar(hour_stats.index, hour_stats["count"] / 1000, alpha=0.25,
            color=PALETTE[4], label="운항 편수 (천)")
    ax2.set_ylabel("운항 편수 (천)", color=PALETTE[4])

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=9)
    ax1.set_title("시간대별 출발 지연 패턴", fontweight="bold")

    plt.tight_layout()
    out = FIG_DIR / "05_delay_by_hour.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"   💾 {out}")


# ── 06. 월별 지연 패턴 ────────────────────────────────────────────────
def plot_delay_by_month(df: pd.DataFrame) -> None:
    df2 = df[df["fl_date"].notna() & df["arr_delay_min"].notna()].copy()
    df2["month"] = df2["fl_date"].dt.month
    month_stats = df2.groupby("month")["arr_delay_min"].agg(["mean", "count"])

    MONTH_KR = ["1월\n(신정)", "2월\n(설날)", "3월", "4월", "5월\n(연휴)", "6월",
                "7월\n(여름)", "8월\n(여름)", "9월\n(추석)", "10월", "11월\n(추수)", "12월\n(크리스마스)"]
    month_stats.index = [MONTH_KR[i - 1] for i in month_stats.index]

    fig, ax = plt.subplots(figsize=(14, 5))
    colors = [PALETTE[1] if v > month_stats["mean"].mean() else PALETTE[2]
              for v in month_stats["mean"]]
    bars = ax.bar(month_stats.index, month_stats["mean"], color=colors, edgecolor="white")
    ax.bar_label(bars, fmt="%.1f분", padding=2, fontsize=8.5)
    ax.axhline(month_stats["mean"].mean(), color="gray", linestyle="--",
               alpha=0.7, label=f"연평균 {month_stats['mean'].mean():.1f}분")
    ax.set_ylabel("평균 도착 지연 (분)")
    ax.set_title("월별 평균 도착 지연 (2015)", fontweight="bold")
    ax.legend()

    plt.tight_layout()
    out = FIG_DIR / "06_delay_by_month.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"   💾 {out}")


# ── 07. 이상치 박스플롯 ───────────────────────────────────────────────
def plot_outlier_boxplot(df: pd.DataFrame) -> None:
    numeric_cols = ["dep_delay_min", "arr_delay_min", "taxi_out_min", "taxi_in_min",
                    "air_time_min", "distance_miles"]
    available = [c for c in numeric_cols if c in df.columns]
    data = [df[c].dropna().clip(-60, 500).values for c in available]

    fig, ax = plt.subplots(figsize=(13, 5))
    bp = ax.boxplot(data, tick_labels=available, patch_artist=True, notch=False,
                    showfliers=True, flierprops=dict(marker=".", markersize=1.5, alpha=0.3))
    for patch, color in zip(bp["boxes"], PALETTE):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.axhline(0, color="red", linestyle="--", alpha=0.5)
    ax.set_ylabel("분 (min) / 마일 (miles)")
    ax.set_title("주요 수치 컬럼 이상치 분포 (Box Plot)", fontweight="bold")
    ax.tick_params(axis="x", rotation=20)

    plt.tight_layout()
    out = FIG_DIR / "07_outlier_boxplot.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"   💾 {out}")


# ── 08. 상관관계 히트맵 ───────────────────────────────────────────────
def plot_correlation_heatmap(df: pd.DataFrame) -> None:
    corr_cols = [
        "dep_delay_min", "arr_delay_min", "taxi_out_min", "taxi_in_min",
        "air_time_min", "distance_miles",
        "carrier_delay_min", "weather_delay_min", "nas_delay_min",
        "late_aircraft_delay_min",
    ]
    available = [c for c in corr_cols if c in df.columns]
    corr = df[available].corr()

    labels = {
        "dep_delay_min": "출발지연",
        "arr_delay_min": "도착지연",
        "taxi_out_min": "택시아웃",
        "taxi_in_min": "택시인",
        "air_time_min": "비행시간",
        "distance_miles": "거리",
        "carrier_delay_min": "항공사귀책",
        "weather_delay_min": "기상",
        "nas_delay_min": "NAS",
        "late_aircraft_delay_min": "전편지연",
    }
    corr.columns = [labels.get(c, c) for c in corr.columns]
    corr.index   = [labels.get(c, c) for c in corr.index]

    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdYlGn",
                vmin=-1, vmax=1, linewidths=0.5, ax=ax,
                annot_kws={"size": 9})
    ax.set_title("주요 수치 변수 상관관계 히트맵", fontsize=13, fontweight="bold")

    plt.tight_layout()
    out = FIG_DIR / "08_correlation_heatmap.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"   💾 {out}")


# ── EDA 요약 보고서 저장 ───────────────────────────────────────────────
def save_summary(df: pd.DataFrame) -> None:
    out = DATA_DIR / "eda_summary.txt"
    total = len(df)
    delayed = (df["arr_delay_min"] > 0).sum()
    cancelled = df["cancelled"].sum() if "cancelled" in df.columns else 0

    lines = [
        "=" * 60,
        "SkyOps Intelligence — EDA 요약 보고서",
        "=" * 60,
        f"전체 항공편:    {total:>10,}편",
        f"지연 (>0분):   {delayed:>10,}편  ({delayed/total*100:.1f}%)",
        f"취소:          {int(cancelled):>10,}편  ({cancelled/total*100:.1f}%)",
        "",
        "[도착 지연 통계]",
        f"  평균:   {df['arr_delay_min'].mean():>8.1f}분",
        f"  중위수: {df['arr_delay_min'].median():>8.0f}분",
        f"  표준편차:{df['arr_delay_min'].std():>7.1f}분",
        f"  최소:   {df['arr_delay_min'].min():>8.0f}분",
        f"  최대:   {df['arr_delay_min'].max():>8.0f}분",
        "",
        "[지연 원인별 기여 비율]",
    ]

    delayed_df = df[(df["arr_delay_min"] > 0) & (df["cancelled"] != 1)]
    for col in DELAY_CAUSE_COLS:
        if col in df.columns:
            total_cause = delayed_df[col].sum()
            total_delay = sum(delayed_df[c].sum() for c in DELAY_CAUSE_COLS if c in df.columns)
            pct = total_cause / total_delay * 100 if total_delay > 0 else 0
            label = DELAY_CAUSE_LABELS[col]
            lines.append(f"  {label:20s}: {pct:5.1f}%  ({total_cause/1e6:.2f}M분)")

    lines += [
        "",
        "[결측치 상위 컬럼]",
    ]
    missing = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
    for col, pct in missing[missing > 0].items():
        lines.append(f"  {col:30s}: {pct:5.1f}%")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📄 EDA 요약 저장: {out}")
    print("\n".join(lines[1:6]))


# ── 메인 ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="SkyOps EDA 스크립트")
    parser.add_argument("--sample", type=int, default=None,
                        help="샘플 행 수 (예: --sample 500000)")
    args = parser.parse_args()

    print("=" * 60)
    print("  SkyOps Intelligence — EDA 시작")
    print("=" * 60)

    df = load_data(args.sample)

    print("\n[데이터 기본 정보]")
    print(f"  Shape: {df.shape}")
    print(f"  메모리: {df.memory_usage(deep=True).sum() / 1024**2:.0f} MB")
    print(f"  기간:   {df['fl_date'].min()} ~ {df['fl_date'].max()}")

    steps = [
        ("01 결측치 분포",         lambda: plot_missing_values(df)),
        ("02 지연 분포",            lambda: plot_delay_distribution(df)),
        ("03 지연 원인 TOP 10",     lambda: plot_delay_causes(df)),
        ("04 항공사별 지연",        lambda: plot_delay_by_carrier(df)),
        ("05 시간대별 지연",        lambda: plot_delay_by_hour(df)),
        ("06 월별 지연",            lambda: plot_delay_by_month(df)),
        ("07 이상치 박스플롯",      lambda: plot_outlier_boxplot(df)),
        ("08 상관관계 히트맵",      lambda: plot_correlation_heatmap(df)),
        ("요약 보고서 저장",        lambda: save_summary(df)),
    ]

    for name, func in steps:
        print(f"\n▶ {name}")
        try:
            func()
        except Exception as e:
            print(f"   ⚠️ 오류: {e}")

    print(f"\n✅ EDA 완료! 시각화 저장 위치: {FIG_DIR}")
    print("다음 단계: python analysis/feature_engineering.py")


if __name__ == "__main__":
    main()
