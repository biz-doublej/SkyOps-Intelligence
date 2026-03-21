"""
SkyOps Intelligence — CEP (Complex Event Processing) 룰 정의
==============================================================
3주차 과제: 고도 급변 / 속도 이상 / 경로 이탈 룰

각 룰은 AircraftState 딕셔너리를 받아 AnomalyEvent 딕셔너리(또는 None)를 반환합니다.
flink_processor.py 의 ProcessFunction에서 호출됩니다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Optional

# ── 상수 정의 ──────────────────────────────────────────────────────────
# 고도 급변 임계값: ±500 ft / 30초  →  m/s 단위로 변환 (1 ft = 0.3048 m)
ALTITUDE_SPIKE_THRESHOLD_M_S = (500 * 0.3048) / 30   # ≈ 5.08 m/s

# 속도 이상 임계값: ±100 knot / 1분  →  m/s 단위로 변환 (1 knot = 0.514444 m/s)
VELOCITY_SPIKE_THRESHOLD_M_S_PER_MIN = 100 * 0.514444   # ≈ 51.44 m/s/min

# 경로 이탈 임계값: 예상 경로에서 10km 이상 벗어남
PATH_DEVIATION_THRESHOLD_KM = 10.0

# Redis 이상 이벤트 TTL (초)
ANOMALY_EVENT_TTL_SEC = 3600  # 1시간 보존


# ── 데이터 클래스 ──────────────────────────────────────────────────────
@dataclass
class AnomalyEvent:
    """이상 탐지 이벤트 — Redis / Kafka anomaly-event 토픽으로 전송됩니다."""
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


# ── CEP 룰 1: 고도 급변 ────────────────────────────────────────────────
def check_altitude_spike(
    current: dict,
    previous: Optional[dict],
    window_sec: float = 30.0,
) -> Optional[AnomalyEvent]:
    """
    고도 급변 감지 (±500 ft / 30초 초과).

    Args:
        current:  현재 flight-position 레코드
        previous: 이전 레코드 (동일 icao24)
        window_sec: 비교 시간 창 (기본 30초)

    Returns:
        AnomalyEvent if anomaly detected, else None
    """
    if previous is None:
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

    # 30초 기준으로 정규화
    normalized_rate = rate_m_s * (window_sec / dt) if dt != window_sec else rate_m_s

    if rate_m_s < ALTITUDE_SPIKE_THRESHOLD_M_S:
        return None

    ratio = rate_m_s / ALTITUDE_SPIKE_THRESHOLD_M_S
    direction = "▲상승" if float(cur_alt) > float(prev_alt) else "▼하강"

    return AnomalyEvent(
        icao24=current.get("icao24", ""),
        callsign=(current.get("callsign") or "N/A").strip(),
        anomaly_type="ALTITUDE_SPIKE",
        severity=_classify_severity(ratio),
        description=(
            f"고도 급변 감지 {direction}: "
            f"{alt_change_m:.0f}m 변화 / {dt:.0f}초 "
            f"(기준: {500 * 0.3048:.0f}m/30초)"
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
            "threshold_m_s": round(ALTITUDE_SPIKE_THRESHOLD_M_S, 3),
            "elapsed_sec": round(dt, 1),
        },
    )


# ── CEP 룰 2: 속도 이상 ────────────────────────────────────────────────
def check_velocity_spike(
    current: dict,
    previous: Optional[dict],
    window_sec: float = 60.0,
) -> Optional[AnomalyEvent]:
    """
    속도 이상 감지 (±100 knot / 1분 초과).

    Args:
        current:  현재 flight-position 레코드
        previous: 이전 레코드 (동일 icao24)
        window_sec: 비교 시간 창 (기본 60초)

    Returns:
        AnomalyEvent if anomaly detected, else None
    """
    if previous is None:
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

    if rate_per_min < VELOCITY_SPIKE_THRESHOLD_M_S_PER_MIN:
        return None

    ratio = rate_per_min / VELOCITY_SPIKE_THRESHOLD_M_S_PER_MIN
    # m/s → knot 환산 (표시용)
    vel_change_knots = vel_change_m_s / 0.514444
    cur_vel_knots = float(cur_vel) / 0.514444

    return AnomalyEvent(
        icao24=current.get("icao24", ""),
        callsign=(current.get("callsign") or "N/A").strip(),
        anomaly_type="VELOCITY_SPIKE",
        severity=_classify_severity(ratio),
        description=(
            f"속도 이상 감지: {vel_change_knots:.1f}kt 변화 / {dt:.0f}초 "
            f"(분당 {rate_per_min / 0.514444:.1f}kt, 기준: 100kt/min)"
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
            "threshold_per_min_m_s": round(VELOCITY_SPIKE_THRESHOLD_M_S_PER_MIN, 3),
            "elapsed_sec": round(dt, 1),
        },
    )


# ── CEP 룰 3: 경로 이탈 ────────────────────────────────────────────────
def check_path_deviation(
    current: dict,
    history: list[dict],
    lookahead_points: int = 3,
) -> Optional[AnomalyEvent]:
    """
    경로 이탈 감지 (예상 선형 경로에서 10km 이상 벗어남).

    최근 N개의 위치 기록으로 선형 보간 경로를 추정하고,
    현재 위치와의 수직 거리(cross-track distance)가 임계값을 넘으면 이상으로 판단합니다.

    Args:
        current:         현재 레코드
        history:         최근 레코드 리스트 (오래된 것부터, 최소 2개 필요)
        lookahead_points: 경로 추정에 사용할 이전 포인트 수

    Returns:
        AnomalyEvent if anomaly detected, else None
    """
    if len(history) < 2:
        return None

    cur_lat = current.get("latitude")
    cur_lon = current.get("longitude")
    cur_ts = current.get("time_position") or current.get("last_contact")

    if None in (cur_lat, cur_lon):
        return None

    # 유효 포인트만 추출
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

    # 선분 p1→p2 에 대한 점 p3의 수직 거리 계산
    deviation_km = _cross_track_distance_km(lat1, lon1, lat2, lon2, lat3, lon3)

    if deviation_km < PATH_DEVIATION_THRESHOLD_KM:
        return None

    ratio = deviation_km / PATH_DEVIATION_THRESHOLD_KM

    return AnomalyEvent(
        icao24=current.get("icao24", ""),
        callsign=(current.get("callsign") or "N/A").strip(),
        anomaly_type="PATH_DEVIATION",
        severity=_classify_severity(ratio),
        description=(
            f"경로 이탈 감지: 예상 경로에서 {deviation_km:.1f}km 벗어남 "
            f"(기준: {PATH_DEVIATION_THRESHOLD_KM}km)"
        ),
        latitude=cur_lat,
        longitude=cur_lon,
        altitude_m=current.get("baro_altitude"),
        velocity_m_s=current.get("velocity"),
        detected_at=int(float(cur_ts) * 1000) if cur_ts else 0,
        details={
            "deviation_km": round(deviation_km, 3),
            "threshold_km": PATH_DEVIATION_THRESHOLD_KM,
            "ref_point_1": {"lat": lat1, "lon": lon1},
            "ref_point_2": {"lat": lat2, "lon": lon2},
            "cur_point": {"lat": lat3, "lon": lon3},
        },
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
) -> list[AnomalyEvent]:
    """
    모든 CEP 룰을 평가하고 탐지된 이상 이벤트 목록을 반환합니다.

    Args:
        current:  현재 flight-position 레코드
        previous: 직전 레코드 (동일 icao24)
        history:  최근 N개 레코드 리스트

    Returns:
        감지된 AnomalyEvent 목록 (없으면 빈 리스트)
    """
    events: list[AnomalyEvent] = []

    alt_event = check_altitude_spike(current, previous)
    if alt_event:
        events.append(alt_event)

    vel_event = check_velocity_spike(current, previous)
    if vel_event:
        events.append(vel_event)

    path_event = check_path_deviation(current, history)
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

    print("\n[TEST 4] 통합 평가 (모든 룰):")
    all_events = evaluate_all_rules(cur_vel, prev_vel, history)
    print(f"  탐지된 이상 이벤트: {len(all_events)}건")
    for e in all_events:
        print(f"    - {e.anomaly_type} [{e.severity}]: {e.description}")
