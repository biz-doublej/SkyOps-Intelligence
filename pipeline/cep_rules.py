"""
SkyOps Intelligence — CEP (Complex Event Processing) 룰 정의
==============================================================
3주차 과제: 고도 급변 / 속도 이상 / 경로 이탈 룰

각 룰은 AircraftState 딕셔너리를 받아 AnomalyEvent 딕셔너리(또는 None)를 반환합니다.
flink_processor.py 의 ProcessFunction에서 호출됩니다.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

# ── 상수 정의 (CRUISE 기본값) ─────────────────────────────────────────
# 고도 급변 임계값: ±500 ft / 30초  →  m/s 단위로 변환 (1 ft = 0.3048 m)
ALTITUDE_SPIKE_THRESHOLD_M_S = (500 * 0.3048) / 30   # ≈ 5.08 m/s

# 속도 이상 임계값: ±100 knot / 1분  →  m/s 단위로 변환 (1 knot = 0.514444 m/s)
VELOCITY_SPIKE_THRESHOLD_M_S_PER_MIN = 100 * 0.514444   # ≈ 51.44 m/s/min

# 경로 이탈 임계값: 예상 경로에서 10km 이상 벗어남
PATH_DEVIATION_THRESHOLD_KM = 10.0

# Redis 이상 이벤트 TTL (초)
ANOMALY_EVENT_TTL_SEC = 3600  # 1시간 보존


# ── Phase-aware threshold 조정 배율 (P2 · 2026-04-14) ───────────────
# 비행 단계별로 정상 변화 폭이 달라 CRUISE 기준 threshold를 phase에 따라 조정.
# Strategic Review 3번 병목 — rule engine + semi-supervised + analyst feedback.
# None = 해당 phase에서는 rule 자체를 비활성 (e.g., TAXI 중 ALTITUDE_SPIKE 불가)
PHASE_ALTITUDE_MULTIPLIER = {
    "TAXI":     None,    # 지상 → 고도 변화 없음
    "TAKEOFF":  3.0,     # ±1500 ft/30s 허용 (급상승 정상)
    "CLIMB":    2.0,
    "CRUISE":   1.0,     # 기본 ±500 ft/30s
    "DESCENT":  2.0,
    "APPROACH": 2.0,
    "LANDING":  3.0,
    "UNKNOWN":  1.0,     # 보수적으로 기본값
}

PHASE_VELOCITY_MULTIPLIER = {
    "TAXI":     0.1,     # ±10 kt/min (taxiing 시 작은 변화가 이상)
    "TAKEOFF":  1.5,     # ±150 kt/min (가속 정상)
    "CLIMB":    0.8,
    "CRUISE":   1.0,     # 기본 ±100 kt/min
    "DESCENT":  0.8,
    "APPROACH": 0.8,
    "LANDING":  1.5,     # 감속 정상
    "UNKNOWN":  1.0,
}

PHASE_PATH_MULTIPLIER = {
    "TAXI":     None,    # 지상 경로는 CEP 대상 아님
    "TAKEOFF":  0.5,     # ±5km (이륙 직후 경로 이탈 엄격)
    "CLIMB":    0.7,
    "CRUISE":   1.0,     # 기본 10km
    "DESCENT":  0.7,
    "APPROACH": 0.5,     # 진입 경로 엄격
    "LANDING":  None,    # 착륙 자체는 runway 내 → rule 비활성
    "UNKNOWN":  1.0,
}


# ── 데이터 클래스 ──────────────────────────────────────────────────────
@dataclass
class AnomalyEvent:
    """이상 탐지 이벤트 — Redis / Kafka anomaly-event 토픽으로 전송됩니다.

    [2026-04-14 P2] Canonical Event Model (AlertDecisionEvent)에 맞춰
    flight_phase, alert_id, correlation_id 필드 추가. Phase-aware detection
    을 위해 필수.
    """
    icao24: str
    callsign: str
    anomaly_type: str               # "ALTITUDE_SPIKE" | "VELOCITY_SPIKE" | "PATH_DEVIATION"
    severity: str                   # "LOW" | "MEDIUM" | "HIGH"
    description: str
    latitude: Optional[float]
    longitude: Optional[float]
    altitude_m: Optional[float]
    velocity_m_s: Optional[float]
    detected_at: int                # Unix timestamp (ms)
    details: dict = field(default_factory=dict)

    # P2 (2026-04-14) · Phase-aware anomaly + alert lifecycle
    flight_phase: str = "UNKNOWN"           # FlightPhase enum value
    phase_confidence: float = 0.0           # 0.0 ~ 1.0
    alert_id: str = ""                      # UUID4; 생성 시 자동 할당
    correlation_id: str = ""                # e.g. f"{icao24}:{detected_at}"

    def __post_init__(self):
        if not self.alert_id:
            self.alert_id = str(uuid.uuid4())
        if not self.correlation_id:
            self.correlation_id = f"{self.icao24}:{self.detected_at}"

    def to_dict(self) -> dict:
        return asdict(self)


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간 대원 거리(km)를 계산합니다 (Haversine 공식)."""
    R = 6371.0  # 지구 반지름 km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _classify_severity(ratio: float) -> str:
    """임계값 대비 비율로 심각도를 분류합니다."""
    if ratio >= 3.0:
        return "HIGH"
    elif ratio >= 2.0:
        return "MEDIUM"
    return "LOW"


