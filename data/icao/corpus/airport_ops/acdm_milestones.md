---
source: EUROCONTROL A-CDM Implementation Manual (paraphrase + summary)
domain: airport_ops
section: A-CDM Milestones
lang: en+ko
---

# A-CDM (Airport Collaborative Decision Making) — 16 Milestones

A-CDM은 공항 운영 주체(공항 운영사, 항공사, 지상조업, ATC, 출입국 관리)가 turn-around 과정에서 표준 milestones를 공유해 운영 가시성과 예측 가능성을 높이는 EUROCONTROL 표준이다.

## Inbound Phase

1. **EOBT** — Estimated Off-Block Time (origin)
2. **TOBT** — Target Off-Block Time (destination 출발 예정)
3. **EXOT** — Expected Taxi-Out Time
4. **TSAT** — Target Start-up Approval Time

## Turn-around 16 Milestones

1. ATC FPL Submission
2. EOBT − 2h: Initial Information completed
3. EOBT − 1h: TOBT established
4. EOBT − 40m: TSAT calculation
5. EOBT − 30m: Final TOBT/TSAT publication
6. ARO (Aircraft Readiness Out): boarding complete + doors closed
7. Boarding completed
8. Pushback approved (TSAT acceptance)
9. Pushback initiated
10. Engine start-up
11. Taxi out from gate
12. Take-off
13. Take-off (in air)
14. Reached cruising altitude (TOC)
15. Top of Descent (TOD)
16. Touch down

## SkyOps와 매핑

A-CDM의 milestone들은 SkyOps의 canonical event model에서:
- TOBT/TSAT → `FlightLegEvent.scheduled_*` 필드
- Pushback → `SurfaceMovementEvent` (taxi 진입)
- Taxi out / Take-off / TOC → `FlightPositionEvent` 의 phase 변화 (TAXI → TAKEOFF → CLIMB → CRUISE)

XGBoost 지연 예측에서 가장 중요한 입력은 EOBT - 30m 시점의 TSAT, ATFM slot, 기상 condition. 본 corpus는 RAG 기반 LLM advisory에서 운영 컨텍스트를 설명할 때 참고된다.

## 한국 A-CDM (KAC ICCC)

KAC(한국공항공사)는 인천·김포·제주 3개 공항에 ICCC(Integrated Collaborative Coordination Center)를 운영. EUROCONTROL A-CDM과 호환되는 milestone 체계.
