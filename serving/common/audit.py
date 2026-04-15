"""SkyOps structured audit log (P8-F · 2026-04-15).

Immutable append-only audit events for operational/compliance traceability.
Strategic Review #8 operational requirement — ADR-001 SLO doc requires
audit log per correlation_id.

Format (JSONL, one line per event):
  {
    "ts": "2026-04-15T10:30:00+00:00",
    "event": "anomaly_feedback_submitted",
    "actor": "analyst_01",           # user id / service account
    "resource": "alert-xyz",
    "outcome": "saved|rejected|failed",
    "trace_id": "<OTel trace id>",   # for cross-ref in Jaeger
    "correlation_id": "...",
    "ip": "...",                     # optional
    "extra": { ... }                 # free-form event-specific payload
  }

Storage:
  - Default: data/audit/audit-YYYYMMDD.jsonl (rotated daily)
  - Prod: env-configurable to stdout (JSON log → Loki/ELK)

Retention:
  - Compliance (GDPR/PIPA): 5년 기본
  - Security incidents: 영구 (legal hold on demand)

Usage:
    from common.audit import audit_log
    audit_log(
        event="delay_prediction",
        actor="api_client",
        resource="request-123",
        outcome="success",
        extra={"predicted_min": 18.4},
    )
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = Path(os.getenv("AUDIT_LOG_DIR", str(PROJECT_ROOT / "data" / "audit")))
AUDIT_STDOUT = os.getenv("AUDIT_STDOUT", "0") == "1"  # production: write to stdout instead


def _trace_id() -> str:
    """Return current OTel trace id as hex string, or empty if not in span."""
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span is None:
            return ""
        ctx = span.get_span_context()
        if not ctx.is_valid:
            return ""
        return format(ctx.trace_id, "032x")
    except Exception:
        return ""


def audit_log(
    event: str,
    actor: str,
    resource: str,
    outcome: str = "success",
    correlation_id: str | None = None,
    ip: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Append one audit event. Never raises — audit failures are logged."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "actor": actor,
        "resource": resource,
        "outcome": outcome,
        "trace_id": _trace_id(),
    }
    if correlation_id:
        record["correlation_id"] = correlation_id
    if ip:
        record["ip"] = ip
    if extra:
        record["extra"] = extra

    line = json.dumps(record, ensure_ascii=False)

    if AUDIT_STDOUT:
        # Prod: one-line JSON → captured by container log driver
        print(line, flush=True)
        return

    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        fname = AUDIT_DIR / f"audit-{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        with open(fname, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:  # noqa: BLE001
        logger.error("audit write failed: %s (event=%s)", e, event)


def audit_query(event: str | None = None, actor: str | None = None,
                date: str | None = None, limit: int = 100) -> list[dict]:
    """Simple audit log reader — for internal/admin endpoints.

    date format: YYYYMMDD (defaults to today UTC).
    """
    d = date or datetime.now(timezone.utc).strftime("%Y%m%d")
    fname = AUDIT_DIR / f"audit-{d}.jsonl"
    if not fname.exists():
        return []

    rows: list[dict] = []
    for line in fname.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if event and r.get("event") != event:
            continue
        if actor and r.get("actor") != actor:
            continue
        rows.append(r)
        if len(rows) >= limit:
            break
    return rows
