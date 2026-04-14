"""Anomaly detection router — /detect/anomaly, /anomaly/feedback.

ADR-001 Migration Phase 1 (2026-04-14 P3).
P2 Phase-aware detection + Redis debounce + Analyst feedback stub.
"""

from __future__ import annotations

import json as _json
import time
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException

from common.constants import (
    FEEDBACK_DIR,
    FEEDBACK_FILE,
    IF_FEATURES,
    IF_SCORE_THRESHOLD,
    REDIS_AIRCRAFT_PHASE,
    REDIS_ANOMALY_DEBOUNCE,
)
from common.model_store import ModelStore
from common.models import (
    AnomalyFeedbackRequest,
    AnomalyFeedbackResponse,
    AnomalyRequest,
    AnomalyResponse,
)
from common.redis_client import get_redis
from common.telemetry import get_tracer

router = APIRouter(tags=["anomaly"])
tracer = get_tracer("anomaly")


@router.post("/detect/anomaly", response_model=AnomalyResponse)
def detect_anomaly(req: AnomalyRequest) -> AnomalyResponse:
    """Isolation Forest 이상 탐지 (P2 phase-aware + debounce)."""
    t0 = time.time()
    with tracer.start_as_current_span("if_inference") as span:
        try:
            model = ModelStore.isolation_forest()
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))

        row = {f: getattr(req, f) for f in IF_FEATURES}
        X = pd.DataFrame([row])[IF_FEATURES]

        try:
            score = float(model.decision_function(X)[0])
            pred = int(model.predict(X)[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"이상 탐지 오류: {e}")

        span.set_attribute("anomaly_score", score)
        span.set_attribute("is_anomaly", pred == -1)

        is_anomaly = (pred == -1) or (score < IF_SCORE_THRESHOLD)

        if score < -0.2:
            risk_level = "critical"
        elif score < IF_SCORE_THRESHOLD:
            risk_level = "warning"
        else:
            risk_level = "normal"

        # P2 · flight_phase + debounce
        flight_phase = None
        phase_confidence = None
        suppressed = False
        suppress_reason = None

        if req.flight_id:
            r = get_redis()
            if r is not None:
                try:
                    phase_data = r.hgetall(REDIS_AIRCRAFT_PHASE.format(req.flight_id))
                    if phase_data:
                        flight_phase = phase_data.get("phase")
                        conf_str = phase_data.get("confidence")
                        if conf_str:
                            phase_confidence = float(conf_str)
                except Exception:
                    pass

                if is_anomaly and risk_level != "critical":
                    dkey = REDIS_ANOMALY_DEBOUNCE.format(req.flight_id, "IF_DETECT")
                    try:
                        if r.exists(dkey):
                            suppressed = True
                            suppress_reason = "debounce_60s_same_flight"
                        else:
                            r.setex(dkey, 60, "1")
                    except Exception:
                        pass

        if flight_phase:
            span.set_attribute("flight_phase", flight_phase)
        if suppressed:
            span.set_attribute("suppressed", True)

    latency = (time.time() - t0) * 1000
    return AnomalyResponse(
        flight_id=req.flight_id,
        anomaly_score=round(score, 4),
        is_anomaly=is_anomaly,
        risk_level=risk_level,
        latency_ms=round(latency, 1),
        flight_phase=flight_phase,
        phase_confidence=phase_confidence,
        suppressed=suppressed,
        suppress_reason=suppress_reason,
    )


@router.post("/anomaly/feedback", response_model=AnomalyFeedbackResponse)
def submit_anomaly_feedback(req: AnomalyFeedbackRequest) -> AnomalyFeedbackResponse:
    """Analyst feedback stub → data/analyst_feedback/feedback.jsonl (P2)."""
    valid_labels = {"true_positive", "false_positive", "uncertain"}
    if req.label not in valid_labels:
        raise HTTPException(
            status_code=400,
            detail=f"label은 {valid_labels} 중 하나여야 합니다.",
        )

    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "alert_id": req.alert_id,
        "label": req.label,
        "note": req.note,
        "labeled_by": req.labeled_by,
        "labeled_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(_json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 저장 실패: {e}")

    return AnomalyFeedbackResponse(
        saved=True,
        alert_id=req.alert_id,
        file_path=str(FEEDBACK_FILE),
    )
