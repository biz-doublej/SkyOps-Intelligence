---
source: IATA AHM (Airport Handling Manual) summary
domain: airport_ops
section: Ground Handling Safety
lang: en+ko
---

# Ground Handling Safety

## Ramp Safety

- **GSE (Ground Support Equipment)** 와 항공기 충돌이 ramp incident 의 35%
- 모든 GSE 는 항공기 접근 시 최저 속도, 정해진 wing-tip clearance 유지
- Engine running 상태에서 ramp staff: 위험 구역 (intake hazard area + jet blast danger zone) 절대 진입 금지

## FOD (Foreign Object Debris)

- 활주로/유도로의 FOD: 엔진 ingestion → catastrophic 손상 가능 (Concorde AF4590)
- 매 운항 turn-around 종료 후 FOD walk 필수
- KAC RKSI: 자동 FOD detection radar (FODetect) 운영

## Pushback / Towing

- 토우바 (towbar): aircraft type별 정규 모델 사용
- Towless tractor: nose wheel 직접 lift, 신속하지만 정확한 alignment 필요
- Communication: tug operator + cockpit + wingwalker (저시정 시) 3-way

## Lightning / Severe Weather

- 번개 5 NM 이내 감지: 모든 ramp 활동 중지, GSE 격납
- 평균 RKSI 봄/여름 thunderstorm 으로 ramp shutdown 연간 ~25시간
- SkyOps WeatherEvent 의 `severe_weather` flag와 결합해 자동 알람

## Bird strike

- BASH (Bird Aircraft Strike Hazard) prevention: 공항별 wildlife management plan
- RKSI: 4계절 야생동물 매뉴얼 (해안 매립지 특성)
- Bird strike 보고: NTSB / 한국 항공철도사고조사위원회

## SkyOps와 연결

NOTAM AERODROME / OPS 카테고리에 ground handling 관련 알림이 자주 등장. 본 corpus는 LLM이 NOTAM을 해석할 때 도메인 컨텍스트를 제공한다.
