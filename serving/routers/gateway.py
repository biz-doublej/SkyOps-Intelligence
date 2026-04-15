"""Gateway router — /health and top-level system endpoints.

ADR-001 Migration Phase 1 (2026-04-14 P3).
P6-A (2026-04-15): Feast health wiring.
"""

from __future__ import annotations

from fastapi import APIRouter

from common.constants import (
    API_VERSION,
    CONFORMAL_PATH,
    IF_MODEL_PATH,
    VLLM_BASE_URL,
    XGB_MODEL_PATH,
)

router = APIRouter(tags=["system"])


def _feast_health() -> dict:
    """Attempt feast_health() without hard dependency on the Feast install."""
    try:
        from feature_store.client import feast_health  # type: ignore
        return feast_health()
    except Exception:  # noqa: BLE001
        return {"enabled": False, "loaded": False, "repo_path": None}


@router.get("/health")
def health():
    return {
        "status": "ok",
        "version": API_VERSION,
        "models": {
            "xgboost": XGB_MODEL_PATH.exists(),
            "isolation_forest": IF_MODEL_PATH.exists(),
            "conformal": CONFORMAL_PATH.exists(),  # P1 (2026-04-14)
        },
        "vllm_url": VLLM_BASE_URL,
        "feast": _feast_health(),  # P6-A (2026-04-15)
    }
