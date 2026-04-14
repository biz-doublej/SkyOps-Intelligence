---
source: SkyOps SOP + FAA AIM 5-4-21
domain: sop
section: Go-Around
---

# SOP — 고어라운드 / Go-Around Procedure

## Go-Around Trigger

조종사가 final approach 중 다음 상황 시 go-around 수행:
1. **Unstable approach**: 1000 ft AAL에서 airspeed ±10 kt, sink rate >1000 fpm, 미정렬 glidepath >1 dot
2. **Runway incursion**: 활주로 점유 (다른 항공기, 차량, 동물)
3. **Traffic conflict**: 선행기 미활성 (아직 runway exit 안함)
4. **Weather deterioration**: 접근 중 ceiling/visibility 급감
5. **TCAS RA**: Resolution Advisory 발동
6. **ATC 지시**: `"GO AROUND"` 관제 지시

## 조종사 절차 (표준)

1. **Thrust TOGA**: Takeoff/Go-Around thrust 설정
2. **Pitch up**: rotate to 15° (초기), fly pitch + speed reference
3. **Positive climb rate** 확인
4. **Gear up**: 상승 확인 후 landing gear retract
5. **Flaps**: incremental retract (25° → 15° → 5° → up) with speed 증가
6. **Missed approach procedure**: 공항별 지정된 MAP (Missed Approach Procedure) 경로 수행
7. **ATC 통보**: `"{Callsign}, going around"` (통상 positive climb 확인 후 즉시)

## 관제사 대응

**우선순위 있음** — 접근 항공기가 다시 pattern으로 진입하려면 다른 traffic과 분리 필요.

**액션**:
1. **Acknowledge**: `"{Callsign}, roger, going around, {instructions}"`
2. **Traffic separation**:
   - 다른 접근기와 3~5 NM 분리 유지
   - Departure traffic과 수직/횡적 분리
3. **Reroute**: Radar vector for re-sequencing 또는 holding
4. **Original runway**: 문제 해결 후 다시 사용 가능한 상태인지 확인

## 통계 / 빈도

일반적인 go-around 비율:
- 대형 국제 공항 (JFK, LAX, LHR, ICN): **~0.3%** of all approaches
- Weather-heavy 환경: 최대 1~2%
- 주요 원인: wind shear, runway occupancy, unstable approach

Go-around는 **안전 조치**로 비정상 이벤트 아님. 펜딩되지 않는 한 문서 의무 없음.

## SkyOps 연계

Phase classifier가 "APPROACH → CLIMB 전환"을 감지하면 go-around 가능성. 이상 탐지 시스템:
- Altitude rising during final approach → go-around 추정
- 자동 log: `anomaly_type=GO_AROUND_DETECTED`, severity=INFO

RAG 어시스턴트에게 다음 질의 가능:
```
"Flight {Callsign} just did a go-around on RWY 33L. What are the standard
next steps for ATC to re-sequence?"
```
