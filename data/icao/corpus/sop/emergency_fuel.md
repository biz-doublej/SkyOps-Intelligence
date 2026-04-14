---
source: SkyOps SOP + FAA Order 7110.65 reference
domain: sop
section: Fuel Emergency
---

# SOP — 연료 비상 대응 / Emergency Fuel Response

## 연료 상태 분류

**Normal**: Filed alternate + 45분 reserve 이상.
**Minimum Fuel**: Alternate 없이 landing 시 45분 이하. 운영상 고려 사항, 비상 아님.
**Emergency Fuel**: Alternate 포함 landing 후 30분 이하. **MAYDAY FUEL** 선언 권장.

## 조종사의 표준 무선 Phraseology

- Minimum: `"{Callsign}, MINIMUM FUEL"`
- Emergency: `"MAYDAY MAYDAY MAYDAY, {Callsign}, FUEL EMERGENCY, FUEL REMAINING {N} MINUTES, REQUEST PRIORITY LANDING {airport}"`

## 관제사 대응 (Controller Actions)

1. **Immediate acknowledgment**: `"{Callsign}, ROGER FUEL EMERGENCY, CLEARED DIRECT {airport}"`
2. **Priority routing**: 가능한 최단 경로, vector 제공. 다른 트래픽은 clear.
3. **Emergency equipment**: Tower + RFF 통보 (대기 상태로 전환)
4. **Altitude block**: Unrestricted altitude 부여 (조종사 재량)
5. **Language simplicity**: 단순 영어 사용, 복잡 용어 피함

## 우선권 (Priority)

Fuel Emergency는 다른 모든 traffic 대비 최우선. 단, Hijack (7500), Medical Emergency, Structural Emergency 는 동등 우선권.

## Post-Landing

1. Rollout 후 taxi 지시 — **short route to gate**
2. RFF standby (필요 시 tow bar 사용)
3. Fuel tanker 즉시 배치
4. **Report filing**: pilot statement + tower log + RFF log → 항공 당국 (FAA/MOLIT)

## 재연료 지연 방지

- Emergency fuel 선언 항공기는 재출발 전 **반드시 fuel replenishment**
- 지연 연료 공급 시 다시 Emergency 재발 가능 → 문서화 필요
- 항공사 OCC에 **dispatch hold** 요청 가능

## Case Study: KE081 2024-XX-XX

(가상 사례) 인천→로스앤젤레스 장거리 노선. 강한 jet stream 역풍으로 연료 소비 증가. LAX 50 NM 전에서 "MINIMUM FUEL" 선언, 최종 접근 중 "EMERGENCY FUEL"로 승격. LAX tower가 29L priority landing 승인, RFF stand-by. 무사 착륙 후 runway 29R exit + shortest taxi route. 후속: OCC 재연료 + 30분 지연 출발.
