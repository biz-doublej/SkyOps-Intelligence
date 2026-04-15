"""SkyOps OpenLineage emitter (P7-B · 2026-04-15).

Emits OpenLineage events that link MLflow runs to their input datasets
and output model versions.

Why?
----
Strategic Review #5 said dataset → feature → model → deployment must be
traceable. MLflow alone tracks model metadata but not which Iceberg
snapshot was used. OpenLineage standardizes this: every training run
emits START + COMPLETE events with input datasets (Iceberg URIs +
snapshot IDs) and output model URI.

Configuration:
  OPENLINEAGE_URL=http://marquez:5000   # or any OL-compatible backend
  OPENLINEAGE_NAMESPACE=skyops          # default

Marquez (open-source OpenLineage backend) — runs locally:
  docker run --rm -p 5000:5000 marquezproject/marquez:latest

Usage:
    from monitoring.lineage import emit_train_run_start, emit_train_run_complete

    run_id = emit_train_run_start(
        job_name="xgboost_delay_train",
        inputs=[("skyops.silver_flight_features", snapshot_id)],
    )
    # ... train ...
    emit_train_run_complete(
        run_id=run_id,
        job_name="xgboost_delay_train",
        outputs=[("skyops.gold_inference_log", None)],
        model_version="2.1.1",
        metrics={"val_rmse": 22.61, "test_r2": 0.4328},
    )

Graceful fallback when openlineage-python missing — returns None.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

OL_URL = os.getenv("OPENLINEAGE_URL", "")
OL_NAMESPACE = os.getenv("OPENLINEAGE_NAMESPACE", "skyops")
OL_PRODUCER_URI = "https://github.com/biz-doublej/SkyOps-Intelligence"


def _client():
    """Return OpenLineage client or None if disabled/unavailable."""
    if not OL_URL:
        return None
    try:
        from openlineage.client import OpenLineageClient
        return OpenLineageClient(url=OL_URL)
    except ImportError:
        logger.debug("openlineage-python not installed — lineage events skipped")
        return None
    except Exception as e:  # noqa: BLE001
        logger.warning("openlineage client init failed: %s", e)
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dataset(name: str, snapshot_id: int | None = None) -> dict[str, Any]:
    """Build a dataset descriptor with optional Iceberg snapshot version facet."""
    facets = {}
    if snapshot_id is not None:
        # OpenLineage version facet — track the exact snapshot
        facets["version"] = {
            "_producer": OL_PRODUCER_URI,
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DatasetVersionDatasetFacet.json",
            "datasetVersion": str(snapshot_id),
        }
    return {"namespace": OL_NAMESPACE, "name": name, "facets": facets}


def emit_train_run_start(job_name: str,
                         inputs: list[tuple[str, int | None]] | None = None) -> str | None:
    """Emit START event. Returns run_id (UUID) or None if disabled."""
    client = _client()
    if client is None:
        return None
    try:
        from openlineage.client.run import Job, Run, RunEvent, RunState
        run_id = str(uuid.uuid4())
        event = RunEvent(
            eventType=RunState.START,
            eventTime=_now_iso(),
            run=Run(runId=run_id),
            job=Job(namespace=OL_NAMESPACE, name=job_name),
            inputs=[_dataset(n, sid) for n, sid in (inputs or [])],
            outputs=[],
            producer=OL_PRODUCER_URI,
        )
        client.emit(event)
        logger.info("openlineage START emitted: %s (run=%s)", job_name, run_id)
        return run_id
    except Exception as e:  # noqa: BLE001
        logger.warning("openlineage emit START failed: %s", e)
        return None


def emit_train_run_complete(run_id: str | None,
                            job_name: str,
                            outputs: list[tuple[str, int | None]] | None = None,
                            model_version: str | None = None,
                            metrics: dict[str, float] | None = None) -> None:
    """Emit COMPLETE event with output datasets + run-level metric facet."""
    if not run_id:
        return
    client = _client()
    if client is None:
        return
    try:
        from openlineage.client.run import Job, Run, RunEvent, RunState
        run_facets: dict[str, Any] = {}
        if metrics or model_version:
            run_facets["skyops_model"] = {
                "_producer": OL_PRODUCER_URI,
                "_schemaURL": OL_PRODUCER_URI + "/blob/dev/docs/event_model.md",
                "model_version": model_version,
                "metrics": metrics or {},
            }
        event = RunEvent(
            eventType=RunState.COMPLETE,
            eventTime=_now_iso(),
            run=Run(runId=run_id, facets=run_facets),
            job=Job(namespace=OL_NAMESPACE, name=job_name),
            inputs=[],
            outputs=[_dataset(n, sid) for n, sid in (outputs or [])],
            producer=OL_PRODUCER_URI,
        )
        client.emit(event)
        logger.info("openlineage COMPLETE emitted: %s", job_name)
    except Exception as e:  # noqa: BLE001
        logger.warning("openlineage emit COMPLETE failed: %s", e)


def lineage_health() -> dict[str, Any]:
    """Expose OpenLineage availability."""
    return {
        "enabled": bool(OL_URL),
        "client_loaded": _client() is not None,
        "url": OL_URL or None,
        "namespace": OL_NAMESPACE,
    }
