"""Delay prediction router — /predict/delay, /predict/delay/batch.

ADR-001 Migration Phase 1 (2026-04-14 P3).
P1 Conformal Prediction interval + P1 Rotation features 포함.
"""

from __future__ import annotations

import time

import pandas as pd
from fastapi import APIRouter, HTTPException

from common.constants import ALL_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES
from common.model_store import ModelStore
from common.models import DelayRequest, DelayResponse, PredictionInterval
from common.telemetry import get_tracer

router = APIRouter(tags=["prediction"])
tracer = get_tracer("delay")


def _apply_conformal(model, X_prep, pred: float) -> PredictionInterval | None:
    """Try Conformal interval, None if calibrator missing or fails."""
    conformal = ModelStore.conformal()
    if conformal is None or X_prep is None:
        return None
    try:
        scr = conformal["scr"]
        result = scr.predict_interval(X_prep)
        y_int = result[1] if isinstance(result, tuple) else result
        if y_int.ndim == 3:
            lower = float(y_int[0, 0, 0])
            upper = float(y_int[0, 1, 0])
        else:
            lower = float(y_int[0, 0])
            upper = float(y_int[0, 1])
        return PredictionInterval(
            lower_min=round(lower, 1),
            upper_min=round(upper, 1),
            confidence=float(conformal.get("confidence_level", 0.9)),
            width_min=round(upper - lower, 1),
            method=f"split_conformal_mapie_v{conformal.get('mapie_version', '1.3.0')}",
        )
    except Exception as e:
        print(f"⚠️  Conformal prediction 실패: {e}")
        return None


def _confidence_str(pred: float) -> str:
    abs_pred = abs(pred)
    if abs_pred < 5:
        return "high"
    if abs_pred < 15:
        return "medium"
    return "low"


@router.post("/predict/delay", response_model=DelayResponse)
def predict_delay(req: DelayRequest) -> DelayResponse:
    """XGBoost + Conformal Prediction 기반 지연 예측."""
    t0 = time.time()
    with tracer.start_as_current_span("xgb_inference") as span:
        span.set_attribute("carrier_code", req.carrier_code)
        span.set_attribute("route", f"{req.origin}-{req.dest}")
        span.set_attribute("rotation_depth", req.rotation_depth)

        try:
            model = ModelStore.xgb()
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))

        row = {
            **{f: getattr(req, f) for f in NUMERIC_FEATURES},
            **{f: getattr(req, f) for f in CATEGORICAL_FEATURES},
        }
        X = pd.DataFrame([row])[ALL_FEATURES]

        try:
            if isinstance(model, dict):
                X_prep = model["pipeline_preprocessor"].transform(X)
                pred = float(model["model"].predict(X_prep)[0])
            else:
                X_prep = None
                pred = float(model.predict(X)[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"예측 오류: {e}")

        span.set_attribute("predicted_delay_min", pred)

        with tracer.start_as_current_span("conformal_interval"):
            interval = _apply_conformal(model, X_prep, pred)

    latency = (time.time() - t0) * 1000
    return DelayResponse(
        predicted_delay_min=round(pred, 1),
        is_delayed=pred >= 15.0,
        confidence=_confidence_str(pred),
        prediction_interval=interval,
        latency_ms=round(latency, 1),
    )


@router.post("/predict/delay/batch")
def predict_delay_batch(requests: list[DelayRequest]):
    """최대 100건 일괄 지연 예측 (XGBoost + Conformal interval)."""
    if len(requests) > 100:
        raise HTTPException(status_code=400, detail="최대 100건까지 가능합니다.")
    t0 = time.time()
    with tracer.start_as_current_span("xgb_batch_inference") as span:
        span.set_attribute("batch_size", len(requests))

        try:
            model = ModelStore.xgb()
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))

        rows = [
            {
                **{f: getattr(r, f) for f in NUMERIC_FEATURES},
                **{f: getattr(r, f) for f in CATEGORICAL_FEATURES},
            }
            for r in requests
        ]
        X = pd.DataFrame(rows)[ALL_FEATURES]

        try:
            if isinstance(model, dict):
                X_prep = model["pipeline_preprocessor"].transform(X)
                preds = model["model"].predict(X_prep).tolist()
            else:
                X_prep = None
                preds = model.predict(X).tolist()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"배치 예측 오류: {e}")

        # Conformal intervals for each row
        intervals: list[dict | None] = [None] * len(preds)
        conformal = ModelStore.conformal()
        if conformal is not None and X_prep is not None:
            try:
                scr = conformal["scr"]
                conf_level = float(conformal.get("confidence_level", 0.9))
                result = scr.predict_interval(X_prep)
                y_int = result[1] if isinstance(result, tuple) else result
                if y_int.ndim == 3:
                    lowers, uppers = y_int[:, 0, 0], y_int[:, 1, 0]
                else:
                    lowers, uppers = y_int[:, 0], y_int[:, 1]
                intervals = [
                    {
                        "lower_min": round(float(lo), 1),
                        "upper_min": round(float(up), 1),
                        "confidence": conf_level,
                        "width_min": round(float(up - lo), 1),
                        "method": f"split_conformal_mapie_v{conformal.get('mapie_version', '1.3.0')}",
                    }
                    for lo, up in zip(lowers, uppers)
                ]
            except Exception as e:
                print(f"⚠️  배치 Conformal prediction 실패: {e}")

    latency = (time.time() - t0) * 1000
    return {
        "predictions": [
            {
                "predicted_delay_min": round(p, 1),
                "is_delayed": p >= 15.0,
                "prediction_interval": interval,
            }
            for p, interval in zip(preds, intervals)
        ],
        "count": len(preds),
        "latency_ms": round(latency, 1),
    }
