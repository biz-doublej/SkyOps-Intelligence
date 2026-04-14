"""
SkyOps Intelligence — Flight Phase Classifier (P2 · 2026-04-14)
================================================================
Strategic Review 3번 병목 — phase-aware anomaly detection의 선행 작업.

ADS-B record(icao24, on_ground, baro_altitude, velocity, vertical_rate)
를 입력으로 받아 비행 단계를 heuristic하게 분류한다. Production 수준의
ML classifier가 아닌 rule-based PoC다. Edge case(go-around, holding 등)는
UNKNOWN으로 fallback하고 후속 과제(P3+)에서 ML 모델로 전환 예정.

사용 예:
    from pipeline.phase_classifier import classify_phase, FlightPhase
    phase, confidence = classify_phase(record)
    # phase: FlightPhase, confidence: 0.0~1.0
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class FlightPhase(str, Enum):
    """7 canonical flight phases + UNKNOWN."""
    TAXI = "TAXI"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    DESCENT = "DESCENT"
    APPROACH = "APPROACH"
    LANDING = "LANDING"
    UNKNOWN = "UNKNOWN"


# ── 임계값 (ICAO/도메인 heuristic 기반) ───────────────────────────────
# 미터 단위 baro_altitude (OpenSky native). 1 ft = 0.3048 m.
_FT = 0.3048
_CRUISE_ALT_M = 3000           # ~10,000 ft (cruise 시작)
_APPROACH_ALT_M = 600          # ~2,000 ft (approach 진입)
_LANDING_ALT_M = 150           # ~500 ft (최종 landing)
_CRUISE_VR_M_S = 1.0           # cruise 수직속도 임계 (|vr| < 1 m/s)
_CLIMB_VR_M_S = 2.0            # climb 최소 상승율
_DESCENT_VR_M_S = -1.0         # descent 최대 상승율 (이하이면 하강)
_APPROACH_VR_M_S = -0.5        # approach 최소 하강율
_TAKEOFF_VR_M_S = 5.0          # takeoff 급상승 감지
_TAXI_VEL_M_S = 5.0            # 5 m/s = ~10 knots (taxi 상한)
_LANDING_VEL_M_S = 60.0        # 60 m/s = ~117 knots (landing threshold speed)


def classify_phase(
    record: dict,
    previous: Optional[dict] = None,
) -> tuple[FlightPhase, float]:
    """Classify flight phase from an ADS-B record.

    Args:
        record: dict with keys
            - on_ground (bool, required)
            - baro_altitude (float meters, optional)
            - velocity (float m/s, optional)
            - vertical_rate (float m/s, optional)
        previous: optional prior record for transition detection (takeoff/landing)

    Returns:
        (FlightPhase, confidence in [0.0, 1.0])
    """
    on_ground = bool(record.get("on_ground", False))
    alt = _nz(record.get("baro_altitude"))
    vel = _nz(record.get("velocity"))
    vr = _nz(record.get("vertical_rate"))

    # ── Transition detection (이전 record 있을 때) ──────────────────
    if previous is not None:
        prev_on_ground = bool(previous.get("on_ground", on_ground))
        # Ground → airborne transition → TAKEOFF
        if prev_on_ground and not on_ground:
            return FlightPhase.TAKEOFF, 0.95
        # Airborne → ground transition → LANDING
        if not prev_on_ground and on_ground:
            return FlightPhase.LANDING, 0.95

    # ── 지상 상태 ─────────────────────────────────────────────────
    if on_ground:
        if vel is not None and vel > _TAXI_VEL_M_S * 10:  # 50 m/s on ground = takeoff roll
            return FlightPhase.TAKEOFF, 0.7
        if vel is not None and vel > 0:
            return FlightPhase.TAXI, 0.9
        # velocity 미상: on_ground 상태만으로 TAXI 추정
        return FlightPhase.TAXI, 0.6

    # ── 공중 상태 ─────────────────────────────────────────────────
    # alt/vr 모두 missing이면 UNKNOWN
    if alt is None and vr is None:
        return FlightPhase.UNKNOWN, 0.0

    # TAKEOFF (지상 근처 급격한 상승 — rotation & initial climb만)
    # 500m 이상은 이미 CLIMB 구간
    if vr is not None and vr >= _TAKEOFF_VR_M_S and alt is not None and alt < 500:
        return FlightPhase.TAKEOFF, 0.85

    # LANDING (저고도 + 저속 + 하강)
    if alt is not None and alt < _LANDING_ALT_M:
        if vel is not None and vel < _LANDING_VEL_M_S and (vr is None or vr < 0):
            return FlightPhase.LANDING, 0.85
        return FlightPhase.APPROACH, 0.75

    # APPROACH (저고도 하강)
    if alt is not None and alt < _APPROACH_ALT_M:
        if vr is not None and vr <= _APPROACH_VR_M_S:
            return FlightPhase.APPROACH, 0.9
        return FlightPhase.APPROACH, 0.7

    # CRUISE (고고도 + 수평)
    if alt is not None and alt >= _CRUISE_ALT_M:
        if vr is None or abs(vr) <= _CRUISE_VR_M_S:
            return FlightPhase.CRUISE, 0.95
        if vr >= _CLIMB_VR_M_S:
            return FlightPhase.CLIMB, 0.85       # top-of-climb near cruise alt
        if vr <= _DESCENT_VR_M_S:
            return FlightPhase.DESCENT, 0.85     # top-of-descent
        return FlightPhase.CRUISE, 0.7

    # 저고도 공중 (LANDING_ALT < alt < CRUISE_ALT)
    if vr is not None:
        if vr >= _CLIMB_VR_M_S:
            return FlightPhase.CLIMB, 0.9
        if vr <= _DESCENT_VR_M_S:
            return FlightPhase.DESCENT, 0.9
        if vr <= _APPROACH_VR_M_S:
            return FlightPhase.APPROACH, 0.75

    # 분류 실패
    return FlightPhase.UNKNOWN, 0.3


def _nz(value) -> Optional[float]:
    """Cast to float, return None if missing or NaN."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


