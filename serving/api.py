"""SkyOps Intelligence FastAPI — thin entry point.

ADR-001 Migration Phase 1 (2026-04-14 P3).

기존 1120-line monolith가 `serving/common/` + `serving/routers/` 로 분해됨.
본 파일은 app 초기화 + middleware + router 등록만 담당.

실행:
    python serving/api.py
    uvicorn serving.api:app --host 0.0.0.0 --port 8000 --reload

환경 변수 (주요):
    VLLM_BASE_URL          vLLM OpenAI-compatible endpoint
    LLM_MODEL_ID           served model name
    REDIS_HOST / REDIS_PORT / REDIS_DB
    OTEL_ENABLED, OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT
"""

from __future__ import annotations

import sys
from pathlib import Path

# serving/ 디렉토리를 path에 추가 (common, routers 임포트 가능)
_SERVING_DIR = Path(__file__).resolve().parent
if str(_SERVING_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVING_DIR))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.constants import API_VERSION, VLLM_BASE_URL
from common.telemetry import setup_tracing
from routers import anomaly, delay, gateway, notification, rag, streaming

# ──────────────────────────────────────────────────────────────────────
# FastAPI 앱 초기화
# ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SkyOps Intelligence API",
    description=(
        "항공 지연 예측 · 이상 탐지 · AI 관제 어시스턴트 서비스. "
        "ADR-001 Migration Phase 1 완료 (router 분해). "
        "P0 TimeSeriesSplit, P1 Conformal+Rotation, P2 Phase-aware+RAGAs, P3 OTel+Router."
    ),
    version=API_VERSION,
)

# CORS (현재 전면 개방 — ADR-001 Phase 2에서 도메인 화이트리스트로 축소 예정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus 메트릭 (기존 유지, OTel과 병행) ────────────────────────
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app)
    _prometheus_enabled = True
except ImportError:
    _prometheus_enabled = False

# ── OpenTelemetry 계측 (P3 · 2026-04-14) ──────────────────────────────
_otel_enabled = setup_tracing(app)

# ── Router 등록 ──────────────────────────────────────────────────────
app.include_router(gateway.router)
app.include_router(delay.router)
app.include_router(anomaly.router)
app.include_router(rag.router)
app.include_router(notification.router)
app.include_router(streaming.router)


# ──────────────────────────────────────────────────────────────────────
# 단독 실행 / entry point (ADR-001 Phase 2 · 2026-04-14)
# ──────────────────────────────────────────────────────────────────────
def main():
    """CLI entry point — pyproject.toml의 `skyops-api`로 연결."""
    import argparse

    parser = argparse.ArgumentParser(description="SkyOps Intelligence FastAPI 서버")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", default=False)
    args = parser.parse_args()

    print("=" * 60)
    print(f"  SkyOps Intelligence API v{API_VERSION}")
    print(f"  http://{args.host}:{args.port}")
    print(f"  Docs: http://localhost:{args.port}/docs")
    print(f"  vLLM: {VLLM_BASE_URL}")
    print(f"  Prometheus: {_prometheus_enabled}")
    print(f"  OpenTelemetry: {_otel_enabled}")
    print("=" * 60)

    uvicorn.run(
        "api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=str(_SERVING_DIR),
    )


if __name__ == "__main__":
    main()
