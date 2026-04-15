"""SkyOps Feast — thin adapter for the serving layer (P6-A · 2026-04-15).

serving/routers/delay.py, anomaly.py 가 직접 feast 를 import 하지 않고
이 adapter 를 쓴다. Feast 미설치/미설정인 환경에서도 service 가 기동되도록
graceful fallback을 제공한다.

Usage:
    from feature_store.client import get_online_rotation_features

    rot = get_online_rotation_features(tail_number="N12345")
    # rot is dict with 5 keys (or None for missing)

Design:
- LRU cache on FeatureStore handle
- Single-process (serving worker) safe
- 요청당 <5ms 부가 latency (Redis round-trip)
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_DIR = Path(__file__).resolve().parent
FEAST_ENABLED = os.getenv("FEAST_ENABLED", "0") == "1"


@lru_cache(maxsize=1)
def _store() -> Any | None:
    """Lazy singleton FeatureStore. Returns None if Feast not available."""
    if not FEAST_ENABLED:
        return None
    try:
        from feast import FeatureStore
        fs = FeatureStore(repo_path=str(REPO_DIR))
        logger.info("feast: FeatureStore loaded from %s", REPO_DIR)
        return fs
    except Exception as e:  # noqa: BLE001
        logger.warning("feast: FeatureStore unavailable (%s) — falling back", e)
        return None


def get_online_rotation_features(tail_number: str) -> dict[str, Any] | None:
    """Return 5 rotation features for this tail, or None if unavailable."""
    fs = _store()
    if fs is None or not tail_number:
        return None
    try:
        result = fs.get_online_features(
            features=[
                "flight_rotation:rotation_depth",
                "flight_rotation:prev_leg_arr_delay_min",
                "flight_rotation:scheduled_turnaround_min",
                "flight_rotation:actual_turnaround_min",
                "flight_rotation:is_first_leg_of_day",
            ],
            entity_rows=[{"tail_number": tail_number}],
        ).to_dict()
        # result is {feature_name: [value, ...], entity_key: [...]}
        return {
            k.split(":")[-1]: (v[0] if v else None)
            for k, v in result.items()
            if ":" in k
        }
    except Exception as e:  # noqa: BLE001
        logger.debug("feast rotation fetch failed for %s: %s", tail_number, e)
        return None


def get_online_airport_context(airport_code: str) -> dict[str, Any] | None:
    """Return congestion + NOTAM impact for an airport, or None."""
    fs = _store()
    if fs is None or not airport_code:
        return None
    try:
        result = fs.get_online_features(
            features=[
                "airport_congestion:hourly_departures",
                "airport_congestion:hourly_arrivals",
                "airport_congestion:avg_taxi_out_min",
                "airport_congestion:avg_taxi_in_min",
                "notam_impact:active_notam_count",
                "notam_impact:runway_closure_count",
                "notam_impact:navaid_outage_count",
                "notam_impact:notam_impact_score",
            ],
            entity_rows=[{"airport_code": airport_code}],
        ).to_dict()
        return {
            k.split(":")[-1]: (v[0] if v else None)
            for k, v in result.items()
            if ":" in k
        }
    except Exception as e:  # noqa: BLE001
        logger.debug("feast airport fetch failed for %s: %s", airport_code, e)
        return None


def feast_health() -> dict[str, Any]:
    """Expose Feast availability to /health endpoint."""
    fs = _store()
    return {
        "enabled": FEAST_ENABLED,
        "loaded": fs is not None,
        "repo_path": str(REPO_DIR),
    }
