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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── 경로 설정 ─────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(__file__).parent.parent
MODELS_DIR     = PROJECT_ROOT / "data" / "models"
XGB_MODEL_PATH = MODELS_DIR / "xgboost_best.pkl"
IF_MODEL_PATH  = MODELS_DIR / "isolation_forest.pkl"

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


class DelayResponse(BaseModel):
    predicted_delay_min: float
    is_delayed:          bool   # ≥15분이면 지연
    confidence:          str    # "high" / "medium" / "low"
    latency_ms:          float


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

    - **predicted_delay_min**: 예측 지연 시간(분)
    - **is_delayed**: 15분 이상 지연 여부
    - **confidence**: 예측 신뢰도 (절댓값 기반 휴리스틱)
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
            pred = float(model.predict(X)[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예측 오류: {e}")

    latency = (time.time() - t0) * 1000

    # 신뢰도 휴리스틱: ±5분 이내 high, ±15분 medium, 그 외 low
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
            answer=result["answer"],
            sources=result["sources"],
            latency_ms=result["latency_ms"],
            rag_used=True,
        )

    else:
        # 직접 vLLM 호출 (RAG 없이)
        import json
        import urllib.request as ur

        SYSTEM = (
            "당신은 AviationLLM입니다. 항공 관제사를 돕는 AI 어시스턴트입니다. "
            "정확하고 간결하게 한국어로 답변하며, ATC 전문 용어를 사용합니다."
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
            answer=answer,
            sources=[],
            latency_ms=round(latency, 1),
            rag_used=False,
        )


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
        preds = model.predict(X).tolist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 예측 오류: {e}")

    latency = (time.time() - t0) * 1000
    return {
        "predictions": [
            {
                "predicted_delay_min": round(p, 1),
                "is_delayed": p >= 15.0,
            }
            for p in preds
        ],
        "count":      len(preds),
        "latency_ms": round(latency, 1),
    }


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
