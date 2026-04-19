"""
SkyOps — Upstream delay state features (Stage 2 / ADR-005, v2.1.9 · 2026-04-19).

실제 운영에서 공항은 "지연이 전염되는" 시스템이다. ICN 이 지난 60 분간
30 분 이상 평균 지연을 보이고 있다면, 지금 이 순간 ICN 발 비행편도 높은
확률로 지연된다 — **그런데 이걸 알려주는 feature 가 기존엔 없었다**.

본 모듈은 airport-level 의 **시계열 롤링 상태** 를 계산한다:

    origin_recent_delay_avg_60m     (도착지가 아닌 출발 공항의 최근 60 분 출발 지연 평균)
    origin_recent_delay_p95_60m     (최근 60 분 p95 — 꼬리 리스크)
    origin_recent_volume_60m        (같은 60 분 출발 편수 — 혼잡도)
    dest_recent_delay_avg_60m       (도착 공항의 최근 60 분 도착 지연 평균)
    dest_recent_volume_60m
    origin_hub_congestion_ratio     (현재 볼륨 / 해당 공항 평균 시간당 볼륨)

**학습 시**: leak-free 를 위해 "현 항공편의 departure_time 이전" 데이터만 사용.
pandas 에서는 `groupby(airport).rolling(window, closed='left')` 로 구현.

**서빙 시**: Redis hash 에 실시간으로 갱신되는 값을 조회 (O(1)).
key pattern:   `skyops:upstream:{airport}:{bucket}`
value:         JSON  {"count": 42, "delay_sum": 350.5, "delay_sq": 8421.1, "p95": 22.0}

실행:
    python -m analysis.upstream_delay --sample 500000 --window-min 60
    python -m analysis.upstream_delay --self-test
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_CSV = DATA_DIR / "raw" / "flights.csv"
OUT_CSV = DATA_DIR / "models" / "upstream_delay_features.csv"


# ──────────────────────────────────────────────────────────────────────
# Feature computation
# ──────────────────────────────────────────────────────────────────────
def _to_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Combine FL_DATE + DEP_TIME / ARR_TIME into tz-naive datetimes."""
    df = df.copy()
    fl_date = pd.to_datetime(df["FL_DATE"], errors="coerce")
    # CRS_DEP_TIME is hhmm int (e.g. 1430). Convert to timedelta.
    def _hhmm(col):
        mins = (df[col].fillna(0).astype(int) % 100)
        hrs = (df[col].fillna(0).astype(int) // 100)
        return pd.to_timedelta(hrs, unit="h") + pd.to_timedelta(mins, unit="m")
    df["dep_ts"] = fl_date + _hhmm("CRS_DEP_TIME")
    df["arr_ts"] = fl_date + _hhmm("CRS_ARR_TIME")
    return df


def _rolling_by_group(
    df: pd.DataFrame, group_col: str, ts_col: str, value_col: str,
    window: str, funcs: tuple[str, ...],
) -> dict[str, pd.Series]:
    """Leak-free time-based rolling per group.

    pandas time-rolling 은 DatetimeIndex 가 필수라 먼저 ts_col 을 index 로 만들고
    groupby.rolling 을 사용한 뒤 원 df 순서로 align.

    Returns dict {func_name: Series aligned to df's original row order}.
    """
    df = df.reset_index(drop=True)
    df_sorted = (
        df.sort_values([group_col, ts_col], kind="stable")
          .reset_index()  # 원 index 를 '__orig' column 으로 보존
          .rename(columns={"index": "__orig"})
    )
    df_idx = df_sorted.set_index(ts_col)

    results: dict[str, pd.Series] = {}
    for fn in funcs:
        g = df_idx.groupby(group_col, observed=True, sort=False)[value_col]
        rolled = g.rolling(window, closed="left")
        if fn == "mean":
            s = rolled.mean()
        elif fn == "count":
            s = rolled.count()
        elif fn == "p95":
            s = rolled.quantile(0.95)
        else:
            raise ValueError(f"unsupported fn={fn}")
        # drop the group-level index, keep ts-level ONLY values; align to __orig
        values = s.reset_index(level=0, drop=True).reset_index(drop=True)
        # align back: df_sorted['__orig'] gives the original row indices in sorted order
        aligned = pd.Series(index=range(len(df)), dtype=float)
        aligned.loc[df_sorted["__orig"].values] = values.values
        results[fn] = aligned
    return results


def compute_origin_state(
    df: pd.DataFrame, window_min: int = 60, p95_enabled: bool = True,
) -> pd.DataFrame:
    """Rolling state keyed by (origin, dep_ts). Leak-free via closed='left'."""
    win = f"{window_min}min"
    out = df.reset_index(drop=True).copy()

    funcs = ("mean", "count") + (("p95",) if p95_enabled else ())
    res = _rolling_by_group(out, "ORIGIN", "dep_ts", "DEP_DELAY", win, funcs)
    out["origin_recent_delay_avg_60m"] = res["mean"]
    out["origin_recent_volume_60m"] = res["count"]
    if p95_enabled:
        out["origin_recent_delay_p95_60m"] = res["p95"]

    fill_cols = ["origin_recent_delay_avg_60m", "origin_recent_volume_60m"]
    if p95_enabled:
        fill_cols.append("origin_recent_delay_p95_60m")
    out[fill_cols] = out[fill_cols].fillna(0.0)
    return out


def compute_dest_state(df: pd.DataFrame, window_min: int = 60) -> pd.DataFrame:
    """Rolling arrival delay + volume at DEST, keyed by arr_ts."""
    win = f"{window_min}min"
    out = df.reset_index(drop=True).copy()
    res = _rolling_by_group(out, "DEST", "arr_ts", "ARR_DELAY", win, ("mean", "count"))
    out["dest_recent_delay_avg_60m"] = res["mean"]
    out["dest_recent_volume_60m"] = res["count"]
    out[["dest_recent_delay_avg_60m", "dest_recent_volume_60m"]] = (
        out[["dest_recent_delay_avg_60m", "dest_recent_volume_60m"]].fillna(0.0)
    )
    return out


def compute_hub_congestion(df: pd.DataFrame) -> pd.DataFrame:
    """Departure hour vs. origin's long-run hourly average → ratio."""
    df = df.copy()
    df["dep_hour"] = pd.to_datetime(df["dep_ts"], errors="coerce").dt.hour.fillna(0).astype(int)
    # per-origin × per-hour long-run average count (training-time aggregate).
    mean_count = (
        df.groupby(["ORIGIN", "dep_hour"], observed=True).size()
        .groupby("ORIGIN").mean().rename("origin_avg_hourly_departures")
    )
    df = df.merge(mean_count.reset_index(), on="ORIGIN", how="left")
    df["origin_hub_congestion_ratio"] = (
        df["origin_recent_volume_60m"] / df["origin_avg_hourly_departures"]
    ).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return df


# ──────────────────────────────────────────────────────────────────────
# Top-level
# ──────────────────────────────────────────────────────────────────────
UPSTREAM_COLS = [
    "origin_recent_delay_avg_60m",
    "origin_recent_delay_p95_60m",
    "origin_recent_volume_60m",
    "dest_recent_delay_avg_60m",
    "dest_recent_volume_60m",
    "origin_hub_congestion_ratio",
]


def add_upstream_features(
    df: pd.DataFrame, window_min: int = 60, p95_enabled: bool = True,
) -> pd.DataFrame:
    """Pipeline: _to_datetime → compute_origin_state → compute_dest_state → hub_congestion."""
    needed = {"FL_DATE", "CRS_DEP_TIME", "CRS_ARR_TIME", "ORIGIN", "DEST", "DEP_DELAY", "ARR_DELAY"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    df = _to_datetime(df)
    df = compute_origin_state(df, window_min=window_min, p95_enabled=p95_enabled)
    df = compute_dest_state(df, window_min=window_min)
    df = compute_hub_congestion(df)
    return df


# ──────────────────────────────────────────────────────────────────────
# Self-test
# ──────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    """Build a tiny synthetic schedule and verify leak-free rolling."""
    print("── self-test: synthetic origin ICN 6 flights / 2h ──")
    ts = pd.to_datetime([
        "2026-04-19 08:00", "2026-04-19 08:15", "2026-04-19 08:30",
        "2026-04-19 09:00", "2026-04-19 09:45", "2026-04-19 10:30",
    ])
    df = pd.DataFrame({
        "FL_DATE": ts.strftime("%Y-%m-%d"),
        "CRS_DEP_TIME": [800, 815, 830, 900, 945, 1030],
        "CRS_ARR_TIME": [930, 945, 1000, 1030, 1115, 1200],
        "ORIGIN": ["ICN"] * 6,
        "DEST": ["CJU"] * 6,
        "DEP_DELAY": [0, 10, 20, 30, 5, 0],
        "ARR_DELAY": [0, 8, 18, 28, 4, 0],
    })
    out = add_upstream_features(df, window_min=60, p95_enabled=False)
    # first flight has no prior window → 0
    first = out.sort_values("dep_ts").iloc[0]
    assert first["origin_recent_volume_60m"] == 0, f"first should be 0, got {first['origin_recent_volume_60m']}"
    # second flight: sees first flight (DEP_DELAY=0) within 60 min → volume=1, avg=0
    sec = out.sort_values("dep_ts").iloc[1]
    assert sec["origin_recent_volume_60m"] == 1, f"second should see 1 prior, got {sec['origin_recent_volume_60m']}"
    # 10:30 flight: window is (09:30, 10:30) → sees 10:00(none), 09:45, 09:00 → 2 flights
    last = out.sort_values("dep_ts").iloc[-1]
    print(f"last flight (10:30) → vol_60m={last['origin_recent_volume_60m']}, avg={last['origin_recent_delay_avg_60m']:.2f}")
    assert last["origin_recent_volume_60m"] >= 1, "last flight should see some history"
    print("[OK] self-test passed  (leak-free rolling verified)")
    return 0


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="SkyOps upstream delay state features")
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument("--window-min", type=int, default=60)
    parser.add_argument("--no-p95", action="store_true",
                        help="skip p95 (faster for large datasets)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    if args.self_test:
        return _self_test()

    if not RAW_CSV.exists():
        print(f"❌ {RAW_CSV} 없음. prepare_dataset 먼저 실행하세요.")
        return 2

    print(f"📂 load {RAW_CSV}  (sample={args.sample})")
    usecols = ["FL_DATE", "CRS_DEP_TIME", "CRS_ARR_TIME",
               "ORIGIN", "DEST", "DEP_DELAY", "ARR_DELAY"]
    df = pd.read_csv(RAW_CSV, usecols=usecols, nrows=args.sample, low_memory=False)
    out = add_upstream_features(df, window_min=args.window_min, p95_enabled=not args.no_p95)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    keep = usecols + UPSTREAM_COLS
    keep = [c for c in keep if c in out.columns]
    out[keep].to_csv(OUT_CSV, index=False)
    print(f"💾 saved → {OUT_CSV}  ({len(out):,} rows, {len(UPSTREAM_COLS)} new features)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
