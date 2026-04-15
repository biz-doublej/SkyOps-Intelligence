"""SkyOps Feast Feature Views (P6-A).

P1 rotation features + P2 phase + P5+ SWIM NOTAM을 Feature View로 정리.

Why Feature Views?
------------------
Strategic Review 병목 #6 (training-serving skew). 학습 시
`feature_engineering.py` 에서 계산한 rotation feature 와 서빙 시
`serving/routers/delay.py`에서 DelayRequest로 받는 것이 완전히 같은
정의여야 한다. Feature View 가 이 "하나의 진실"을 강제한다.

Training:
  fs.get_historical_features(entity_df=train_df, features=[...])
  → point-in-time correct join

Serving:
  fs.get_online_features(entity_rows=[{tail: 'N12345'}], features=[...])
  → Redis 에서 같은 feature 를 꺼내오기
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from feast import FeatureView, Field, FileSource
from feast.types import Float32, Int32, String

from .entities import aircraft_entity, airport_entity, flight_entity, icao24_entity


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# ── Data Sources ──────────────────────────────────────────────────────

# P1 Rotation features (precomputed, offline)
rotation_source = FileSource(
    name="rotation_source",
    path=str(DATA_DIR / "processed" / "rotation_features.parquet"),
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
    description="Per-leg rotation features from analysis/feature_engineering.py",
)

# Live ADS-B (streaming — materialized periodically)
live_position_source = FileSource(
    name="live_position_source",
    path=str(DATA_DIR / "feast" / "live_position.parquet"),
    timestamp_field="event_timestamp",
    description="Latest position snapshot per icao24 (from Flink processor)",
)

# Airport congestion (rolling window)
airport_congestion_source = FileSource(
    name="airport_congestion_source",
    path=str(DATA_DIR / "feast" / "airport_congestion.parquet"),
    timestamp_field="event_timestamp",
    description="Hourly departure/arrival counts per airport",
)

# NOTAM operational impact (from swim_subscriber output)
notam_impact_source = FileSource(
    name="notam_impact_source",
    path=str(DATA_DIR / "feast" / "notam_impact.parquet"),
    timestamp_field="event_timestamp",
    description="Airport-level NOTAM impact score from FAA SWIM feed",
)


# ── Feature Views ─────────────────────────────────────────────────────

flight_rotation_fv = FeatureView(
    name="flight_rotation",
    entities=[aircraft_entity],
    ttl=timedelta(hours=24),
    schema=[
        Field(name="rotation_depth", dtype=Int32,
              description="# of legs this tail has flown today"),
        Field(name="prev_leg_arr_delay_min", dtype=Float32,
              description="Previous leg arrival delay in minutes"),
        Field(name="scheduled_turnaround_min", dtype=Float32,
              description="Scheduled gate turnaround time"),
        Field(name="actual_turnaround_min", dtype=Float32,
              description="Actual gate turnaround time (rolling avg)"),
        Field(name="is_first_leg_of_day", dtype=Int32,
              description="1 if first leg of calendar day"),
    ],
    source=rotation_source,
    online=True,
    tags={
        "owner": "skyops-ml-team",
        "domain": "delay_prediction",
        "source_sprint": "P1",
    },
    description="P1 Rotation feature set — drives Test R² from 0.10 to 0.43",
)


live_position_fv = FeatureView(
    name="live_position",
    entities=[icao24_entity],
    ttl=timedelta(minutes=5),  # ADS-B는 short TTL
    schema=[
        Field(name="baro_altitude", dtype=Float32),
        Field(name="velocity", dtype=Float32),
        Field(name="vertical_rate", dtype=Float32),
        Field(name="on_ground", dtype=Int32),
        Field(name="flight_phase", dtype=String,
              description="TAXI/TAKEOFF/CLIMB/CRUISE/DESCENT/APPROACH/LANDING"),
        Field(name="phase_confidence", dtype=Float32),
    ],
    source=live_position_source,
    online=True,
    tags={
        "owner": "skyops-streaming-team",
        "domain": "anomaly_detection",
        "source_sprint": "P2",
    },
    description="Live ADS-B snapshot — ML phase classifier output",
)


airport_congestion_fv = FeatureView(
    name="airport_congestion",
    entities=[airport_entity],
    ttl=timedelta(hours=6),
    schema=[
        Field(name="hourly_departures", dtype=Int32),
        Field(name="hourly_arrivals", dtype=Int32),
        Field(name="avg_taxi_out_min", dtype=Float32),
        Field(name="avg_taxi_in_min", dtype=Float32),
    ],
    source=airport_congestion_source,
    online=True,
    tags={
        "owner": "skyops-ml-team",
        "domain": "delay_prediction",
        "source_sprint": "P1",
    },
    description="Rolling-hour airport congestion metrics",
)


notam_impact_fv = FeatureView(
    name="notam_impact",
    entities=[airport_entity],
    ttl=timedelta(hours=12),
    schema=[
        Field(name="active_notam_count", dtype=Int32),
        Field(name="runway_closure_count", dtype=Int32),
        Field(name="navaid_outage_count", dtype=Int32),
        Field(name="notam_impact_score", dtype=Float32,
              description="Weighted operational impact 0-1"),
    ],
    source=notam_impact_source,
    online=True,
    tags={
        "owner": "skyops-streaming-team",
        "domain": "operational_context",
        "source_sprint": "P5+",
    },
    description="Aggregated NOTAM operational impact from FAA SWIM",
)


# ── Feature Services (bundles used by a specific model/endpoint) ──────

from feast import FeatureService  # noqa: E402

delay_prediction_v2 = FeatureService(
    name="delay_prediction_v2",
    features=[
        flight_rotation_fv,
        airport_congestion_fv,
        notam_impact_fv,
    ],
    description="Features consumed by /predict/delay (XGBoost + Conformal)",
    tags={"model": "xgboost_best", "version": "2.1.0"},
)

anomaly_detection_v2 = FeatureService(
    name="anomaly_detection_v2",
    features=[
        live_position_fv,
    ],
    description="Features consumed by /detect/anomaly (per-phase IF)",
    tags={"model": "isolation_forest_per_phase", "version": "2.1.0"},
)


# Public registry (consumed by `feast apply` and `feature_store.apply`)
ALL_ENTITIES = [aircraft_entity, airport_entity, flight_entity, icao24_entity]
ALL_FEATURE_VIEWS = [
    flight_rotation_fv,
    live_position_fv,
    airport_congestion_fv,
    notam_impact_fv,
]
ALL_FEATURE_SERVICES = [delay_prediction_v2, anomaly_detection_v2]
