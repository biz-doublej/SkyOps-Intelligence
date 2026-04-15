"""SkyOps Feast — apply + seed demo data (P6-A · 2026-04-15).

느슨한 wrapper. `feast apply` CLI 를 직접 쓸 수도 있지만, 이 스크립트는:
  1. Feature 정의 registry에 등록 (`feast apply`)
  2. offline store 용 sample parquet 를 data/feast/ 에 생성 (없을 경우)
  3. online materialize 호출 → Redis DB=1 에 최신 snapshot 기록

Run:
    python -m feature_store.apply
또는 editable install 후:
    skyops-feast-apply
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_DIR = PROJECT_ROOT / "feature_store"
DATA_DIR = PROJECT_ROOT / "data"
FEAST_DATA = DATA_DIR / "feast"


def seed_rotation_source() -> None:
    """analysis/feature_engineering.py 의 rotation feature 를 Feast-friendly parquet 로 변환.

    원본: data/processed/features.parquet (5.7M rows × 53 cols)
    출력: data/processed/rotation_features.parquet
      columns: tail_number, event_timestamp, created_timestamp, rotation_depth,
               prev_leg_arr_delay_min, scheduled_turnaround_min,
               actual_turnaround_min, is_first_leg_of_day
    """
    dst = DATA_DIR / "processed" / "rotation_features.parquet"
    src = DATA_DIR / "processed" / "features.parquet"

    if dst.exists():
        print(f"  ✓ {dst.relative_to(PROJECT_ROOT)} already present")
        return

    if src.exists():
        print(f"📦 Deriving {dst.name} from {src.name}...")
        df = pd.read_parquet(src)
        # Feast expects `event_timestamp` as datetime column
        if "fl_date" in df.columns:
            df["event_timestamp"] = pd.to_datetime(df["fl_date"])
        else:
            df["event_timestamp"] = datetime.now(timezone.utc)
        df["created_timestamp"] = datetime.now(timezone.utc)

        cols = [
            "tail_number", "event_timestamp", "created_timestamp",
            "rotation_depth", "prev_leg_arr_delay_min",
            "scheduled_turnaround_min", "actual_turnaround_min",
            "is_first_leg_of_day",
        ]
        keep = [c for c in cols if c in df.columns]
        if "tail_number" not in keep:
            print("  ⚠️ features.parquet 에 tail_number 없음 — demo 데이터로 대체")
            src = None  # trigger demo fallback
        else:
            df[keep].to_parquet(dst, index=False)
            print(f"  ✓ {len(df):,} rows → {dst.name}")
            return

    # Fallback: demo 10 tails × 3 legs
    print(f"📦 Generating demo rotation data → {dst.name}...")
    tails = [f"N{i:05d}" for i in range(10)]
    rows = []
    base_time = datetime.now(timezone.utc) - timedelta(days=1)
    for i, tail in enumerate(tails):
        for leg in range(3):
            rows.append({
                "tail_number": tail,
                "event_timestamp": base_time + timedelta(hours=leg * 3),
                "created_timestamp": datetime.now(timezone.utc),
                "rotation_depth": leg,
                "prev_leg_arr_delay_min": float(np.random.normal(5, 10)) if leg > 0 else 0.0,
                "scheduled_turnaround_min": 45.0,
                "actual_turnaround_min": 45.0 + float(np.random.normal(0, 8)),
                "is_first_leg_of_day": 1 if leg == 0 else 0,
            })
    pd.DataFrame(rows).to_parquet(dst, index=False)
    print(f"  ✓ {len(rows)} demo rows → {dst.name}")


def seed_live_position() -> None:
    """Flink processor가 실시간으로 publish할 스냅샷 parquet 의 예시본."""
    dst = FEAST_DATA / "live_position.parquet"
    if dst.exists():
        print(f"  ✓ {dst.relative_to(PROJECT_ROOT)} already present")
        return

    print(f"📦 Generating demo live position → {dst.relative_to(PROJECT_ROOT)}...")
    icaos = [f"{i:06x}" for i in range(0xA00000, 0xA0000A)]
    phases = ["TAXI", "TAKEOFF", "CLIMB", "CRUISE", "DESCENT", "APPROACH", "LANDING"]
    rows = []
    now = datetime.now(timezone.utc)
    for icao in icaos:
        rows.append({
            "icao24": icao,
            "event_timestamp": now,
            "baro_altitude": float(np.random.uniform(0, 38000)),
            "velocity": float(np.random.uniform(0, 500)),
            "vertical_rate": float(np.random.uniform(-1500, 1500)),
            "on_ground": int(np.random.choice([0, 1])),
            "flight_phase": str(np.random.choice(phases)),
            "phase_confidence": float(np.random.uniform(0.6, 1.0)),
        })
    pd.DataFrame(rows).to_parquet(dst, index=False)
    print(f"  ✓ {len(rows)} demo rows")


def seed_airport_congestion() -> None:
    dst = FEAST_DATA / "airport_congestion.parquet"
    if dst.exists():
        print(f"  ✓ {dst.relative_to(PROJECT_ROOT)} already present")
        return
    print(f"📦 Generating demo airport congestion → {dst.relative_to(PROJECT_ROOT)}...")
    airports = ["RKSI", "RKSS", "RKPC", "KATL", "KJFK", "EGLL", "RJAA", "VHHH"]
    rows = []
    now = datetime.now(timezone.utc)
    for ap in airports:
        for hr_offset in range(6):
            rows.append({
                "airport_code": ap,
                "event_timestamp": now - timedelta(hours=hr_offset),
                "hourly_departures": int(np.random.randint(10, 60)),
                "hourly_arrivals": int(np.random.randint(10, 60)),
                "avg_taxi_out_min": float(np.random.uniform(8, 22)),
                "avg_taxi_in_min": float(np.random.uniform(4, 12)),
            })
    pd.DataFrame(rows).to_parquet(dst, index=False)
    print(f"  ✓ {len(rows)} demo rows")


def seed_notam_impact() -> None:
    dst = FEAST_DATA / "notam_impact.parquet"
    if dst.exists():
        print(f"  ✓ {dst.relative_to(PROJECT_ROOT)} already present")
        return
    print(f"📦 Generating demo NOTAM impact → {dst.relative_to(PROJECT_ROOT)}...")
    airports = ["RKSI", "RKSS", "KATL", "KJFK", "EGLL"]
    rows = []
    now = datetime.now(timezone.utc)
    for ap in airports:
        runway_closures = int(np.random.choice([0, 0, 0, 1]))
        navaid_outages = int(np.random.choice([0, 1, 2]))
        rows.append({
            "airport_code": ap,
            "event_timestamp": now,
            "active_notam_count": int(np.random.randint(3, 15)),
            "runway_closure_count": runway_closures,
            "navaid_outage_count": navaid_outages,
            "notam_impact_score": min(1.0,
                0.1 + runway_closures * 0.5 + navaid_outages * 0.15),
        })
    pd.DataFrame(rows).to_parquet(dst, index=False)
    print(f"  ✓ {len(rows)} demo rows")


def main() -> int:
    print("=" * 65)
    print("  SkyOps Feast — apply + seed (P6-A)")
    print("=" * 65)

    FEAST_DATA.mkdir(parents=True, exist_ok=True)

    # 1. Seed sample parquet files
    seed_rotation_source()
    seed_live_position()
    seed_airport_congestion()
    seed_notam_impact()

    # 2. Feast apply (registry write)
    try:
        from feast import FeatureStore
    except ImportError:
        print("\n❌ feast 미설치. `pip install -e \".[feast]\"` 실행 후 재시도")
        return 1

    from .feature_views import ALL_ENTITIES, ALL_FEATURE_SERVICES, ALL_FEATURE_VIEWS

    print(f"\n📝 Applying feature definitions to {REPO_DIR}...")
    fs = FeatureStore(repo_path=str(REPO_DIR))
    fs.apply(
        objects=list(ALL_ENTITIES) + list(ALL_FEATURE_VIEWS) + list(ALL_FEATURE_SERVICES),
        partial=False,
    )
    print(f"  ✓ Registered {len(ALL_ENTITIES)} entities, "
          f"{len(ALL_FEATURE_VIEWS)} feature views, "
          f"{len(ALL_FEATURE_SERVICES)} feature services")

    # 3. Summary
    print("\n" + "=" * 65)
    print("  ✅ Feast apply complete")
    print("=" * 65)
    print(f"  Registry: {REPO_DIR}/../data/feast/registry.db")
    print(f"  Offline:  file (parquet)")
    print(f"  Online:   Redis localhost:6379 db=1")
    print("\n  Next:")
    print(f"    python -m feature_store.materialize")
    return 0


if __name__ == "__main__":
    sys.exit(main())
