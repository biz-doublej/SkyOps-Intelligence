"""Redis client + helpers for SkyOps serving layer.

ADR-001 Migration Phase 1 — extracted from serving/api.py (2026-04-14 P3).
"""

from __future__ import annotations

import os
from typing import Any, Optional

_redis_client: Optional[Any] = None


def get_redis():
    """Lazy Redis connection. None if redis package missing or connection fails.

    외부에서는 항상 None 체크 후 사용 (Redis는 optional).
    """
    global _redis_client
    if _redis_client is None:
        try:
            import redis

            _redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # connection test
            _redis_client.ping()
        except Exception as e:
            print(f"⚠️  Redis unavailable: {e}")
            _redis_client = None
    return _redis_client


def safe_float(value) -> Optional[float]:
    """Cast to float, None if missing or NaN."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f
