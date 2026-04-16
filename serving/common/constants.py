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
CONFORMAL_PATH = MODELS_DIR / "conformal_calibrator.pkl"  # P1 (2026-04-14)

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

# IF 이상 판정 임계값 (6주차 기준)
IF_SCORE_THRESHOLD = -0.1  # score < threshold → 이상

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
API_VERSION = "2.1.7"  # 2026-04-17 — RAG_RETRIEVE_DISABLED + canned topics for NAS demo
