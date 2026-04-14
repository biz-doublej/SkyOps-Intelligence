---
source: SkyOps Intelligence internal SOP
domain: sop
section: Anomaly Response
---

# SOP — 이상 탐지 대응 / Anomaly Response

## ALTITUDE_SPIKE 대응

**상황**: 항공기가 30초 내 ±500 ft 이상 급변 감지.

**즉시 조치**:
1. **Callsign 확인** + 비행 단계 (flight_phase)
2. **Phase 검증**:
   - TAXI / TAKEOFF: 정상 상승 가능 → 오탐지 확인
   - CRUISE: 비정상, 즉시 대응
   - APPROACH / DESCENT: 패턴 확인
3. **조종사 호출**: `"{Callsign}, verify altitude, we show you at FL{current}"`

**LOW 심각도**: 지속 모니터링
**MEDIUM**: Supervisor 알림
**HIGH**: TCAS (Traffic Collision Avoidance) advisory 발생 여부 확인 + 주변 기 분리 확인

## VELOCITY_SPIKE 대응

**상황**: 1분 내 ±100 knot 이상 속도 변화.

**단계**:
1. 위험 속도 범위 확인 (Vmo / Mmo 근접?)
2. 조종사에게 속도 확인 요청: `"{Callsign}, report airspeed"`
3. 이상 지속 시 기장(pilot in command) 상태 확인 (decompression, engine issue 가능성)

## PATH_DEVIATION 대응

**상황**: 예상 경로에서 10 km (5.4 NM) 이상 벗어남.

**체크리스트**:
1. 의도적 회피인가? (기상, TCAS RA, 요청 회항)
2. NAVAID 문제인가? (NOTAM 확인)
3. Communication 정상인가? (NORDO 가능성)

**조치**:
- 조종사 호출: `"{Callsign}, verify track, we show you X miles {direction} of course"`
- 30초 내 응답 없으면 **7600 squawk 준비** + 시각 신호
- 1분 내 응답 없으면 **Emergency 선언** + 인접 ATC 알림

## 비상 선언 (Declared Emergency)

조종사가 "MAYDAY" 선언 시:
1. **Clear airspace**: 반경 10 NM 트래픽 분산
2. **Direct vectors**: 가장 가까운 공항으로 priority routing
3. **CRASH 통보**: 공항 RFF (Rescue and Fire Fighting) 알림
4. **기록**: 시각, 위치, 상황, 취한 조치 모두 timestamped log
5. **Supervisor briefing**: Post-event 10분 내

## 문서화

모든 anomaly 대응은 다음 정보로 기록:
- Alert ID (UUID), Correlation ID
- Callsign, ICAO24, 위치 (lat/lon)
- 탐지 시각, 조치 시각, 해결 시각
- 사용된 분리 기준, 회피 기동
- Follow-up 필요 여부 (PIREP, NOTAM 발행 등)

→ `/anomaly/feedback` endpoint 로 analyst label 제공 (true_positive / false_positive / uncertain).
