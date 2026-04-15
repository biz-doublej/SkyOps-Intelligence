---
source: RKSI AIP + KAC SOP
domain: rksi_local
section: Winter Operations - De-icing
lang: en+ko
---

# RKSI — Winter Operations & De-icing

## De-icing 시설

- **제1여객터미널 (Concourse A·B·F)**: 7개 de-icing pad
- **제2여객터미널 (Concourse 4)**: 5개 de-icing pad
- **Type I/II/IV fluid** 사용 가능

## Holdover Time (HOT)

ATC와 조종사가 holdover time을 협의해 takeoff timing 결정. SAE Type IV (의도적 anti-icing) 의 일반 HOT:
- 강설 1mm/h: 35~75분
- 강설 2.5mm/h: 20~40분
- Light freezing rain: 10~30분

HOT 초과 시 anti-icing fluid의 공력 영향을 고려해 reapply 필요.

## CTAF (Cold Weather Operations) 트리거

- OAT (Outside Air Temperature) ≤ 5°C and visible moisture
- Frost on critical surfaces (wing, tail)
- 활주로 contamination report (snow, slush, ice)

## 활주로 마찰 측정

GRF (Global Reporting Format) 도입 (2021 ICAO Annex 14):
- RWYCC (Runway Condition Code) 0~6, 6 = dry
- 항공사는 RWYCC를 takeoff/landing performance 계산에 사용

## SkyOps와 결합

NOTAM `notam_class=AERODROME` 의 RUNWAY CONTAMINATED 메시지가 발행되면 ML phase classifier가 LANDING phase 모델의 contamination을 일시적으로 +0.02 (more sensitive) 로 조정해도 좋다 — Active learning loop이 winter season feedback 으로 자동 튜닝하길 기대한다.