# ── Unit tests (when run as script) ────────────────────────────────────
if __name__ == "__main__":
    cases = [
        # (label, record, expected_phase)
        ("TAXI (on_ground, slow)",
         {"on_ground": True, "velocity": 3.0}, FlightPhase.TAXI),
        ("TAKEOFF (ground→air transition)",
         {"on_ground": False, "baro_altitude": 100, "velocity": 70, "vertical_rate": 8},
         FlightPhase.TAKEOFF),
        ("CLIMB (low alt, climbing)",
         {"on_ground": False, "baro_altitude": 2000, "vertical_rate": 10, "velocity": 180},
         FlightPhase.CLIMB),
        ("CRUISE (high alt, level)",
         {"on_ground": False, "baro_altitude": 11000, "vertical_rate": 0.3, "velocity": 240},
         FlightPhase.CRUISE),
        ("DESCENT (mid alt, descending)",
         {"on_ground": False, "baro_altitude": 5000, "vertical_rate": -5, "velocity": 220},
         FlightPhase.DESCENT),
        ("APPROACH (low alt, slow descent)",
         {"on_ground": False, "baro_altitude": 400, "vertical_rate": -3, "velocity": 90},
         FlightPhase.APPROACH),
        ("LANDING (very low, slow)",
         {"on_ground": False, "baro_altitude": 50, "vertical_rate": -2, "velocity": 55},
         FlightPhase.LANDING),
        ("LANDING (air→ground transition)",
         {"on_ground": True, "velocity": 40},
         FlightPhase.LANDING),
        ("UNKNOWN (missing data)",
         {"on_ground": False}, FlightPhase.UNKNOWN),
    ]

    prev = None
    print("=" * 70)
    print("  Flight Phase Classifier — Unit Tests")
    print("=" * 70)
    fail = 0
    for idx, (label, rec, expected) in enumerate(cases):
        # LANDING (transition) 케이스만 previous 제공
        if label.startswith("LANDING (air"):
            prev = {"on_ground": False, "baro_altitude": 100, "velocity": 50}
        else:
            prev = None
        phase, conf = classify_phase(rec, previous=prev)
        ok = phase == expected
        mark = "✅" if ok else "❌"
        print(f"  {mark} [{idx+1:02d}] {label:45s} → {phase.value:9s} (conf={conf:.2f})")
        if not ok:
            print(f"       expected={expected.value}")
            fail += 1

    print("=" * 70)
    print(f"  {len(cases) - fail}/{len(cases)} passed")
    print("=" * 70)
    exit(1 if fail else 0)
