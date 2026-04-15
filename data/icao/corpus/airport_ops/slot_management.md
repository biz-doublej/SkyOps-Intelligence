---
source: IATA Worldwide Airport Slot Guidelines (paraphrase)
domain: airport_ops
section: Slot Management
lang: en+ko
...
---

# Airport Slot Management

## Slot 종류

- **Historic slots**: 이전 시즌 80% 이상 운항한 항공사가 다음 시즌 동일 시간대에 우선권
- **New entrant slots**: pool slots 의 50%를 신규 항공사 우대
- **Pool slots**: 회수된 historic + 신규 capacity, 6주마다 재배정

## RKSI Capacity (시간당 declared capacity)

- 평시: 90 movements/hour
- 야간 (23~06 KST): 50/hour
- IFR low visibility: 70/hour (평행 활주로 dependent ops)
- 단일 활주로 운영 시 (정비/사고): 35/hour

## Slot vs Schedule Coordinator

- **Level 3** 공항: capacity 부족, slot 강제 (RKSI Level 3)
- **Level 2** 공항: facilitated, voluntary (RKSS 김포)
- **Level 1** 공항: 제한 없음

## ATFM CTOT (Calculated Take-Off Time)

EUROCONTROL NM B2B / FAA TFMS는 demand-capacity imbalance 시 CTOT 발행. 조종사는 CTOT − 5min ~ CTOT + 10min window 안에 takeoff 해야 함. SkyOps의 ATFMRestrictionEvent 의 expected_delay_min 필드는 CTOT - EOBT 로 계산.

## SkyOps와 연결

slot management 정보는:
- 지연 예측 input feature (`hourly_departures`, capacity utilization)
- Anomaly detection의 false positive 감소 (slot 대기 holding은 정상)
- 승객 안내문에서 "ATC slot 대기로 인한 지연" 설명 컨텍스트
