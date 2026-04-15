"""Pydantic request/response models for SkyOps serving layer.

ADR-001 Migration Phase 1 — extracted from serving/api.py (2026-04-14 P3).
모든 forward reference는 파일 끝의 `model_rebuild()` 로 해소.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Delay Prediction (XGBoost + Conformal) ───────────────────────────
class DelayRequest(BaseModel):
    """지연 예측 요청 — NUMERIC + CATEGORICAL features (P1 Rotation 포함)."""
    # 필수 수치형
    dep_hour: float = Field(..., ge=0, le=23, description="출발 시(0-23)")
    dep_minute: float = Field(0, ge=0, le=59)
    dep_dayofweek: float = Field(..., ge=0, le=6, description="요일(0=월)")
    dep_month: float = Field(..., ge=1, le=12)
    dep_dayofyear: float = Field(1, ge=1, le=366)
    is_weekend: float = Field(0, ge=0, le=1)
    distance_miles: float = Field(..., gt=0)
    sched_elapsed_min: float = Field(..., gt=0)
    prev_dep_delay_min: float = Field(0.0)
    prev_arr_delay_min: float = Field(0.0)
    is_prev_delayed: float = Field(0, ge=0, le=1)
    origin_hourly_departures: float = Field(10.0, ge=0)
    dest_hourly_arrivals: float = Field(10.0, ge=0)
    dep_month_weather_score: float = Field(0.0)
    origin_weather_hist_delay: float = Field(0.0)
    dest_weather_hist_delay: float = Field(0.0)
    carrier_hist_delay: float = Field(0.0)
    origin_hist_delay: float = Field(0.0)
    dest_hist_delay: float = Field(0.0)
    route_hist_delay: float = Field(0.0)
    # Rotation features (P1 · 2026-04-14)
    rotation_depth: int = Field(0, ge=0, description="해당 일자 내 몇 번째 leg (0=첫째)")
    prev_leg_arr_delay_min: float = Field(0.0, description="같은 tail의 직전 leg 실도착 지연")
    scheduled_turnaround_min: float = Field(60.0, description="예정 turnaround (분)")
    actual_turnaround_min: float = Field(60.0, description="실제 turnaround (분)")
    is_first_leg_of_day: int = Field(1, ge=0, le=1, description="당일 첫 leg 여부")
    # 범주형
    carrier_code: str = Field("OO", description="항공사 코드")
    origin: str = Field("ATL", description="출발 공항 IATA")
    dest: str = Field("LAX", description="도착 공항 IATA")


class PredictionInterval(BaseModel):
    """Conformal Prediction interval (P1 · 2026-04-14)."""
    lower_min: float = Field(..., description="Lower bound of prediction (minutes)")
    upper_min: float = Field(..., description="Upper bound of prediction (minutes)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Coverage confidence (e.g. 0.9)")
    width_min: float = Field(..., description="upper - lower (minutes)")
    method: str = Field("split_conformal_mapie_v1.3", description="Calibration method")


class DelayResponse(BaseModel):
    predicted_delay_min: float
    is_delayed: bool  # ≥15분이면 지연
    confidence: str  # "high" / "medium" / "low" (기존 휴리스틱, backward compat)
    prediction_interval: Optional[PredictionInterval] = None  # P1 · Conformal
    latency_ms: float


# ── Anomaly Detection (Isolation Forest + Phase-aware) ───────────────
class AnomalyRequest(BaseModel):
    """이상 탐지 요청 — IF_FEATURES"""
    dep_hour: float = Field(..., ge=0, le=23)
    dep_dayofweek: float = Field(..., ge=0, le=6)
    distance_miles: float = Field(..., gt=0)
    sched_elapsed_min: float = Field(..., gt=0)
    prev_dep_delay_min: float = Field(0.0)
    prev_arr_delay_min: float = Field(0.0)
    is_prev_delayed: float = Field(0, ge=0, le=1)
    origin_hourly_departures: float = Field(10.0, ge=0)
    dest_hourly_arrivals: float = Field(10.0, ge=0)
    dep_month_weather_score: float = Field(0.0)
    origin_weather_hist_delay: float = Field(0.0)
    dest_weather_hist_delay: float = Field(0.0)
    carrier_hist_delay: float = Field(0.0)
    origin_hist_delay: float = Field(0.0)
    dest_hist_delay: float = Field(0.0)
    route_hist_delay: float = Field(0.0)
    # 선택 메타
    flight_id: Optional[str] = Field(None, description="항공편 식별자 (로그용 + Redis phase 조회)")


class AnomalyResponse(BaseModel):
    flight_id: Optional[str]
    anomaly_score: float  # IF decision_function 값 (음수일수록 이상)
    is_anomaly: bool
    risk_level: str  # "critical" / "warning" / "normal"
    latency_ms: float
    # P2 · 2026-04-14 · Phase-aware anomaly + alert discipline
    flight_phase: Optional[str] = None  # TAXI | TAKEOFF | CRUISE | ...
    phase_confidence: Optional[float] = None
    suppressed: bool = False  # debounce로 억제되었는가
    suppress_reason: Optional[str] = None


class AnomalyFeedbackRequest(BaseModel):
    """P2 · 2026-04-14 · Analyst feedback stub for active learning."""
    alert_id: str = Field(..., description="AnomalyEvent.alert_id (UUID)")
    label: str = Field(..., description="true_positive | false_positive | uncertain")
    note: Optional[str] = Field(None, description="자유 주석")
    labeled_by: Optional[str] = Field("anonymous", description="labeler ID")


class AnomalyFeedbackResponse(BaseModel):
    saved: bool
    alert_id: str
    file_path: str


# P8-F · Human-in-the-loop approval for suggested mitigations
class AnomalyApprovalRequest(BaseModel):
    """Analyst endorses or overrides an LLM advisory.

    Used when an LLM-proposed action (rerouting, hold-short, pax advisory)
    needs human sign-off before being surfaced to ATC or broadcast.
    """
    alert_id: str = Field(..., description="Target AlertDecisionEvent.alert_id")
    advisory_id: str = Field(..., description="LLM advisory correlation id")
    decision: str = Field(..., description="approved | rejected | modified | deferred")
    approver: str = Field(..., description="analyst user id (RBAC role required)")
    modified_text: Optional[str] = Field(None, description="if decision=modified, the final text")
    reason: Optional[str] = Field(None, description="approver's rationale")


class AnomalyApprovalResponse(BaseModel):
    recorded: bool
    alert_id: str
    advisory_id: str
    decision: str
    audit_trace_id: Optional[str] = None


class AnomalyExplainRequest(BaseModel):
    """이상 이벤트를 LLM으로 자연어 설명."""
    icao24: str
    callsign: Optional[str] = None
    anomaly_type: str
    severity: str
    details: dict = Field(default_factory=dict)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_m: Optional[float] = None
    velocity_m_s: Optional[float] = None


# ── Chat / RAG ────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="관제사 질문")
    use_rag: bool = Field(True, description="RAG 컨텍스트 사용 여부")
    max_tokens: int = Field(512, ge=64, le=2048)


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    latency_ms: float
    rag_used: bool


# ── Notification ──────────────────────────────────────────────────────
class AnnouncementRequest(BaseModel):
    flight_number: str
    delay_type: str = Field(..., description="weather | mechanical | atc | crew | other")
    delay_minutes: int = Field(..., ge=0)
    details: Optional[str] = None


# ── Active Learning Uncertainty Sampling (P4+ · 2026-04-15) ───────────
class ActiveLearningItem(BaseModel):
    """단일 anomaly 이벤트의 라벨링 우선순위 항목."""
    alert_id: str
    anomaly_score: float
    anomaly_type: str
    severity: str
    flight_phase: Optional[str] = None
    icao24: Optional[str] = None
    callsign: Optional[str] = None
    description: str
    uncertainty_score: float = Field(..., ge=0.0, le=1.0,
                                      description="0~1 (1=가장 불확실, threshold 근접)")


class ActiveLearningQuery(BaseModel):
    """`/active-learning/next` 응답."""
    items: list[ActiveLearningItem]
    total_pending: int = Field(..., description="Redis stream 내 unlabeled 총 건수")
    returned_count: int
    query_strategy: str = "uncertainty_sampling_v1"
    generated_at: str  # ISO 8601 UTC


# forward reference 해소 — `from __future__ import annotations` 대응
DelayRequest.model_rebuild()
DelayResponse.model_rebuild()
AnomalyRequest.model_rebuild()
AnomalyResponse.model_rebuild()
AnomalyFeedbackRequest.model_rebuild()
AnomalyFeedbackResponse.model_rebuild()
AnomalyExplainRequest.model_rebuild()
ChatRequest.model_rebuild()
ChatResponse.model_rebuild()
AnnouncementRequest.model_rebuild()
ActiveLearningItem.model_rebuild()
ActiveLearningQuery.model_rebuild()