# ── CEP 룰 1: 고도 급변 (Phase-aware) ─────────────────────────────────
def check_altitude_spike(
    current: dict,
    previous: Optional[dict],
    window_sec: float = 30.0,
    flight_phase: str = "UNKNOWN",
    phase_confidence: float = 0.0,
) -> Optional[AnomalyEvent]:
    """
    고도 급변 감지 (phase-aware, CRUISE 기본 ±500 ft / 30초 초과).

    [2026-04-14 P2] flight_phase 에 따라 threshold 조정. TAXI 중에는
    rule 자체 비활성 (불가능한 조합).

    Args:
        current:  현재 flight-position 레코드
        previous: 이전 레코드 (동일 icao24)
        window_sec: 비교 시간 창 (기본 30초)
        flight_phase: FlightPhase enum value (TAXI/TAKEOFF/.../UNKNOWN)
        phase_confidence: classifier 신뢰도

    Returns:
        AnomalyEvent if anomaly detected, else None
    """
    if previous is None:
        return None

    # Phase 비활성화 (TAXI 등)
    mult = PHASE_ALTITUDE_MULTIPLIER.get(flight_phase, 1.0)
    if mult is None:
        return None

    cur_alt = current.get("baro_altitude")
    prev_alt = previous.get("baro_altitude")
    cur_ts = current.get("time_position") or current.get("last_contact")
    prev_ts = previous.get("time_position") or previous.get("last_contact")

    if None in (cur_alt, prev_alt, cur_ts, prev_ts):
        return None

    dt = float(cur_ts) - float(prev_ts)
    if dt <= 0 or dt > 300:  # 300초 이상 갭은 무시
        return None

    alt_change_m = abs(float(cur_alt) - float(prev_alt))
    rate_m_s = alt_change_m / dt

    # Phase-aware threshold
    effective_threshold = ALTITUDE_SPIKE_THRESHOLD_M_S * mult

    if rate_m_s < effective_threshold:
        return None

    ratio = rate_m_s / effective_threshold
    direction = "▲상승" if float(cur_alt) > float(prev_alt) else "▼하강"

    return AnomalyEvent(
        icao24=current.get("icao24", ""),
        callsign=(current.get("callsign") or "N/A").strip(),
        anomaly_type="ALTITUDE_SPIKE",
        severity=_classify_severity(ratio),
        description=(
            f"고도 급변 감지 {direction} [{flight_phase}]: "
            f"{alt_change_m:.0f}m 변화 / {dt:.0f}초 "
            f"(기준: {effective_threshold*30:.0f}m/30초, phase mult={mult})"
        ),
        latitude=current.get("latitude"),
        longitude=current.get("longitude"),
        altitude_m=float(cur_alt),
        velocity_m_s=current.get("velocity"),
        detected_at=int(float(cur_ts) * 1000),
        details={
            "prev_altitude_m": float(prev_alt),
            "cur_altitude_m": float(cur_alt),
            "delta_m": round(alt_change_m, 2),
            "rate_m_s": round(rate_m_s, 3),
            "threshold_m_s": round(effective_threshold, 3),
            "phase_multiplier": mult,
            "elapsed_sec": round(dt, 1),
        },
        flight_phase=flight_phase,
        phase_confidence=phase_confidence,
    )


