---
source: IATA Ground Operations Manual (paraphrase) + KAC SOP
domain: airport_ops
section: Turn-around Process
lang: en+ko
---

# Turn-around Process Optimization

## 표준 turn-around time (분)

| Aircraft type | Min turn | Standard | Extended (low-cost / hub) |
|---------------|----------|----------|-------------------------|
| B737/A320 narrow-body | 25 | 35 | 50 |
| A330 wide-body | 50 | 70 | 90 |
| B777-300ER | 65 | 90 | 120 |
| A380 | 90 | 120 | 150 |

## Critical path 활동

1. **Disembark** — 1st 승객부터 10~20분 (도어 1개) / 5~10분 (jet bridge 2개)
2. **Cleaning** — 평균 12분 (narrow), 25분 (wide)
3. **Catering** — door L1/R2 동시 진행, 8~15분
4. **Fueling** — 1500~3000 GPM 펌프, narrow 8~12분, wide 25~40분
5. **Cargo/baggage** — 평균 15~25분
6. **Boarding** — 첫 승객 호출 부터 push-ready 까지 25~35분

## SkyOps rotation feature 와 연결

`actual_turnaround_min` 과 `scheduled_turnaround_min` 의 차이가 cascade delay 의 가장 강한 predictor (XGBoost SHAP 상위 5위 안). 이 corpus는 LLM 안내문 생성 시 "왜 지연됐는지" 설명에 참고된다.

## OTP (On-Time Performance)

- D-15 (departure 지연 15분 이내): 글로벌 평균 78%, 한국 90%+ (정시성 우수)
- A-15 (arrival 지연 15분 이내): 도착이 더 어려움 (route weather 영향), 평균 75%

## 지연 원인 카테고리 (IATA Delay Codes)

- 06: Late arrival of inbound flight (rotation delay)
- 11~18: Passenger / baggage handling
- 21~25: Cargo / mail
- 31~38: Aircraft / ramp handling
- 41~48: Technical / equipment
- 71~75: Weather (origin / en-route / destination)
- 81~89: ATC restriction
- 91~99: Reactionary (downstream rotational)

EUROCONTROL CODA Q2 2019 통계: reactionary delay는 전체 delay 의 약 45%를 차지 — 즉 rotation feature가 SkyOps에서 가장 영향력 있는 이유.
