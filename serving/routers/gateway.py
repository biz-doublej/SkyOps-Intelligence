"""Gateway router — /health and top-level system endpoints.

ADR-001 Migration Phase 1 (2026-04-14 P3).
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
    }
