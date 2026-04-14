"""
10주차 Step 6 — SkyOps Intelligence FastAPI 서버

엔드포인트:
  POST /predict/delay   — XGBoost 지연 예측
  POST /detect/anomaly  — Isolation Forest 이상 탐지
  POST /chat            — AviationLLM RAG 어시스턴트
  GET  /health          — 헬스 체크
  GET  /metrics         — Prometheus 메트릭

실행:
    uvicorn serving.api:app --host 0.0.0.0 --port 8000 --reload
    # 또는
    python serving/api.py

요구사항:
    pip install fastapi uvicorn prometheus-fastapi-instrumentator
"""

from __future__ import annotations

import os
import pickle
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── 경로 설정 ─────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(__file__).parent.parent
MODELS_DIR     = PROJECT_ROOT / "data" / "models"
XGB_MODEL_PATH = MODELS_DIR / "xgboost_best.pkl"
IF_MODEL_PATH  = MODELS_DIR / "isolation_forest.pkl"
CONFORMAL_PATH = MODELS_DIR / "conformal_calibrator.pkl"  # P1 · Conformal Prediction (2026-04-14)

# ── Feature 정의 (analysis/ 스크립트와 동일) ──────────────────────────
NUMERIC_FEATURES = [
    "dep_hour", "dep_minute", "dep_dayofweek", "dep_month",
    "dep_dayofyear", "is_weekend",
    "distance_miles", "sched_elapsed_min",
    "prev_dep_delay_min", "prev_arr_delay_min", "is_prev_delayed",
    "origin_hourly_departures", "dest_hourly_arrivals",
    "dep_month_weather_score",
    "origin_weather_hist_delay", "dest_weather_hist_delay",
    "carrier_hist_delay", "origin_hist_delay",
    "dest_hist_delay", "route_hist_delay",
    # Rotation features (P1 · 2026-04-14)
    "rotation_depth", "prev_leg_arr_delay_min",
    "scheduled_turnaround_min", "actual_turnaround_min",
    "is_first_leg_of_day",
]
CATEGORICAL_FEATURES = ["carrier_code", "origin", "dest"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

IF_FEATURES = [
    "dep_hour", "dep_dayofweek",
    "distance_miles", "sched_elapsed_min",
    "prev_dep_delay_min", "prev_arr_delay_min", "is_prev_delayed",
    "origin_hourly_departures", "dest_hourly_arrivals",
    "dep_month_weather_score",
    "origin_weather_hist_delay", "dest_weather_hist_delay",
    "carrier_hist_delay", "origin_hist_delay",
    "dest_hist_delay", "route_hist_delay",
]

# IF 이상 판정 임계값 (6주차 기준)
IF_SCORE_THRESHOLD = -0.1   # score < threshold → 이상

# ── vLLM 설정 ─────────────────────────────────────────────────────────
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
LLM_MODEL_ID  = os.getenv("LLM_MODEL_ID",  "aviation-llm")


# ── 한국어 후처리 (Qwen2.5 중국어 코드스위칭 대응) ────────────────────
import re as _re

def _clean_korean(text: str) -> str:
    """중국어/영어 문장이 섞인 응답에서 한국어 문장만 추출."""
    if not text:
        return text
    # 중국어 유니코드 범위: CJK Unified (4E00-9FFF), 확장 등
    # 한국어: 가-힣 (AC00-D7A3), ㄱ-ㅎ, ㅏ-ㅣ
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        # 줄에서 중국어 비율 계산
        chars = [c for c in stripped if not c.isspace() and not c.isdigit() and c not in ".,;:!?()-/·•[]{}\"'"]
        if not chars:
            cleaned.append(stripped)
            continue
        chinese_count = sum(1 for c in chars if "\u4e00" <= c <= "\u9fff")
        korean_count = sum(1 for c in chars if "\uac00" <= c <= "\ud7a3" or "\u3131" <= c <= "\u3163")
        total = len(chars)
        # 중국어가 30% 이상이면 해당 줄 제거
        if total > 0 and chinese_count / total > 0.3:
            # 줄 앞부분에 한국어가 있으면 그 부분만 살리기
            parts = _re.split(r"[\u4e00-\u9fff]{3,}", stripped)
            if parts and parts[0].strip():
                kr_part = parts[0].strip().rstrip(".,;:!? ")
                if kr_part and any("\uac00" <= c <= "\ud7a3" for c in kr_part):
                    cleaned.append(kr_part)
            continue
        cleaned.append(stripped)

    result = "\n".join(cleaned).strip()
    # 끝이 이상하게 잘린 경우 마지막 완성 문장까지만
    if result and result[-1] not in ".!?。다요":
        last_period = max(result.rfind("."), result.rfind("다."), result.rfind("요."), result.rfind("세요."))
        if last_period > len(result) * 0.3:
            result = result[:last_period + 1]
    return result if result else text


# ──────────────────────────────────────────────────────────────────────
# FastAPI 앱 초기화
# ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SkyOps Intelligence API",
    description="항공 지연 예측 · 이상 탐지 · AI 관제 어시스턴트 서비스",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus 메트릭 (선택적) ────────────────────────────────────────
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
    _prometheus_enabled = True
except ImportError:
    _prometheus_enabled = False


# ──────────────────────────────────────────────────────────────────────
# 모델 싱글톤 로더
# ──────────────────────────────────────────────────────────────────────

class _ModelStore:
    _xgb = None
    _if  = None
    _rag = None
    _conformal = None  # P1 · Conformal Prediction (2026-04-14)

    @classmethod
    def xgb(cls):
        if cls._xgb is None:
            if not XGB_MODEL_PATH.exists():
                raise RuntimeError(f"XGBoost 모델 없음: {XGB_MODEL_PATH}")
            with open(XGB_MODEL_PATH, "rb") as f:
                cls._xgb = pickle.load(f)
        return cls._xgb

    @classmethod
    def isolation_forest(cls):
        if cls._if is None:
            if not IF_MODEL_PATH.exists():
                raise RuntimeError(f"Isolation Forest 모델 없음: {IF_MODEL_PATH}")
            with open(IF_MODEL_PATH, "rb") as f:
                cls._if = pickle.load(f)
        return cls._if

    @classmethod
    def conformal(cls):
        """MAPIE SplitConformalRegressor calibrator.

        analysis/conformal_calibration.py에서 생성. 없으면 None 반환(fallback).
        Strategic Review 2번 병목 — uncertainty-aware inference.
        """
        if cls._conformal is None and CONFORMAL_PATH.exists():
            try:
                with open(CONFORMAL_PATH, "rb") as f:
                    cls._conformal = pickle.load(f)
            except Exception as e:
                # 호환성 문제 있어도 전체 서빙은 계속
                print(f"⚠️  Conformal calibrator 로드 실패 ({e}) → fallback to point estimate")
                cls._conformal = None
        return cls._conformal

    @classmethod
    def rag(cls):
        if cls._rag is None:
            # 지연 로딩: vLLM이 없어도 나머지 엔드포인트는 동작
            import sys, importlib
            # serving 디렉터리를 경로에 추가
            serving_dir = str(Path(__file__).parent)
            if serving_dir not in sys.path:
                sys.path.insert(0, serving_dir)
            # parent도 추가 (from serving.05_rag_chain import ... 방식 대비)
            project_dir = str(PROJECT_ROOT)
            if project_dir not in sys.path:
                sys.path.insert(0, project_dir)
            # 05_rag_chain 은 숫자로 시작하므로 importlib 사용
            spec = importlib.util.spec_from_file_location(
                "rag_chain_module",
                Path(__file__).parent / "05_rag_chain.py",
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls._rag = mod.rag_chain
        return cls._rag


# ──────────────────────────────────────────────────────────────────────
# Pydantic 요청/응답 모델
# ──────────────────────────────────────────────────────────────────────

class DelayRequest(BaseModel):
    """지연 예측 요청 — NUMERIC + CATEGORICAL features"""
    # 필수 수치형
    dep_hour:                   float = Field(..., ge=0, le=23, description="출발 시(0-23)")
    dep_minute:                 float = Field(0,   ge=0, le=59)
    dep_dayofweek:              float = Field(..., ge=0, le=6,  description="요일(0=월)")
    dep_month:                  float = Field(..., ge=1, le=12)
    dep_dayofyear:              float = Field(1,   ge=1, le=366)
    is_weekend:                 float = Field(0,   ge=0, le=1)
    distance_miles:             float = Field(..., gt=0)
    sched_elapsed_min:          float = Field(..., gt=0)
    prev_dep_delay_min:         float = Field(0.0)
    prev_arr_delay_min:         float = Field(0.0)
    is_prev_delayed:            float = Field(0,   ge=0, le=1)
    origin_hourly_departures:   float = Field(10.0, ge=0)
    dest_hourly_arrivals:       float = Field(10.0, ge=0)
    dep_month_weather_score:    float = Field(0.0)
    origin_weather_hist_delay:  float = Field(0.0)
    dest_weather_hist_delay:    float = Field(0.0)
    carrier_hist_delay:         float = Field(0.0)
    origin_hist_delay:          float = Field(0.0)
    dest_hist_delay:            float = Field(0.0)
    route_hist_delay:           float = Field(0.0)
    # Rotation features (P1 · 2026-04-14) — 모두 default로 optional
    rotation_depth:             int   = Field(0,    ge=0, description="해당 일자 내 몇 번째 leg (0=첫째)")
    prev_leg_arr_delay_min:     float = Field(0.0,  description="같은 tail의 직전 leg 실도착 지연")
    scheduled_turnaround_min:   float = Field(60.0, description="예정 turnaround (분)")
    actual_turnaround_min:      float = Field(60.0, description="실제 turnaround (분)")
    is_first_leg_of_day:        int   = Field(1,    ge=0, le=1, description="당일 첫 leg 여부")
    # 범주형
    carrier_code: str = Field("OO",  description="항공사 코드")
    origin:       str = Field("ATL", description="출발 공항 IATA")
    dest:         str = Field("LAX", description="도착 공항 IATA")

    class Config:
        json_schema_extra = {
            "example": {
                "dep_hour": 8, "dep_minute": 30, "dep_dayofweek": 1,
                "dep_month": 6, "dep_dayofyear": 160, "is_weekend": 0,
                "distance_miles": 2475, "sched_elapsed_min": 330,
                "prev_dep_delay_min": 20, "prev_arr_delay_min": 15,
                "is_prev_delayed": 1,
                "origin_hourly_departures": 18, "dest_hourly_arrivals": 14,
                "dep_month_weather_score": 0.3,
                "origin_weather_hist_delay": 8.2, "dest_weather_hist_delay": 5.1,
                "carrier_hist_delay": 12.4,
                "origin_hist_delay": 10.5, "dest_hist_delay": 7.8,
                "route_hist_delay": 9.3,
                "carrier_code": "DL", "origin": "JFK", "dest": "LAX",
            }
        }


class PredictionInterval(BaseModel):
    """Conformal Prediction interval (P1 · 2026-04-14)."""
    lower_min:        float = Field(..., description="Lower bound of prediction (minutes)")
    upper_min:        float = Field(..., description="Upper bound of prediction (minutes)")
    confidence:       float = Field(..., ge=0.0, le=1.0, description="Coverage confidence (e.g. 0.9)")
    width_min:        float = Field(..., description="upper - lower (minutes)")
    method:           str   = Field("split_conformal_mapie_v1.3", description="Calibration method")


class DelayResponse(BaseModel):
    predicted_delay_min:  float
    is_delayed:           bool   # ≥15분이면 지연
    confidence:           str    # "high" / "medium" / "low" (기존 휴리스틱, backward compat)
    prediction_interval:  Optional[PredictionInterval] = None  # P1 · Conformal (optional, 없으면 fallback)
    latency_ms:           float


# `from __future__ import annotations` 로 인한 forward reference 해소
DelayResponse.model_rebuild()


class AnomalyRequest(BaseModel):
    """이상 탐지 요청 — IF_FEATURES"""
    dep_hour:                   float = Field(..., ge=0, le=23)
    dep_dayofweek:              float = Field(..., ge=0, le=6)
    distance_miles:             float = Field(..., gt=0)
    sched_elapsed_min:          float = Field(..., gt=0)
    prev_dep_delay_min:         float = Field(0.0)
    prev_arr_delay_min:         float = Field(0.0)
    is_prev_delayed:            float = Field(0,   ge=0, le=1)
    origin_hourly_departures:   float = Field(10.0, ge=0)
    dest_hourly_arrivals:       float = Field(10.0, ge=0)
    dep_month_weather_score:    float = Field(0.0)
    origin_weather_hist_delay:  float = Field(0.0)
    dest_weather_hist_delay:    float = Field(0.0)
    carrier_hist_delay:         float = Field(0.0)
    origin_hist_delay:          float = Field(0.0)
    dest_hist_delay:            float = Field(0.0)
    route_hist_delay:           float = Field(0.0)
    # 선택 메타
    flight_id: Optional[str] = Field(None, description="항공편 식별자 (로그용)")

    class Config:
        json_schema_extra = {
            "example": {
                "dep_hour": 14, "dep_dayofweek": 4,
                "distance_miles": 2450, "sched_elapsed_min": 310,
                "prev_dep_delay_min": 87, "prev_arr_delay_min": 92,
                "is_prev_delayed": 1,
                "origin_hourly_departures": 5, "dest_hourly_arrivals": 4,
                "dep_month_weather_score": 0.8,
                "origin_weather_hist_delay": 18.5, "dest_weather_hist_delay": 14.2,
                "carrier_hist_delay": 22.1,
                "origin_hist_delay": 20.0, "dest_hist_delay": 16.0,
                "route_hist_delay": 19.5,
                "flight_id": "AAR123",
            }
        }


class AnomalyResponse(BaseModel):
    flight_id:    Optional[str]
    anomaly_score: float          # IF decision_function 값 (음수일수록 이상)
    is_anomaly:   bool
    risk_level:   str             # "critical" / "warning" / "normal"
    latency_ms:   float


class ChatRequest(BaseModel):
    question:  str  = Field(..., min_length=1, description="관제사 질문")
    use_rag:   bool = Field(True,  description="RAG 컨텍스트 사용 여부")
    max_tokens: int = Field(512,  ge=64, le=2048)

    class Config:
        json_schema_extra = {
            "example": {
                "question": "항공기 이상 연료 소비 시 관제사는 어떻게 대응해야 하나요?",
                "use_rag": True,
                "max_tokens": 512,
            }
        }


class ChatResponse(BaseModel):
    answer:     str
    sources:    list[dict[str, Any]]
    latency_ms: float
    rag_used:   bool


# ──────────────────────────────────────────────────────────────────────
# 헬스 체크
# ──────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "models": {
            "xgboost":         XGB_MODEL_PATH.exists(),
            "isolation_forest": IF_MODEL_PATH.exists(),
        },
        "prometheus": _prometheus_enabled,
        "vllm_url":   VLLM_BASE_URL,
    }


