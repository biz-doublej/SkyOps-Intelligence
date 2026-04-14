---
source: SkyOps SOP
domain: sop
section: Weather Diversion
---

# SOP — 기상 회항 / Weather Diversion

## Trigger 조건

공항 기상 조건이 landing minima 미달:
- **CAT I**: ceiling < 200 ft 또는 RVR < 550 m
- **CAT II**: ceiling < 100 ft 또는 RVR < 300 m
- **CAT III**: ceiling < 50 ft 또는 RVR < 200 m
- **Crosswind**: 허용 한계 초과 (대개 25~35 kt)
- **Thunderstorm**: 공항 반경 5 NM 이내 + CB cloud

## 조종사 결정 절차

1. **Hold 시도**: 가능하면 holding pattern으로 대기 (연료 허용 범위)
2. **Alternate 재평가**: Filed alternate 기상 확인 → Suitable?
3. **New alternate**: 필요 시 ATC에 alternate change 요청
4. **공표 (Diversion declared)**: `"{Callsign}, diverting to {alternate}"` + ATC 확인

## ATC 대응

- Priority vectoring to alternate
- Fuel state 확인 (Emergency Fuel 가능성)
- Original destination approach: **cleared of other traffic** (re-attempt 대비)
- Alternate airport tower 사전 통보

## Dispatch / OCC 조치

- **Ground handling**: alternate airport에 승객 수용 대책 (버스, 호텔)
- **Fuel**: alternate 재연료 + 최종 목적지 재출발 fuel 계산
- **Crew duty time**: 비행 시간 연장으로 duty limit 접근 시 crew replacement 고려
- **Passenger communication**: 기내 방송 + alternate 공항 도착 후 지상 안내

## 비용 영향

Diversion 1건 당 예상 비용 (참고):
- 추가 연료: $5K ~ $15K (기종별)
- 공항 landing/handling fee: $3K ~ $10K
- 승객 보상/호텔: $200/pax × 승객수
- Crew 대기 + 숙박: $2K ~ $5K

총 $10K ~ $50K 수준 — **사전 예측 + 회피가 핵심**.

## SkyOps 예측 연계

[[docs/event_model.md]] WeatherEvent 스트림에서 alternate airport 기상 지속 모니터링. RAG 어시스턴트가 diversion option을 실시간 제안:

```
User: "Paris CDG weather below minima, what are my options?"
RAG: "Suitable alternates within 100 NM: ORY (Paris Orly), LFPB (Le Bourget),
     BRU (Brussels). Current weather:
       ORY: VMC, runway 06/24 open
       LFPB: IFR, CAT I approach ok
       BRU: VMC, recommended as primary alternate due to widebody handling"
```
