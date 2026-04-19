"""Shared constants for SkyOps serving layer.

ADR-001 Migration Phase 1 — extracted from serving/api.py (2026-04-14 P3).
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────
# P4+ Packaging 이후 `serving` 이 site-packages 로 install 되는 경우
# `Path(__file__).parent.parent.parent` 가 site-packages 루트를 가리켜
# `/usr/local/lib/python3.11/site-packages/data/models/...` 같은
# 엉뚱한 곳을 찾게 된다 (2026-04-17 v2.1.4 수정).
#
# 컨테이너/운영 환경에서는 SKYOPS_DATA_DIR 환경변수로 데이터 루트를
# 명시 주입하고, 로컬 개발에서는 기존 리포 상대경로를 유지한다.
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR = Path(os.getenv("SKYOPS_DATA_DIR") or _DEFAULT_DATA_DIR).resolve()
PROJECT_ROOT = DATA_DIR.parent  # 하위 호환
MODELS_DIR = DATA_DIR / "models"
XGB_MODEL_PATH = MODELS_DIR / "xgboost_best.pkl"
IF_MODEL_PATH = MODELS_DIR / "isolation_forest.pkl"
CONFORMAL_PATH = MODELS_DIR / "conformal_calibrator.pkl"  # P1 (2026-04-14) — symmetric split conformal
CONFORMAL_PATH_CQR = MODELS_DIR / "conformal_calibrator_cqr.pkl"  # v2.1.9 ADR-005 — Conformalized Quantile Regression (asymmetric)

FEEDBACK_DIR = DATA_DIR / "analyst_feedback"  # P2 (2026-04-14)
FEEDBACK_FILE = FEEDBACK_DIR / "feedback.jsonl"

# ── Feature 정의 ──────────────────────────────────────────────────────
# analysis/xgboost_model.py 와 동기 유지 (P1 Rotation features 포함)
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

# ── Stage 2 / ADR-005 ── Network-aware features (v2.1.9)
# 아직 production 모델 (xgboost_best.pkl) 에 포함되지 않음. 다음 retrain cycle
# 에서 NUMERIC_FEATURES 에 추가 예정. 지금은 training script + feature store 에서만 사용.
GRAPH_FEATURES_AIRPORT = [
    "origin_degree_total", "origin_pagerank", "origin_airport_hub_score",
    "dest_degree_total", "dest_pagerank", "dest_airport_hub_score",
]
GRAPH_FEATURES_ROUTE = [
    "route_volume", "route_rank", "route_degree_product", "route_hub_to_hub",
]
UPSTREAM_DELAY_FEATURES = [
    "origin_recent_delay_avg_60m", "origin_recent_delay_p95_60m",
    "origin_recent_volume_60m",
    "dest_recent_delay_avg_60m", "dest_recent_volume_60m",
    "origin_hub_congestion_ratio",
]
# 다음 retrain 에 포함될 후보 set — training_pipeline 에서 ALL_FEATURES + NETWORK_FEATURES.
NETWORK_FEATURES = GRAPH_FEATURES_AIRPORT + GRAPH_FEATURES_ROUTE + UPSTREAM_DELAY_FEATURES

# IF 이상 판정 임계값 (6주차 기준)
IF_SCORE_THRESHOLD = -0.1  # score < threshold → 이상

# ── Stage 3 / ADR-006 · Alert Discipline (v2.1.10) ─────────────────
# Hysteresis — 진입 / 탈출 임계값 분리로 플래핑 방지.
# score < ENTER 면 alerting 진입, score > EXIT 이면 clear 로 탈출.
# 두 값 사이 (band) 에 있으면 기존 state 유지.
IF_SCORE_ENTER = float(os.getenv("IF_SCORE_ENTER", "-0.15"))  # 더 엄격
IF_SCORE_EXIT = float(os.getenv("IF_SCORE_EXIT", "-0.05"))    # 더 관대
# Hysteresis state TTL (초) — 비활성 flight 는 자동 만료.
IF_HYSTERESIS_TTL_SEC = int(os.getenv("IF_HYSTERESIS_TTL_SEC", "900"))

# Per-phase Isolation Forest — 학습 시 7개 모델이 별도 파일로 저장됨.
# serving 은 AnomalyRequest.phase (or Redis 조회) 에 따라 해당 모델을 로드.
IF_PHASES = ["TAXI", "TAKEOFF", "CLIMB", "CRUISE", "DESCENT", "APPROACH", "LANDING"]

def if_model_path_for_phase(phase: str):
    """Phase 이름 → 해당 모델 파일 경로. 없으면 base IF 로 fallback."""
    phase = (phase or "").upper()
    if phase in IF_PHASES:
        return MODELS_DIR / f"isolation_forest_{phase}.pkl"
    return IF_MODEL_PATH

# Alert suppression config 파일 — v2.1.10 ADR-006 D3.
SUPPRESSION_CONFIG = PROJECT_ROOT / "config" / "alert_suppression.yaml"

# Redis key patterns — hysteresis + suppression audit log
REDIS_ANOMALY_HYSTERESIS = "skyops:anomaly:hysteresis:{}"   # .format(flight_id)
REDIS_ANOMALY_SUPPRESS_AUDIT = "skyops:anomaly:suppress:audit"  # Redis Stream

# ── vLLM 설정 ─────────────────────────────────────────────────────────
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "aviation-llm")

# ── Redis 키 네임스페이스 (P2 phase-aware + debounce) ─────────────────
REDIS_AIRCRAFT_LATEST = "skyops:aircraft:latest"
REDIS_AIRCRAFT_STATE = "skyops:aircraft:state:{}"
REDIS_AIRCRAFT_PHASE = "skyops:aircraft:phase:{}"          # P2 (2026-04-14)
REDIS_ANOMALY_STREAM = "skyops:anomaly:stream"
REDIS_ANOMALY_DEBOUNCE = "skyops:anomaly:debounce:{}:{}"   # P2 (2026-04-14)
REDIS_NOTAM_STREAM = "skyops:notam:stream"                 # P6-G (2026-04-15)

# Version
API_VERSION = "2.2.0"  # 2026-04-19 — ADR-007 Stage 4 Production Readiness (RAGAs CI + router split + full-stack OTel + RBAC/SLO burn-rate/Shadow)