# ── CEP 룰 2: 속도 이상 ────────────────────────────────────────────────
def check_velocity_spike(
    current: dict,
    previous: Optional[dict],
    window_sec: float = 60.0,
    flight_phase: str = "UNKNOWN",
    phase_confidence: float = 0.0,
) -> Optional[AnomalyEvent]:
    """
    속도 이상 감지 (phase-aware, CRUISE 기본 ±100 knot / 1분 초과).

    [2026-04-14 P2] flight_phase 에 따라 threshold 조정.

    Args:
        current:  현재 flight-position 레코드
        previous: 이전 레코드 (동일 icao24)
        window_sec: 비교 시간 창 (기본 60초)
        flight_phase: FlightPhase enum value
        phase_confidence: classifier 신뢰도

    Returns:
        AnomalyEvent if anomaly detected, else None
    """
    if previous is None:
        return None

    mult = PHASE_VELOCITY_MULTIPLIER.get(flight_phase, 1.0)
    if mult is None:
        return None

    cur_vel = current.get("velocity")
    prev_vel = previous.get("velocity")
    cur_ts = current.get("time_position") or current.get("last_contact")
    prev_ts = previous.get("time_position") or previous.get("last_contact")

    if None in (cur_vel, prev_vel, cur_ts, prev_ts):
        return None

    dt = float(cur_ts) - float(prev_ts)
    if dt <= 0 or dt > 600:
        return None

    vel_change_m_s = abs(float(cur_vel) - float(prev_vel))
    # 분당 변화율로 정규화
    rate_per_min = vel_change_m_s * (60.0 / dt)

    effective_threshold = VELOCITY_SPIKE_THRESHOLD_M_S_PER_MIN * mult

    if rate_per_min < effective_threshold:
        return None

    ratio = rate_per_min / effective_threshold
    vel_change_knots = vel_change_m_s / 0.514444

    return AnomalyEvent(
        icao24=current.get("icao24", ""),
        callsign=(current.get("callsign") or "N/A").strip(),
        anomaly_type="VELOCITY_SPIKE",
        severity=_classify_severity(ratio),
        description=(
            f"속도 이상 감지 [{flight_phase}]: {vel_change_knots:.1f}kt 변화 / {dt:.0f}초 "
            f"(분당 {rate_per_min / 0.514444:.1f}kt, 기준: {100*mult:.0f}kt/min)"
        ),
        latitude=current.get("latitude"),
        longitude=current.get("longitude"),
        altitude_m=current.get("baro_altitude"),
        velocity_m_s=float(cur_vel),
        detected_at=int(float(cur_ts) * 1000),
        details={
            "prev_velocity_m_s": round(float(prev_vel), 2),
            "cur_velocity_m_s": round(float(cur_vel), 2),
            "delta_m_s": round(vel_change_m_s, 3),
            "rate_per_min_m_s": round(rate_per_min, 3),
            "threshold_per_min_m_s": round(effective_threshold, 3),
            "phase_multiplier": mult,
            "elapsed_sec": round(dt, 1),
        },
        flight_phase=flight_phase,
        phase_confidence=phase_confidence,
    )


# ── CEP 룰 3: 경로 이탈 (Phase-aware) ──────────────────────────────────
def check_path_deviation(
    current: dict,
    history: list[dict],
    lookahead_points: int = 3,
    flight_phase: str = "UNKNOWN",
    phase_confidence: float = 0.0,
) -> Optional[AnomalyEvent]:
    """
    경로 이탈 감지 (phase-aware, CRUISE 기본 10km 초과).

    [2026-04-14 P2] flight_phase 에 따라 threshold 조정. TAXI/LANDING은
    rule 비활성 (runway 내 이동).
    """
    if len(history) < 2:
        return None

    mult = PHASE_PATH_MULTIPLIER.get(flight_phase, 1.0)
    if mult is None:
        return None

    cur_lat = current.get("latitude")
    cur_lon = current.get("longitude")
    cur_ts = current.get("time_position") or current.get("last_contact")

    if None in (cur_lat, cur_lon):
        return None

    valid = [
        p for p in history[-lookahead_points:]
        if p.get("latitude") is not None and p.get("longitude") is not None
    ]
    if len(valid) < 2:
        return None

    p1 = valid[0]
    p2 = valid[-1]

    lat1, lon1 = float(p1["latitude"]), float(p1["longitude"])
    lat2, lon2 = float(p2["latitude"]), float(p2["longitude"])
    lat3, lon3 = float(cur_lat), float(cur_lon)

    deviation_km = _cross_track_distance_km(lat1, lon1, lat2, lon2, lat3, lon3)
    effective_threshold = PATH_DEVIATION_THRESHOLD_KM * mult

    if deviation_km < effective_threshold:
        return None

    ratio = deviation_km / effective_threshold

    return AnomalyEvent(
        icao24=current.get("icao24", ""),
        callsign=(current.get("callsign") or "N/A").strip(),
        anomaly_type="PATH_DEVIATION",
        severity=_classify_severity(ratio),
        description=(
            f"경로 이탈 감지 [{flight_phase}]: 예상 경로에서 {deviation_km:.1f}km 벗어남 "
            f"(기준: {effective_threshold:.1f}km, phase mult={mult})"
        ),
        latitude=cur_lat,
        longitude=cur_lon,
        altitude_m=current.get("baro_altitude"),
        velocity_m_s=current.get("velocity"),
        detected_at=int(float(cur_ts) * 1000) if cur_ts else 0,
        details={
            "deviation_km": round(deviation_km, 3),
            "threshold_km": round(effective_threshold, 3),
            "phase_multiplier": mult,
            "ref_point_1": {"lat": lat1, "lon": lon1},
            "ref_point_2": {"lat": lat2, "lon": lon2},
            "cur_point": {"lat": lat3, "lon": lon3},
        },
        flight_phase=flight_phase,
        phase_confidence=phase_confidence,
    )


