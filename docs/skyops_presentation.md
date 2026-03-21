---
marp: true
theme: default
paginate: true
size: 16:9
---

# SkyOps Intelligence
## 항공 지연 예측 및 실시간 이상 탐지 플랫폼

- 발표일: 2026-03-21
- 범위: 과거 운항 데이터 기반 지연 예측 + 실시간 스트림 기반 이상 탐지

---

# 1. 문제 정의

- 항공 지연은 승객 불편, 운영 비용 증가, 공항 혼잡 심화로 이어집니다.
- 실제 운영에서는 "이미 지연이 발생한 뒤" 대응하는 경우가 많습니다.
- 항공 운영 상황은 지연 예측과 실시간 이상 탐지를 함께 봐야 의미가 있습니다.
- 목표는 사후 대응을 줄이고 사전 경보 중심 운영으로 전환하는 것입니다.

---

# 2. 제안 솔루션

- 과거 운항 이력으로 출발 지연 시간을 예측합니다.
- 실시간 항공기 위치와 공항 기상 데이터를 받아 이상 이벤트를 탐지합니다.
- 결과를 Kafka, PyFlink, Redis 기반 파이프라인으로 연결합니다.
- 최종적으로는 운영자 대시보드와 의사결정 지원으로 이어집니다.

```text
Historical Data -> EDA -> Feature Engineering -> Delay Prediction Model

Real-time OpenSky + NOAA METAR
    -> Kafka
    -> PyFlink Window / CEP
    -> Redis
    -> Alert / Dashboard
```

---

# 3. 데이터 구성

- 과거 운항 데이터: U.S. DOT 2015 Flight Delays
- 원본 규모: 5,819,079행, 항공사 14개, 출발 공항 628개, 도착 공항 629개
- 모델링용 정제 데이터: 5,714,008행
- 실시간 항공기 위치: OpenSky ADS-B, 30초 주기
- 실시간 기상 데이터: NOAA METAR, 30분 주기
- 실시간 공항 범위: RKSI, RKSS, RKPC, RKPK, RKTN, RKTU, RKJJ, RKJB
- `gate-event` 토픽은 후속 단계에서 추가 예정입니다.

---

# 4. EDA 핵심 결과

- 시각화 기준: 500,000행 샘플, 2015-01-01 ~ 2015-02-03
- 지연 항공편 비율: 38.8%
- 취소 항공편 비율: 3.4%
- 지연 원인 컬럼 결측치가 매우 큽니다.
- 따라서 원인 컬럼은 설명용으로는 유용하지만 예측 입력값으로는 신중히 다뤄야 합니다.

<img src="../data/figures/01_missing_values.png" width="48%" />
<img src="../data/figures/03_delay_causes_top10.png" width="48%" />

---

# 5. EDA 인사이트

- `cancel_code` 결측치는 96.6%로 매우 높습니다.
- `weather_delay_min`, `carrier_delay_min`, `nas_delay_min` 등 원인 컬럼 결측치는 약 79.5%입니다.
- 시간대별, 항공사별 지연 패턴이 분명하게 존재합니다.
- 즉, 지연은 단일 변수보다 "시간 + 노선 + 항공사 + 운영 상태"의 조합으로 설명하는 것이 적절합니다.

<img src="../data/figures/04_delay_by_carrier.png" width="48%" />
<img src="../data/figures/05_delay_by_hour.png" width="48%" />

---

# 6. Feature Engineering 설계

- 최종 설계 Feature: 26개
- 생성 결과 데이터: 5,714,008행 x 47컬럼
- 정제 데이터 기준 출발 지연 평균: 9.24분
- 정제 데이터 기준 15분 초과 지연 비율: 17.7%

주요 Feature 그룹:

- 시간: `dep_hour`, `dep_dayofweek`, `dep_month`, `dep_block`
- 노선/공항: `origin`, `dest`, `route`, `distance_miles`
- 연쇄 지연: `prev_dep_delay_min`, `prev_arr_delay_min`, `is_prev_delayed`
- 혼잡도: `origin_hourly_departures`, `dest_hourly_arrivals`
- 기상 이력: `dep_month_weather_score`, `origin_weather_hist_delay`
- 통계 인코딩: `carrier_hist_delay`, `route_hist_delay`

---

# 7. 데이터 누설 방지 원칙

- 예측 시점 이후에만 알 수 있는 값은 학습 입력에서 제외했습니다.
- `arr_delay_min`은 출발 이후 결정되므로 제외합니다.
- `weather_delay_min`, `carrier_delay_min` 등 원인 지연 컬럼은 추론 시 제외 대상입니다.
- `act_dep_time`, `act_arr_time` 같은 실제 시각도 사전 예측에는 사용할 수 없습니다.
- 즉, "운영자가 출발 전에 실제로 볼 수 있는 정보" 중심으로 Feature를 설계했습니다.

---

# 8. 실시간 스트리밍 아키텍처

- `flight-position` 토픽: OpenSky 위치 데이터, 30초 주기
- `weather-event` 토픽: NOAA METAR 데이터, 30분 주기
- PyFlink 프로세서: 5분 윈도우 집계 + 30초 슬라이딩 평가
- Redis 저장: 항공기 최신 상태, 윈도우 집계 결과, 이상 이벤트 스트림

```text
OpenSky Producer  -> Kafka topic: flight-position ---+
                                                     |
NOAA Producer     -> Kafka topic: weather-event -----+-> PyFlink
                                                          |- 5min window aggregation
                                                          |- CEP rule evaluation
                                                          `- Redis latest state / anomaly stream
```

---

# 9. CEP 이상 탐지 규칙

- 고도 급변: 30초 기준 500ft 이상 변화
- 속도 이상: 1분 기준 100kt 이상 변화
- 경로 이탈: 예상 경로 대비 10km 이상 이탈
- 각 이벤트는 `LOW`, `MEDIUM`, `HIGH` 심각도로 분류됩니다.
- 운영자는 개별 항공기 상태와 이상 이벤트를 동시에 확인할 수 있습니다.

예상 활용:

- 비정상 강하/상승 조기 감지
- 속도 급변 이벤트 탐지
- 계획 경로 이탈 탐지
- 기상 악화와 이상 이벤트의 동시 모니터링

---

# 10. 현재 성과와 한계

현재까지 성과:

- 과거 데이터 EDA 완료
- 26개 Feature 설계 및 5.7M행 전처리 완료
- Kafka Producer 2종 구현 완료
- PyFlink 기반 실시간 집계 및 CEP 룰 구현 완료
- Redis 기반 최신 상태/이상 이벤트 적재 구조 확보

현재 한계:

- EDA 시각화는 500,000행 샘플 기준입니다.
- 예측 모델 학습 및 성능 비교는 다음 단계입니다.
- `gate-event` 실시간 이벤트는 아직 미구현입니다.

---

# 11. 다음 단계

- `prepare_dataset.py`로 시계열 분할 데이터셋 생성
- XGBoost 또는 LightGBM 기반 지연 예측 모델 학습
- 회귀와 이진 분류 성능을 함께 평가
- 실시간 기상/항공기 이벤트와 예측 결과를 통합
- 대시보드와 운영 경보 시나리오까지 연결

---

# 12. 기대 효과

- 출발 전 지연 가능성 예측으로 선제 대응 가능
- 실시간 이상 탐지로 운영 안전성과 가시성 향상
- 데이터 기반 의사결정으로 관제/운항/공항 운영 협업 강화
- 장기적으로는 공항 운영 디지털 트윈의 기반이 될 수 있습니다.

---

# Q&A

- 감사합니다.
- 질문 부탁드립니다.
