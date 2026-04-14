"""OpenTelemetry setup for SkyOps serving layer.

Task B · 2026-04-14 P3 — Strategic Review 8번 병목 (observability).

지원 exporter:
  - OTLP gRPC (localhost:4317 기본, env override 가능)
  - Console (dev 환경 디버깅)

환경 변수:
  OTEL_ENABLED               "1" | "0" (default: "1")
  OTEL_SERVICE_NAME          default: "skyops-api"
  OTEL_EXPORTER_OTLP_ENDPOINT default: "http://localhost:4317"
  OTEL_CONSOLE_EXPORTER      "1" | "0" (default: "1" — dev debug 용)
  OTEL_OTLP_EXPORTER         "1" | "0" (default: "0" — Collector 없으면 차단)

사용:
    from common.telemetry import setup_tracing, get_tracer
    setup_tracing(app)
    tracer = get_tracer("delay")
    with tracer.start_as_current_span("xgb_inference") as span:
        span.set_attribute("model.version", "v2026-04-14")
        ...
"""

from __future__ import annotations

import logging
import os
from typing import Optional

_initialized = False
_tracer_provider = None

log = logging.getLogger(__name__)


def _bool_env(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip() not in ("0", "false", "False", "")


def setup_tracing(app, service_name: Optional[str] = None) -> bool:
    """Initialize OpenTelemetry tracing + FastAPI instrumentation.

    Returns True if tracing was enabled, False if disabled / setup failed.
    실패 시에도 예외를 raise 하지 않음 — graceful degradation.
    """
    global _initialized, _tracer_provider

    if _initialized:
        return True

    if not _bool_env("OTEL_ENABLED", "1"):
        log.info("OTEL_ENABLED=0 → OpenTelemetry 비활성화")
        _initialized = True
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
    except ImportError as e:
        log.warning(f"OpenTelemetry import 실패 ({e}) → 비활성화 fallback")
        _initialized = True
        return False

    svc = service_name or os.getenv("OTEL_SERVICE_NAME", "skyops-api")
    version = os.getenv("OTEL_SERVICE_VERSION", "2.0.0")

    resource = Resource.create({
        SERVICE_NAME: svc,
        SERVICE_VERSION: version,
        "service.namespace": "skyops",
        "deployment.environment": os.getenv("DEPLOY_ENV", "dev"),
    })

    _tracer_provider = TracerProvider(resource=resource)

    # Console exporter (dev 디버깅)
    if _bool_env("OTEL_CONSOLE_EXPORTER", "1"):
        try:
            _tracer_provider.add_span_processor(
                BatchSpanProcessor(ConsoleSpanExporter())
            )
            log.info("✅ OTel Console exporter 등록")
        except Exception as e:
            log.warning(f"Console exporter 실패: {e}")

    # OTLP gRPC exporter (Collector/Tempo 전송)
    if _bool_env("OTEL_OTLP_EXPORTER", "0"):
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
            _tracer_provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
            )
            log.info(f"✅ OTel OTLP exporter 등록 → {endpoint}")
        except Exception as e:
            log.warning(f"OTLP exporter 실패 ({e}) — Console only")

    trace.set_tracer_provider(_tracer_provider)

    # FastAPI 자동 계측 (request span 생성)
    try:
        FastAPIInstrumentor.instrument_app(app)
        log.info("✅ FastAPIInstrumentor 등록")
    except Exception as e:
        log.warning(f"FastAPI instrument 실패: {e}")

    # 로그에 trace_id / span_id 주입
    try:
        LoggingInstrumentor().instrument(set_logging_format=True)
    except Exception as e:
        log.debug(f"LoggingInstrumentor 실패: {e}")

    _initialized = True
    log.info(f"🔭 OpenTelemetry 초기화 완료 (service={svc}, version={version})")
    return True


def get_tracer(name: str = "skyops"):
    """Get a named tracer. Always safe even if OTel 비활성화 (no-op tracer)."""
    from opentelemetry import trace
    return trace.get_tracer(name)