def _cross_track_distance_km(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    lat3: float, lon3: float,
) -> float:
    """
    점 P3가 선분 P1→P2 로부터 떨어진 수직 거리(km)를 계산합니다.
    (Cross-track distance, 구면 기하학 기반)
    """
    R = 6371.0
    d13 = haversine_km(lat1, lon1, lat3, lon3) / R  # 라디안
    theta13 = math.radians(_bearing(lat1, lon1, lat3, lon3))
    theta12 = math.radians(_bearing(lat1, lon1, lat2, lon2))
    dxt = math.asin(math.sin(d13) * math.sin(theta13 - theta12))
    return abs(dxt) * R


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간 방위각(도)을 계산합니다."""
    d_lon = math.radians(lon2 - lon1)
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    x = math.sin(d_lon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(d_lon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


# ── 통합 CEP 평가기 ────────────────────────────────────────────────────
def evaluate_all_rules(
    current: dict,
    previous: Optional[dict],
    history: list[dict],
    flight_phase: str = "UNKNOWN",
    phase_confidence: float = 0.0,
) -> list[AnomalyEvent]:
    """
    모든 CEP 룰을 평가하고 탐지된 이상 이벤트 목록을 반환합니다.

    [2026-04-14 P2] flight_phase 를 전달받아 phase-aware threshold 적용.
    호출자(flink_processor)가 phase_classifier로 먼저 분류한 뒤 전달.

    Args:
        current:  현재 flight-position 레코드
        previous: 직전 레코드 (동일 icao24)
        history:  최근 N개 레코드 리스트
        flight_phase: FlightPhase enum value (TAXI / TAKEOFF / ... / UNKNOWN)
        phase_confidence: classifier 신뢰도 (0.0 ~ 1.0)

    Returns:
        감지된 AnomalyEvent 목록 (없으면 빈 리스트)
    """
    events: list[AnomalyEvent] = []

    alt_event = check_altitude_spike(current, previous,
                                     flight_phase=flight_phase,
                                     phase_confidence=phase_confidence)
    if alt_event:
        events.append(alt_event)

    vel_event = check_velocity_spike(current, previous,
                                     flight_phase=flight_phase,
                                     phase_confidence=phase_confidence)
    if vel_event:
        events.append(vel_event)

    path_event = check_path_deviation(current, history,
                                      flight_phase=flight_phase,
                                      phase_confidence=phase_confidence)
    if path_event:
        events.append(path_event)

    return events


# ── 테스트 실행 ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import time
    import json

    now = int(time.time())
    print("=== CEP 룰 단위 테스트 ===\n")

    # 테스트 데이터: 고도 급변 시나리오
    prev_record = {
        "icao24": "71bf5c", "callsign": "KAL001",
        "latitude": 37.46, "longitude": 126.44,
        "baro_altitude": 3000.0, "velocity": 250.0,
        "time_position": now - 25, "last_contact": now - 25,
    }
    cur_record = {
        "icao24": "71bf5c", "callsign": "KAL001",
        "latitude": 37.47, "longitude": 126.45,
        "baro_altitude": 2500.0, "velocity": 248.0,  # 500m 하강 / 25초
        "time_position": now, "last_contact": now,
    }

    print("[TEST 1] 고도 급변 룰:")
    evt = check_altitude_spike(cur_record, prev_record)
    if evt:
        print(f"  ✅ 이상 탐지: {evt.anomaly_type} | 심각도: {evt.severity}")
        print(f"  📝 {evt.description}")
    else:
        print("  ⬜ 이상 없음")

    # 테스트 데이터: 속도 이상 시나리오
    prev_vel = dict(prev_record, velocity=200.0, time_position=now - 30)
    cur_vel = dict(cur_record, velocity=320.0, time_position=now)  # 120m/s 변화 / 30초 → 240m/s/min >> 51.44

    print("\n[TEST 2] 속도 이상 룰:")
    evt2 = check_velocity_spike(cur_vel, prev_vel)
    if evt2:
        print(f"  ✅ 이상 탐지: {evt2.anomaly_type} | 심각도: {evt2.severity}")
        print(f"  📝 {evt2.description}")
    else:
        print("  ⬜ 이상 없음")

    # 테스트 데이터: 경로 이탈 시나리오 (인천공항 부근 급선회)
    history = [
        {"icao24": "71bf5c", "latitude": 37.40, "longitude": 126.20,
         "time_position": now - 120, "last_contact": now - 120,
         "baro_altitude": 5000, "velocity": 250},
        {"icao24": "71bf5c", "latitude": 37.42, "longitude": 126.30,
         "time_position": now - 90, "last_contact": now - 90,
         "baro_altitude": 5000, "velocity": 250},
        {"icao24": "71bf5c", "latitude": 37.44, "longitude": 126.40,
         "time_position": now - 60, "last_contact": now - 60,
         "baro_altitude": 5000, "velocity": 250},
    ]
    cur_deviated = dict(cur_record, latitude=37.20, longitude=126.50)  # 대폭 남쪽으로 이탈

    print("\n[TEST 3] 경로 이탈 룰:")
    evt3 = check_path_deviation(cur_deviated, history)
    if evt3:
        print(f"  ✅ 이상 탐지: {evt3.anomaly_type} | 심각도: {evt3.severity}")
        print(f"  📝 {evt3.description}")
    else:
        print("  ⬜ 이상 없음")

    print("\n[TEST 4] 통합 평가 (모든 룰, phase=CRUISE):")
    all_events = evaluate_all_rules(cur_vel, prev_vel, history, flight_phase="CRUISE", phase_confidence=0.9)
    print(f"  탐지된 이상 이벤트: {len(all_events)}건")
    for e in all_events:
        print(f"    - {e.anomaly_type} [{e.severity}] phase={e.flight_phase}: {e.description}")

    # [TEST 5] Phase-aware suppression: CRUISE에서는 탐지되는 altitude_spike가 TAKEOFF에서는 통과
    print("\n[TEST 5] Phase-aware threshold (동일 이벤트, phase 차이):")
    evt_cruise = check_altitude_spike(cur_record, prev_record, flight_phase="CRUISE")
    evt_takeoff = check_altitude_spike(cur_record, prev_record, flight_phase="TAKEOFF")
    evt_taxi = check_altitude_spike(cur_record, prev_record, flight_phase="TAXI")
    print(f"  CRUISE  → {'탐지' if evt_cruise else '정상'}")
    print(f"  TAKEOFF → {'탐지' if evt_takeoff else '정상'}  (mult=3.0, 관대)")
    print(f"  TAXI    → {'탐지' if evt_taxi else '정상'}  (rule 비활성)")
    assert evt_cruise is not None, "CRUISE는 탐지되어야 함"
    assert evt_taxi is None, "TAXI에서는 rule 비활성 (None 반환)"
    print("  ✅ phase-aware threshold 정상 동작")

    # [TEST 6] AnomalyEvent.alert_id / correlation_id 자동 생성
    print("\n[TEST 6] AnomalyEvent metadata:")
    if evt_cruise:
        print(f"  alert_id:       {evt_cruise.alert_id}")
        print(f"  correlation_id: {evt_cruise.correlation_id}")
        print(f"  flight_phase:   {evt_cruise.flight_phase}")
        assert len(evt_cruise.alert_id) == 36, "UUID4 형식이어야 함"
        assert evt_cruise.correlation_id.startswith(evt_cruise.icao24), "correlation_id 포맷"
        print("  ✅ alert_id/correlation_id 자동 할당 확인")
