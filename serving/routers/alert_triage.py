"""
SkyOps — Alert Triage router — v2.2.0 · ADR-007 D2 (Phase 3 split).

`anomaly.py` 가 730+ 줄로 비대해져 "운영 triage" 관심사를 별도 router 로 분리.
core anomaly detection 은 anomaly.py 에, 피드백/라벨링은 anomaly.py 에
그대로 두고, **실시간 운영자용 top-K 큐** 만 여기로 이관.

설계 원칙 (ADR-006 D4 에서 상속):
  - `/active-learning/next` 와 엄격히 구분 (uncertainty-only vs severity×unc)
  - Read-only 엔드포인트 → RBAC 는 viewer 이상이면 허용 (지금은 공개)
  - Redis 조회만 — 모델 호출 없음, p99 < 20 ms 목표
"""
from __future__ import annotations

import json as _json
from datetime import datetime, timezone

from fastapi import APIRouter

from common.anomaly_feedback_io import (
    SEVERITY_WEIGHT,
    load_labeled_alert_ids,
    parse_ts_to_age,
    uncertainty_score,
)
from common.constants import REDIS_ANOMALY_STREAM
from common.models import TriageItem, TriageResponse
from common.redis_client import get_redis
from common.telemetry import get_tracer

router = APIRouter(tags=["triage"])
tracer = get_tracer("alert_triage")


@router.get("/alerts/triage", response_model=TriageResponse)
def get_alert_triage(limit: int = 10, include_labeled: bool = False) -> TriageResponse:
    """Real-time analyst triage queue — composite = severity × (1 + uncertainty).

    v2.1.10 · ADR-006 D4 (원본) · v2.2.0 · ADR-007 D2 (router 분리).

    Active Learning 과의 차이:
      - `/active-learning/next` → "label what we're unsure about" — uncertainty 최대화
      - `/alerts/triage`        → "what should analyst SEE FIRST" — severity × uncertainty

    Args:
        limit: top-K (1..100, default 10)
        include_labeled: True 면 이미 라벨된 alert 도 포함

    Returns:
        items sorted by composite_score desc.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    limit = max(1, min(100, int(limit)))

    with tracer.start_as_current_span("triage.query") as span:
        span.set_attribute("limit", limit)
        span.set_attribute("include_labeled", include_labeled)

        r = get_redis()
        if r is None:
            return TriageResponse(
                items=[], total_considered=0, returned_count=0,
                generated_at=generated_at,
            )

        try:
            raw_events = r.lrange(REDIS_ANOMALY_STREAM, 0, 499)
        except Exception as e:  # noqa: BLE001
            print(f"⚠️  /alerts/triage Redis 조회 실패: {e}")
            return TriageResponse(
                items=[], total_considered=0, returned_count=0,
                generated_at=generated_at,
            )

        labeled = set() if include_labeled else load_labeled_alert_ids()

        candidates: list[TriageItem] = []
        for raw in raw_events:
            try:
                evt = _json.loads(raw)
            except _json.JSONDecodeError:
                continue
            alert_id = evt.get("alert_id", "")
            if not alert_id:
                continue
            already_labeled = alert_id in labeled
            if already_labeled and not include_labeled:
                continue

            score = float(evt.get("anomaly_score", -0.15) or -0.15)
            severity = str(evt.get("severity", "LOW")).upper()
            sev_w = SEVERITY_WEIGHT.get(severity, 0.2)
            unc = uncertainty_score(score, severity)
            composite = sev_w * (1.0 + unc)

            candidates.append(TriageItem(
                alert_id=alert_id,
                anomaly_score=score,
                anomaly_type=evt.get("anomaly_type", "UNKNOWN"),
                severity=severity,
                severity_weight=sev_w,
                uncertainty_score=unc,
                composite_score=round(composite, 4),
                flight_phase=evt.get("flight_phase"),
                icao24=evt.get("icao24"),
                callsign=evt.get("callsign"),
                description=str(evt.get("description", ""))[:300],
                alert_age_sec=round(
                    parse_ts_to_age(evt.get("event_timestamp") or evt.get("ts")), 1,
                ),
                already_labeled=already_labeled,
            ))

        candidates.sort(key=lambda x: x.composite_score, reverse=True)
        top = candidates[:limit]
        span.set_attribute("total_considered", len(candidates))
        span.set_attribute("returned_count", len(top))

    return TriageResponse(
        items=top,
        total_considered=len(candidates),
        returned_count=len(top),
        generated_at=generated_at,
    )