# ──────────────────────────────────────────────────────────────────────
# POST /predict/delay — XGBoost 지연 예측
# ──────────────────────────────────────────────────────────────────────

@app.post("/predict/delay", response_model=DelayResponse, tags=["prediction"])
def predict_delay(req: DelayRequest):
    """
    XGBoost 모델로 항공편 출발 지연을 예측합니다.

    - **predicted_delay_min**: 예측 지연 시간(분) — point estimate
    - **is_delayed**: 15분 이상 지연 여부
    - **confidence**: 예측 신뢰도 (절댓값 기반 휴리스틱, legacy)
    - **prediction_interval**: Conformal Prediction 기반 90% 신뢰구간 (P1 · 2026-04-14)
    """
    t0 = time.time()
    try:
        model = _ModelStore.xgb()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # 입력 DataFrame 구성
    row = {
        **{f: getattr(req, f) for f in NUMERIC_FEATURES},
        **{f: getattr(req, f) for f in CATEGORICAL_FEATURES},
    }
    X = pd.DataFrame([row])[ALL_FEATURES]

    try:
        # pkl은 {"pipeline_preprocessor": ..., "model": xgb} 형태로 저장됨
        if isinstance(model, dict):
            X_prep = model["pipeline_preprocessor"].transform(X)
            pred = float(model["model"].predict(X_prep)[0])
        else:
            X_prep = None
            pred = float(model.predict(X)[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예측 오류: {e}")

    # ── Conformal Prediction interval (P1 · 2026-04-14) ────────────────
    interval = None
    conformal = _ModelStore.conformal()
    if conformal is not None and X_prep is not None:
        try:
            scr = conformal["scr"]
            result = scr.predict_interval(X_prep)
            # MAPIE 1.x returns ndarray (n, 2) or tuple (pred, interval)
            if isinstance(result, tuple):
                _, y_int = result
            else:
                y_int = result
            # y_int: (1, 2) or (1, 2, 1)
            if y_int.ndim == 3:
                lower = float(y_int[0, 0, 0])
                upper = float(y_int[0, 1, 0])
            else:
                lower = float(y_int[0, 0])
                upper = float(y_int[0, 1])
            interval = PredictionInterval(
                lower_min=round(lower, 1),
                upper_min=round(upper, 1),
                confidence=float(conformal.get("confidence_level", 0.9)),
                width_min=round(upper - lower, 1),
                method=f"split_conformal_mapie_v{conformal.get('mapie_version', '1.3.0')}",
            )
        except Exception as e:
            # conformal 실패 시에도 point estimate는 반환
            print(f"⚠️  Conformal prediction 실패: {e}")

    latency = (time.time() - t0) * 1000

    # 신뢰도 휴리스틱 (legacy): ±5분 이내 high, ±15분 medium, 그 외 low
    abs_pred = abs(pred)
    if abs_pred < 5:
        confidence = "high"
    elif abs_pred < 15:
        confidence = "medium"
    else:
        confidence = "low"

    return DelayResponse(
        predicted_delay_min=round(pred, 1),
        is_delayed=pred >= 15.0,
        confidence=confidence,
        prediction_interval=interval,
        latency_ms=round(latency, 1),
    )


# ──────────────────────────────────────────────────────────────────────
# POST /detect/anomaly — Isolation Forest 이상 탐지
# ──────────────────────────────────────────────────────────────────────

@app.post("/detect/anomaly", response_model=AnomalyResponse, tags=["anomaly"])
def detect_anomaly(req: AnomalyRequest):
    """
    Isolation Forest 모델로 항공편 이상을 탐지합니다.

    - **anomaly_score**: IF decision_function 출력 (낮을수록 이상)
    - **is_anomaly**: IF_SCORE_THRESHOLD 기준 이상 여부
    - **risk_level**: critical (score < -0.2) / warning (-0.2 ~ -0.1) / normal
    """
    t0 = time.time()
    try:
        model = _ModelStore.isolation_forest()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    row = {f: getattr(req, f) for f in IF_FEATURES}
    X = pd.DataFrame([row])[IF_FEATURES]

    try:
        score = float(model.decision_function(X)[0])
        pred  = int(model.predict(X)[0])   # -1=이상, 1=정상
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이상 탐지 오류: {e}")

    latency = (time.time() - t0) * 1000

    is_anomaly = (pred == -1) or (score < IF_SCORE_THRESHOLD)

    if score < -0.2:
        risk_level = "critical"
    elif score < IF_SCORE_THRESHOLD:
        risk_level = "warning"
    else:
        risk_level = "normal"

    return AnomalyResponse(
        flight_id=req.flight_id,
        anomaly_score=round(score, 4),
        is_anomaly=is_anomaly,
        risk_level=risk_level,
        latency_ms=round(latency, 1),
    )


# ──────────────────────────────────────────────────────────────────────
# POST /chat — AviationLLM RAG 어시스턴트
# ──────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse, tags=["llm"])
def chat(req: ChatRequest):
    """
    AviationLLM + ChromaDB RAG 기반 관제 어시스턴트입니다.

    - `use_rag=true`: ChromaDB에서 FAA/ICAO/NOTAM 컨텍스트를 검색 후 LLM에 전달
    - `use_rag=false`: RAG 없이 LLM에 직접 질문 (vLLM이 실행 중이어야 합니다)
    """
    t0 = time.time()

    if req.use_rag:
        # RAG 체인 사용
        try:
            chain = _ModelStore.rag()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"RAG 초기화 실패: {e}")

        try:
            result = chain.query(req.question)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG 응답 오류: {e}")

        return ChatResponse(
            answer=_clean_korean(result["answer"]),
            sources=result["sources"],
            latency_ms=result["latency_ms"],
            rag_used=True,
        )

    else:
        # 직접 vLLM 호출 (RAG 없이)
        import json
        import urllib.request as ur

        SYSTEM = (
            "당신은 AviationLLM — 대한민국 항공 관제사를 돕는 AI 어시스턴트입니다. "
            "반드시 한국어로만 답변하세요. 절대 영어, 중국어 등 다른 언어를 사용하지 마세요. "
            "ATC 전문 용어(Squawk, Go-Around, NOTAM, FL 등)는 원어 그대로 사용하되 설명은 한국어로 하세요. "
            "불필요한 인사말 없이 바로 본론으로 답변하세요."
        )
        payload = {
            "model": LLM_MODEL_ID,
            "messages": [
                {"role": "system",  "content": SYSTEM},
                {"role": "user",    "content": req.question},
            ],
            "max_tokens": req.max_tokens,
            "temperature": 0.2,
        }
        data = json.dumps(payload).encode()
        request = ur.Request(
            f"{VLLM_BASE_URL}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with ur.urlopen(request, timeout=120) as r:
                resp = json.loads(r.read())
            answer = resp["choices"][0]["message"]["content"]
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"vLLM 호출 실패: {e}")

        latency = (time.time() - t0) * 1000
        return ChatResponse(
            answer=_clean_korean(answer),
            sources=[],
            latency_ms=round(latency, 1),
            rag_used=False,
        )


# ──────────────────────────────────────────────────────────────────────
# POST /explain/anomaly — 이상 탐지 LLM 자동 설명
# ──────────────────────────────────────────────────────────────────────

class AnomalyExplainRequest(BaseModel):
    callsign: str = Field(..., description="항공편 콜사인")
    anomaly_type: str = Field(..., description="이상 유형 (ALTITUDE_SPIKE, VELOCITY_SPIKE, PATH_DEVIATION)")
    severity: str = Field(..., description="심각도 (LOW, MEDIUM, HIGH)")
    description: str = Field(..., description="이상 설명")
    altitude_m: float = Field(0)
    velocity_m_s: float = Field(0)


@app.post("/explain/anomaly", tags=["llm"])
def explain_anomaly(req: AnomalyExplainRequest):
    """이상 탐지 이벤트를 LLM으로 자동 설명 생성."""
    import json as _j
    import urllib.request as ur

    TYPE_KR = {"ALTITUDE_SPIKE": "고도 급변", "VELOCITY_SPIKE": "속도 이상", "PATH_DEVIATION": "경로 이탈"}
    SEV_KR = {"LOW": "낮음", "MEDIUM": "중간", "HIGH": "높음"}

    SYSTEM = (
        "당신은 대한민국 항공 관제사를 돕는 전문 AI입니다.\n"
        "규칙:\n"
        "- 반드시 한국어로만 답변하세요. 중국어 절대 금지. 영어도 금지.\n"
        "- 항공 약어(ICAO, AIM, FL 등)만 영문 허용. 나머지는 모두 한국어.\n"
        "- 형식: 1) 상황 요약 2) 원인 분석 3) 권고 대응 절차\n"
        "- 반드시 3문장 이내로 간결하게 답변을 마치세요."
    )
    user_msg = (
        f"아래 이상 탐지 결과를 관제사에게 한국어로 설명해 주세요.\n\n"
        f"항공편: {req.callsign}\n"
        f"이상 유형: {TYPE_KR.get(req.anomaly_type, req.anomaly_type)}\n"
        f"심각도: {SEV_KR.get(req.severity, req.severity)}\n"
        f"상세 내용: {req.description}\n"
        f"현재 고도: {req.altitude_m}미터, 현재 속도: {req.velocity_m_s}미터/초"
    )

    t0 = time.time()
    payload = {
        "model": LLM_MODEL_ID,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 200,
        "temperature": 0.2,
    }
    data = _j.dumps(payload).encode()
    request = ur.Request(
        f"{VLLM_BASE_URL}/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with ur.urlopen(request, timeout=120) as r:
            resp = _j.loads(r.read())
        answer = resp["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"vLLM 호출 실패: {e}")

    answer = _clean_korean(answer)
    return {"explanation": answer, "latency_ms": round((time.time() - t0) * 1000, 1)}


# ──────────────────────────────────────────────────────────────────────
# POST /generate/announcement — 승객 안내문 자동 생성
# ──────────────────────────────────────────────────────────────────────

class AnnouncementRequest(BaseModel):
    flight_number: str = Field(..., description="항공편명 (예: KE081)")
    delay_type: str = Field(..., description="지연 유형 (weather, maintenance, traffic, crew, other)")
    delay_minutes: int = Field(..., ge=0, description="예상 지연 시간 (분)")
    details: str = Field("", description="추가 상세 정보")


@app.post("/generate/announcement", tags=["llm"])
def generate_announcement(req: AnnouncementRequest):
    """승객 안내문 자동 생성."""
    import json as _j
    import urllib.request as ur

    DELAY_LABELS = {
        "weather": "기상 악화", "maintenance": "기체 정비",
        "traffic": "항공 교통 혼잡", "crew": "승무원 사유", "other": "운항 사정",
    }
    reason = DELAY_LABELS.get(req.delay_type, req.delay_type)

    SYSTEM = (
        "당신은 대한민국 항공사의 승객 안내방송 작성 전문 AI입니다.\n"
        "규칙:\n"
        "- 한국어 안내문만 작성하세요. 중국어 사용 금지.\n"
        "- 정중하고 전문적인 어조를 사용하세요.\n"
        "- '승객 여러분'으로 시작하세요.\n"
        "- 3~4문장으로 간결하게 작성하세요.\n"
        "- 안전과 양해 감사 표현을 포함하세요."
    )
    user_msg = (
        f"아래 상황에 맞는 승객 안내방송문을 한국어로 작성해 주세요.\n\n"
        f"항공편명: {req.flight_number}\n"
        f"지연 사유: {reason}\n"
        f"예상 지연 시간: 약 {req.delay_minutes}분\n"
        f"추가 정보: {req.details or '없음'}"
    )

    t0 = time.time()
    payload = {
        "model": LLM_MODEL_ID,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 500,
        "temperature": 0.3,
    }
    data = _j.dumps(payload).encode()
    request = ur.Request(
        f"{VLLM_BASE_URL}/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with ur.urlopen(request, timeout=120) as r:
            resp = _j.loads(r.read())
        answer = resp["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"vLLM 호출 실패: {e}")

    answer = _clean_korean(answer)
    return {"announcement": answer, "latency_ms": round((time.time() - t0) * 1000, 1)}


# ──────────────────────────────────────────────────────────────────────
# 일괄 엔드포인트 — /predict/delay/batch
# ──────────────────────────────────────────────────────────────────────

@app.post("/predict/delay/batch", tags=["prediction"])
def predict_delay_batch(requests: list[DelayRequest]):
    """최대 100건 일괄 지연 예측 (XGBoost)."""
    if len(requests) > 100:
        raise HTTPException(status_code=400, detail="최대 100건까지 가능합니다.")
    t0 = time.time()
    try:
        model = _ModelStore.xgb()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    rows = [
        {**{f: getattr(r, f) for f in NUMERIC_FEATURES},
         **{f: getattr(r, f) for f in CATEGORICAL_FEATURES}}
        for r in requests
    ]
    X = pd.DataFrame(rows)[ALL_FEATURES]

    try:
        # pipeline dict 대응 (xgboost_model.py가 저장한 형태)
        if isinstance(model, dict):
            X_prep = model["pipeline_preprocessor"].transform(X)
            preds = model["model"].predict(X_prep).tolist()
        else:
            X_prep = None
            preds = model.predict(X).tolist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 예측 오류: {e}")

    # ── Conformal Prediction intervals (P1 · 2026-04-14) ───────────────
    intervals = [None] * len(preds)
    conformal = _ModelStore.conformal()
    if conformal is not None and X_prep is not None:
        try:
            scr = conformal["scr"]
            conf_level = float(conformal.get("confidence_level", 0.9))
            result = scr.predict_interval(X_prep)
            if isinstance(result, tuple):
                _, y_int = result
            else:
                y_int = result
            if y_int.ndim == 3:
                lowers = y_int[:, 0, 0]
                uppers = y_int[:, 1, 0]
            else:
                lowers = y_int[:, 0]
                uppers = y_int[:, 1]
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
            # fallback: intervals는 모두 None 유지

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
        "count":      len(preds),
        "latency_ms": round(latency, 1),
    }


# ──────────────────────────────────────────────────────────────────────
# 대시보드용 REST + WebSocket 엔드포인트
# ──────────────────────────────────────────────────────────────────────

import asyncio
import json as _json

# Redis 연결 (선택적 — 없으면 Mock 응답)
_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                decode_responses=True,
            )
            _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default


def _read_aircraft_from_redis() -> list[dict]:
    """Redis에서 항공기 위치 데이터 조회."""
    r = _get_redis()
    if r is None:
        return []
    try:
        cutoff = time.time() - 600  # 최근 10분
        icao_list = r.zrangebyscore("skyops:aircraft:latest", cutoff, "+inf")
        result = []
        for icao in icao_list[:200]:
            state = r.hgetall(f"skyops:aircraft:state:{icao}")
            if not state or not state.get("latitude"):
                continue
            result.append({
                "icao24": icao,
                "callsign": state.get("callsign", ""),
                "latitude": _safe_float(state.get("latitude")),
                "longitude": _safe_float(state.get("longitude")),
                "baro_altitude": _safe_float(state.get("baro_altitude")),
                "velocity": _safe_float(state.get("velocity")),
                "on_ground": state.get("on_ground", "false") == "true",
                "true_track": _safe_float(state.get("true_track")),
                "vertical_rate": _safe_float(state.get("vertical_rate")),
                "updated_at": _safe_float(state.get("updated_at")),
            })
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []


def _read_anomalies_from_redis(limit: int = 50) -> list[dict]:
    """Redis에서 최근 이상 탐지 이벤트 조회."""
    r = _get_redis()
    if r is None:
        return []
    try:
        raw = r.lrange("skyops:anomaly:stream", 0, limit - 1)
        return [_json.loads(item) for item in raw if item]
    except Exception:
        return []


@app.get("/aircraft/live", tags=["dashboard"])
def get_aircraft_live():
    """실시간 항공기 위치 (Redis 조회)."""
    return _read_aircraft_from_redis()


@app.get("/aircraft/h3", tags=["dashboard"])
def get_aircraft_h3(resolution: int = 5):
    """항공기 위치를 H3 헥사곤으로 집계하여 반환."""
    try:
        import h3
    except ImportError:
        raise HTTPException(status_code=500, detail="h3 라이브러리 미설치: pip install h3")

    aircraft = _read_aircraft_from_redis()
    if not aircraft:
        return []

    hex_counts: dict[str, dict] = {}
    for a in aircraft:
        lat, lng = a.get("latitude", 0), a.get("longitude", 0)
        if lat == 0 and lng == 0:
            continue
        h3_index = h3.latlng_to_cell(lat, lng, resolution)
        if h3_index not in hex_counts:
            cell_lat, cell_lng = h3.cell_to_latlng(h3_index)
            hex_counts[h3_index] = {
                "hex_id": h3_index,
                "latitude": cell_lat,
                "longitude": cell_lng,
                "count": 0,
                "avg_altitude": 0,
                "avg_velocity": 0,
                "callsigns": [],
            }
        entry = hex_counts[h3_index]
        entry["count"] += 1
        entry["callsigns"].append(a.get("callsign", ""))
        entry["avg_altitude"] += a.get("baro_altitude", 0)
        entry["avg_velocity"] += a.get("velocity", 0)

    for entry in hex_counts.values():
        n = entry["count"]
        if n > 0:
            entry["avg_altitude"] = round(entry["avg_altitude"] / n, 1)
            entry["avg_velocity"] = round(entry["avg_velocity"] / n, 1)
        entry["callsigns"] = entry["callsigns"][:5]

    return list(hex_counts.values())


@app.get("/anomaly/recent", tags=["dashboard"])
def get_anomaly_recent(limit: int = 50):
    """최근 이상 탐지 이벤트 (Redis 조회)."""
    return _read_anomalies_from_redis(limit)


@app.websocket("/ws/aircraft")
async def ws_aircraft(websocket: WebSocket):
    """3초 간격 항공기 위치 WebSocket push."""
    await websocket.accept()
    try:
        while True:
            data = _read_aircraft_from_redis()
            await websocket.send_json(data)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@app.websocket("/ws/anomalies")
async def ws_anomalies(websocket: WebSocket):
    """1초 간격 신규 이상 이벤트 WebSocket push."""
    await websocket.accept()
    last_count = 0
    try:
        while True:
            r = _get_redis()
            if r:
                current_count = r.llen("skyops:anomaly:stream") or 0
                if current_count > last_count:
                    new_count = current_count - last_count
                    data = _read_anomalies_from_redis(new_count)
                    await websocket.send_json(data)
                    last_count = current_count
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────
# 단독 실행
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SkyOps Intelligence FastAPI 서버")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", default=False)
    args = parser.parse_args()

    print("=" * 60)
    print("  SkyOps Intelligence API 서버")
    print(f"  http://{args.host}:{args.port}")
    print(f"  Docs: http://localhost:{args.port}/docs")
    print(f"  vLLM: {VLLM_BASE_URL}")
    print("=" * 60)

    uvicorn.run(
        "api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=str(Path(__file__).parent),
    )
