"""Shared helpers for anomaly feedback / active-learning / triage routers.

v2.2.0 · ADR-007 D2 (Phase 3 router split).

anomaly.py 가 730+ 줄로 비대해져 /alerts/triage 를 별도 router 로 분리했고,
그 과정에서 두 router 가 공통으로 쓰던 함수들을 여기로 추출.

- `_load_labeled_alert_ids()` — feedback.jsonl 에서 이미 라벨된 alert_id 집합
- `_uncertainty_score(score, severity, threshold)` — 임계값 근접성 기반 불확실성
- `parse_ts_to_age(raw)` — ISO8601 / epoch → 경과 초 계산

공용 상수:
- `SEVERITY_WEIGHT` — triage composite score 가중치

함수명은 router 코드에서 쓰던 그대로 유지 (import 만 바꾸면 됨).
"""
from __future__ import annotations

import json as _json
import math
from datetime import datetime, timezone
from typing import Any

from .constants import FEEDBACK_FILE, IF_SCORE_THRESHOLD


SEVERITY_WEIGHT: dict[str, float] = {
    "CRITICAL": 1.0,
    "HIGH": 0.7,
    "MEDIUM": 0.4,
    "LOW": 0.2,
}


def load_labeled_alert_ids() -> set[str]:
    """Return set of alert_ids already labeled in feedback.jsonl."""
    if not FEEDBACK_FILE.exists():
        return set()
    labeled: set[str] = set()
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = _json.loads(line)
                    if rec.get("alert_id"):
                        labeled.add(rec["alert_id"])
                except _json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return labeled


def load_labeled_records() -> list[dict[str, Any]]:
    """Full rows (not just IDs) — used by Bandit v2 prior."""
    if not FEEDBACK_FILE.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in FEEDBACK_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(_json.loads(line))
            except Exception:
                continue
    except Exception:
        pass
    return out


def uncertainty_score(
    anomaly_score: float,
    severity: str,
    threshold: float = IF_SCORE_THRESHOLD,
) -> float:
    """Distance to threshold + severity modifier, clipped to [0, 1].

    - |score - threshold| 작을수록 uncertain (1 에 가까움)
    - HIGH/CRITICAL → base × 0.3 (label 우선순위 낮음)
    - LOW → base × 1.2
    - MEDIUM → base × 1.0
    """
    distance = abs(anomaly_score - threshold)
    base = float(math.exp(-distance * 5))  # 5x scale

    sev = (severity or "LOW").upper()
    if sev in ("HIGH", "CRITICAL"):
        base *= 0.3
    elif sev == "LOW":
        base *= 1.2
    return float(min(1.0, max(0.0, base)))


def parse_ts_to_age(ts_raw: Any) -> float:
    """Return age in seconds. Supports ISO8601 string, epoch float, None."""
    if ts_raw is None:
        return 0.0
    try:
        if isinstance(ts_raw, (int, float)):
            epoch = float(ts_raw)
        else:
            s = str(ts_raw)
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            epoch = datetime.fromisoformat(s).timestamp()
        return max(0.0, datetime.now(timezone.utc).timestamp() - epoch)
    except Exception:
        return 0.0
