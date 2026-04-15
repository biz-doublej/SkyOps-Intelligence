"""SkyOps Iceberg writer — shared adapter (P7-A · 2026-04-15).

Provides write paths for the three medallion layers created by
iceberg_bootstrap.py:

  Bronze:  raw Kafka events as JSON payloads
  Silver:  cleaned + joined records (feature_engineering.py output)
  Gold:    model-ready aggregates + inference logs

All writers degrade gracefully when [iceberg] extras are not installed
or the catalog is unreachable — they log and become no-ops, never
blocking the calling code path.

Usage:
    from feature_store.iceberg_writer import (
        IcebergWriter, write_bronze_event, write_silver_features,
        write_gold_inference_log,
    )

    write_bronze_event("flight_position_raw", icao24="abc123", payload=event)
    write_gold_inference_log(request_id="r1", model_version="2.1.0",
                             predicted_delay_min=18.4,
                             interval_lower=6.2, interval_upper=41.0)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICEBERG_WAREHOUSE = PROJECT_ROOT / "data" / "iceberg"
NAMESPACE = os.getenv("ICEBERG_NAMESPACE", "skyops")
ICEBERG_ENABLED = os.getenv("ICEBERG_ENABLED", "0") == "1"


@lru_cache(maxsize=1)
def _catalog():
    """Lazy singleton catalog. Returns None when iceberg unavailable."""
    if not ICEBERG_ENABLED:
        return None
    try:
        from pyiceberg.catalog import load_catalog
        cat = load_catalog(
            "skyops",
            **{
                "type": "sql",
                "uri": f"sqlite:///{ICEBERG_WAREHOUSE}/catalog.db",
                "warehouse": f"file://{ICEBERG_WAREHOUSE}",
            },
        )
        logger.info("iceberg: catalog loaded from %s", ICEBERG_WAREHOUSE)
        return cat
    except Exception as e:  # noqa: BLE001
        logger.warning("iceberg: catalog unavailable (%s) — writes will be no-op", e)
        return None


class IcebergWriter:
    """Per-table writer with row buffering.

    Buffers up to `batch_size` rows then flushes to Iceberg as one
    atomic snapshot. flush() is called automatically on close().
    """

    def __init__(self, table_name: str, batch_size: int = 100):
        self.table_name = f"{NAMESPACE}.{table_name}"
        self.batch_size = batch_size
        self._buf: list[dict[str, Any]] = []
        self._table = None

    def _ensure_table(self):
        if self._table is not None:
            return self._table
        cat = _catalog()
        if cat is None:
            return None
        try:
            self._table = cat.load_table(self.table_name)
        except Exception as e:  # noqa: BLE001
            logger.warning("iceberg load_table(%s) failed: %s", self.table_name, e)
            self._table = None
        return self._table

    def append(self, row: dict[str, Any]) -> None:
        self._buf.append(row)
        if len(self._buf) >= self.batch_size:
            self.flush()

    def flush(self) -> int:
        if not self._buf:
            return 0
        tbl = self._ensure_table()
        if tbl is None:
            n = len(self._buf)
            self._buf.clear()
            return 0  # silently dropped
        try:
            import pyarrow as pa
            arrow = pa.Table.from_pylist(self._buf)
            tbl.append(arrow)
            n = len(self._buf)
            self._buf.clear()
            return n
        except Exception as e:  # noqa: BLE001
            logger.error("iceberg append to %s failed: %s", self.table_name, e)
            self._buf.clear()
            return 0

    def close(self) -> None:
        self.flush()


# ── Convenience writers (one-shot) ────────────────────────────────────

def _now_ts():
    return datetime.now(timezone.utc).replace(tzinfo=None)  # pyarrow timestamp[us]


def write_bronze_event(table_short_name: str, **fields) -> None:
    """One-shot Bronze write: schema is (event_timestamp, key, payload_json).

    table_short_name without 'bronze_' prefix. e.g. 'flight_position_raw'.
    """
    payload = fields.pop("payload", None)
    payload_json = json.dumps(payload, ensure_ascii=False, default=str) if payload else ""
    row: dict[str, Any] = {
        "event_timestamp": fields.pop("event_timestamp", _now_ts()),
        "payload_json": payload_json,
    }
    row.update(fields)
    w = IcebergWriter(f"bronze_{table_short_name}", batch_size=1)
    w.append(row)
    w.close()


def write_silver_features(tail_number: str,
                          rotation_depth: int,
                          prev_leg_arr_delay_min: float,
                          scheduled_turnaround_min: float) -> None:
    """One-shot Silver write — flight_features."""
    w = IcebergWriter("silver_flight_features", batch_size=1)
    w.append({
        "event_timestamp": _now_ts(),
        "tail_number": tail_number,
        "rotation_depth": str(rotation_depth),
        "prev_leg_arr_delay_min": str(prev_leg_arr_delay_min),
        "scheduled_turnaround_min": str(scheduled_turnaround_min),
    })
    w.close()


def write_gold_inference_log(request_id: str,
                             model_version: str,
                             predicted_delay_min: float,
                             interval_lower: float | None = None,
                             interval_upper: float | None = None) -> None:
    """One-shot Gold write — append inference event for lineage + drift analysis."""
    w = IcebergWriter("gold_inference_log", batch_size=1)
    w.append({
        "event_timestamp": _now_ts(),
        "request_id": request_id,
        "model_version": model_version,
        "predicted_delay_min": str(predicted_delay_min),
        "interval_lower": str(interval_lower) if interval_lower is not None else "",
        "interval_upper": str(interval_upper) if interval_upper is not None else "",
    })
    w.close()


def write_gold_anomaly_decision(alert_id: str,
                                anomaly_type: str,
                                severity: str,
                                flight_phase: str | None = None,
                                analyst_label: str | None = None) -> None:
    """One-shot Gold write — anomaly decision (later joined w/ analyst feedback)."""
    w = IcebergWriter("gold_anomaly_decisions", batch_size=1)
    w.append({
        "event_timestamp": _now_ts(),
        "alert_id": alert_id,
        "anomaly_type": anomaly_type,
        "severity": severity,
        "flight_phase": flight_phase or "",
        "analyst_label": analyst_label or "",
    })
    w.close()


def iceberg_health() -> dict[str, Any]:
    """Expose Iceberg availability to /health endpoint."""
    cat = _catalog()
    return {
        "enabled": ICEBERG_ENABLED,
        "loaded": cat is not None,
        "warehouse": str(ICEBERG_WAREHOUSE),
        "namespace": NAMESPACE,
    }
