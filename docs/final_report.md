# SkyOps Intelligence — 최종 리포트

## 실시간 항공 운항 이상 탐지 및 AI 관제 보조 플랫폼

**2026학년도 1학기 캡스톤디자인**
**팀명:** DoubleJ | **학과:** 빅데이터과 | **팀장:** 정재원
**지도교수:** 조상구

---

## 목차

1. 서론
2. 문제 정의 및 목표
3. 관련 연구
4. 시스템 아키텍처
5. 데이터 수집 및 파이프라인
6. AI 모델링
7. LLM 파인튜닝 및 RAG
8. 서빙 및 API
9. 실시간 대시보드
10. 성능 평가
11. 한계 및 개선 방향
12. 결론
13. 참고문헌

---

## 1. 서론

항공 산업은 전 세계적으로 연간 40억 명 이상의 승객을 운송하며, 항공편 지연은 공항 운영 비용 증가와 승객 불편을 직접적으로 유발한다. 미국 FAA에 따르면 항공편 지연으로 인한 경제적 손실은 연간 약 330억 달러에 달한다.

본 프로젝트 SkyOps Intelligence는 실시간 항공 운항 데이터를 활용하여 지연을 사전 예측하고, 비정상 비행 패턴을 자동 탐지하며, 항공 도메인 특화 LLM을 통해 관제사에게 자연어로 원인 설명과 대응 절차를 제공하는 통합 AI 관제 보조 플랫폼이다.

**핵심 기여:**
1. Kafka/PyFlink 기반 실시간 스트리밍 파이프라인 구축
2. XGBoost + Isolation Forest 기반 지연 예측 및 이상 탐지 모델 개발
3. Qwen2.5-7B 기반 항공 도메인 특화 LLM 자체 개발 (QLoRA + DPO)
4. ChromaDB + LangChain RAG 기반 관제 어시스턴트 구현
5. Next.js 실시간 관제 대시보드 및 AI 챗봇 UI 구축

---

## 2. 문제 정의 및 목표

### 2.1 문제 정의

1. 현재 항공편 지연 예측 시스템은 대부분 배치 기반으로 운영되어 실시간 대응이 불가능하다.
2. 비정상 비행 패턴(급격한 고도/속도 변화, 경로 이탈)을 즉시 탐지하고 원인을 설명할 수 있는 통합 AI 시스템이 부재하다.
3. 관제 SOP 및 FAA/ICAO 규정에 특화된 도메인 LLM이 없어, 이상 발생 시 자연어 대응 안내가 불가능하다.

### 2.2 프로젝트 목표

| 목표 | 세부 내용 | 달성 여부 |
|------|-----------|----------|
| 실시간 파이프라인 | Kafka + Flink + Redis 스트리밍 구축 | O |
| 지연 예측 | XGBoost RMSE 15분 이하 | △ (24.64분) |
| 이상 탐지 | Isolation Forest F1 0.85 이상 | X (0.335) |
| 도메인 LLM | QLoRA + DPO 파인튜닝 | O |
| RAG 통합 | ChromaDB + LangChain | O |
| API 서빙 | FastAPI + vLLM | O |
| 대시보드 | Next.js 실시간 관제 화면 | O |

---

## 3. 관련 연구

### 3.1 항공편 지연 예측

항공편 지연 예측은 머신러닝 분야에서 활발히 연구되고 있다. Rebollo & Balakrishnan (2014)은 Random Forest를 활용한 지연 전파 모델을 제안하였고, Kim et al. (2016)은 딥러닝 기반 지연 예측 모델을 개발하였다. 본 연구에서는 XGBoost + Optuna 하이퍼파라미터 최적화를 적용하여 해석 가능한 트리 기반 모델을 채택하였다.

### 3.2 비행 이상 탐지

비정상 비행 패턴 탐지는 ADS-B 데이터를 활용한 연구가 증가하고 있다. Olive & Basora (2019)는 궤적 클러스터링을 통한 이상 탐지를 제안하였다. 본 연구에서는 Isolation Forest와 Complex Event Processing(CEP) 룰 엔진을 앙상블하여 실시간 이상 탐지를 구현하였다.

### 3.3 LLM 도메인 특화

대규모 언어 모델의 도메인 특화는 QLoRA(Dettmers et al., 2023)와 DPO(Rafailov et al., 2023)의 등장으로 효율적으로 가능해졌다. 본 연구에서는 Qwen2.5-7B-Instruct를 베이스로 항공 관제 도메인 데이터 약 95K건으로 파인튜닝하였다.

---

## 4. 시스템 아키텍처

### 4.1 5-Layer 아키텍처

본 시스템은 5개 레이어로 구성된다:

- **Layer 1 (데이터 수집):** OpenSky ADS-B API, NOAA METAR/TAF, FAA ASPM, Kaggle 데이터
- **Layer 2 (스트리밍 처리):** Apache Kafka 3토픽, PyFlink 5분 윈도우 집계, Redis 상태 캐싱, CEP 룰 엔진
- **Layer 3 (AI 모델):** XGBoost 지연 예측, Isolation Forest 이상 탐지, Qwen2.5-7B QLoRA+DPO LLM, ChromaDB + LangChain RAG
- **Layer 4 (서빙):** FastAPI REST/WebSocket API 13개 엔드포인트, Prometheus 메트릭
- **Layer 5 (대시보드):** Next.js 16 실시간 관제 대시보드 6개 페이지

### 4.2 기술 스택

| 영역 | 기술 |
|------|------|
| 스트리밍 | Apache Kafka 7.5, PyFlink, Redis 7.2 |
| ML | XGBoost 2.0, Optuna, Isolation Forest, SHAP |
| LLM | Qwen2.5-7B, QLoRA (TRL/PEFT), DPO, vLLM (AWQ 4-bit) |
| RAG | LangChain LCEL, ChromaDB, BAAI/bge-m3 |
| API | FastAPI, Pydantic v2, WebSocket |
| 프론트엔드 | Next.js 16, TypeScript, Tailwind CSS, react-leaflet, MapLibre GL |
| MLOps | MLflow, Airflow, EvidentlyAI, Prometheus |
| 인프라 | Docker, Docker Compose |

---

## 5. 데이터 수집 및 파이프라인

### 5.1 데이터 소스

| 소스 | 용도 | 규모 |
|------|------|------|
| Kaggle Flight Delay | XGBoost 학습 | 13,969건 |
| OpenSky Network | 실시간 ADS-B | 60~80대/30초 |
| LiveATC.net | ATC 교신 음성 | 10시간 |
| ICAO 문서 (AIM, FAR) | QA 데이터 생성 | PDF 다수 |
| GPT-4 API | QA 쌍 자동 생성 | ~60,000건 |

### 5.2 Kafka 스트리밍 파이프라인

- **토픽 3종:** flight-position (3파티션), weather-event (3파티션), gate-event (3파티션)
- **Producer:** OpenSky API 30초 폴링, METAR API 10분 폴링
- **Consumer:** PyFlink 5분 슬라이딩 윈도우 집계
- **State Store:** Redis ZSET (항공기 인덱스) + HASH (항공기 상태) + LIST (이상 이벤트)
- **TTL:** 항공기 상태 600초, 이상 이벤트 최근 1,000건

### 5.3 Feature Engineering

20개 수치형 Feature + 3개 범주형 Feature를 설계하였다.

**주요 Feature 그룹:**
1. 시간 Feature: dep_hour, dep_dayofweek, dep_month, dep_dayofyear, is_weekend
2. 노선 Feature: distance_miles, sched_elapsed_min
3. 이력 Feature: prev_dep_delay_min, prev_arr_delay_min, carrier_hist_delay, route_hist_delay
4. 혼잡 Feature: origin_hourly_departures, dest_hourly_arrivals
5. 기상 Feature: dep_month_weather_score, origin_weather_hist_delay

---

## 6. AI 모델링

### 6.1 XGBoost 지연 예측

Optuna를 활용한 하이퍼파라미터 최적화 (30 trials)와 5-Fold Cross Validation을 수행하였다.

**Validation Set 최종 성능:**
- RMSE: 24.64분 | MAE: 11.50분 | R²: 0.090 | 지연 정확도: 88.3%

**SHAP 해석 결과 (상위 5 Feature):**
1. dep_dayofyear (5.702) — 계절/성수기 패턴
2. prev_arr_delay_min (2.930) — 직전편 도착 지연 (Cascade)
3. route_hist_delay (2.401) — 노선 구조적 지연
4. dep_hour (1.871) — 저녁 시간대 누적 지연
5. carrier_hist_delay (0.869) — 항공사 이력 지연

### 6.2 Isolation Forest 이상 탐지

비지도 학습 기반 이상 탐지 모델로, contamination=0.05 설정으로 학습하였다.

**최적 임계값 성능:** Precision 0.359, Recall 0.314, F1 0.335

### 6.3 CEP 룰 엔진

실시간 ADS-B 스트림에서 3가지 이상 패턴을 감지한다:
- ALTITUDE_SPIKE: 고도 급변 (기준 152m/30초)
- VELOCITY_SPIKE: 속도 이상 (기준 50m/s/30초)
- PATH_DEVIATION: 경로 이탈 (기준 5km)

---

## 7. LLM 파인튜닝 및 RAG

### 7.1 학습 데이터 구축

총 약 95,000건의 항공 도메인 학습 데이터를 구축하였다:
- ATC 교신 STT (Whisper large-v3): 10시간 → 정제 텍스트
- GPT-4 QA 자동 생성: ~60,000건
- 이상 탐지 자연어 설명: ~10,000건
- 승객 안내문 한/영 페어: ~5,000건

### 7.2 QLoRA SFT 학습

| 항목 | 값 |
|------|-----|
| 베이스 모델 | Qwen/Qwen2.5-7B-Instruct |
| LoRA rank/alpha | 64/16 |
| Train Loss → Eval Loss | 0.1053 → 0.0445 |
| Eval Token Accuracy | 97.88% |
| 학습 시간 | 9시간 (RTX 3070 8GB) |

### 7.3 DPO 선호도 정렬

| 항목 | 값 |
|------|-----|
| DPO beta | 0.1 |
| Eval Loss | 0.02943 (SFT 대비 34% 개선) |
| Rewards Accuracy | 100% (step 20부터) |
| Rewards Margins | 0.80 → 8.91 (안정적 수렴) |
| 학습 시간 | 12시간 (RTX 3070 8GB) |

### 7.4 AWQ 양자화 및 vLLM 서빙

- AWQ 4-bit 양자화 (autoawq): 47분 소요
- vLLM awq_marlin 커널로 서빙
- GPU 메모리: 5.2 GiB / 8.0 GiB
- 추론 속도: 5~13 tok/s

### 7.5 RAG (Retrieval-Augmented Generation)

- 벡터 DB: ChromaDB (FAA SOP, NOTAM 문서 임베딩)
- 임베딩 모델: BAAI/bge-m3 (CPU 추론)
- 프레임워크: LangChain LCEL (Retriever → LLM)
- Top-K: 4문서, Temperature: 0.2

---

## 8. 서빙 및 API

### 8.1 FastAPI 엔드포인트 (13개)

| 엔드포인트 | 메서드 | 설명 | 평균 응답 |
|-----------|--------|------|----------|
| /health | GET | 서버 상태 | ~5ms |
| /predict/delay | POST | 지연 예측 | ~11ms |
| /predict/delay/batch | POST | 배치 예측 | ~50ms |
| /detect/anomaly | POST | 이상 탐지 | ~15ms |
| /chat | POST | AI 관제 어시스턴트 | ~960ms (직접) |
| /explain/anomaly | POST | 이상 탐지 LLM 설명 | ~3~5초 |
| /generate/announcement | POST | 승객 안내문 생성 | ~3~5초 |
| /aircraft/live | GET | 실시간 항공기 위치 | ~5ms |
| /aircraft/h3 | GET | H3 밀집도 집계 | ~10ms |
| /anomaly/recent | GET | 최근 이상 이벤트 | ~5ms |
| /ws/aircraft | WS | 항공기 위치 (3초) | — |
| /ws/anomalies | WS | 이상 이벤트 (1초) | — |
| /metrics | GET | Prometheus 메트릭 | — |

### 8.2 한국어 후처리

Qwen2.5 모델의 중국어 코드스위칭 문제를 해결하기 위해 `_clean_korean()` 후처리 필터를 구현하였다. 중국어 비율 30% 이상인 줄을 제거하고, 한국어 부분만 추출하는 방식이다.

---

## 9. 실시간 대시보드

### 9.1 기술 구성

Next.js 16 (App Router) + TypeScript + Tailwind CSS 기반의 6페이지 대시보드를 구현하였다.

### 9.2 페이지 구성

| 페이지 | 기능 |
|--------|------|
| 대시보드 (/) | KPI 카드 4종, 최근 알림, 항공기 요약 |
| 실시간 지도 (/map) | Leaflet 라이브맵, WebSocket + SWR fallback |
| 이상 탐지 (/anomaly) | 실시간 알림 피드, 심각도 필터, AI 분석 버튼 |
| 지연 예측 (/predict) | 항공사/공항 선택 폼, XGBoost 결과 표시 |
| 혼잡도 맵 (/heatmap) | MapLibre GL H3 Resolution 5 히트맵 |
| AI 어시스턴트 (/chat) | RAG 채팅, 시나리오 3종, 승객 안내문 생성 |

### 9.3 실시간 데이터 연동

- WebSocket 우선 연결 (자동 재연결, 지수 백오프)
- SWR 폴링 fallback (5초 간격)
- Mock 데이터 지원 (오프라인 데모)

---

## 10. 성능 평가

### 10.1 종합 성능 요약

| 구분 | 지표 | 목표 | 실측 | 달성 |
|------|------|------|------|------|
| 지연 예측 | RMSE | 15분 이하 | 24.64분 | △ |
| 지연 예측 | 분류 정확도 | 75% 이상 | 88.3% | O |
| 이상 탐지 | F1 Score | 0.85 이상 | 0.335 | X |
| LLM | Train Loss | — | 0.1053 | O |
| LLM | Eval Token Acc | — | 97.88% | O |
| DPO | Rewards Accuracy | — | 100% | O |
| LLM 평가 | ROUGE-L | — | 0.169 | — |
| API 응답 | 지연 예측 | 500ms 이하 | 11ms | O |

### 10.2 SHAP Feature Importance 해석

상위 10개 Feature 분석을 통해 항공편 지연의 구조적 원인을 파악하였다:
- **Cascade Delay** 효과: 직전편 지연이 체인처럼 전파
- **노선 구조적 패턴**: 특정 노선의 반복적 지연 구조
- **시간대 효과**: 저녁 17~21시 지연 누적 (Ripple Effect)

---

## 11. 한계 및 개선 방향

### 11.1 주요 한계

1. **지연 예측 RMSE 목표 미달** (24.64분 vs 목표 15분) — 미국 데이터 기반, 한국 공항 특성 미반영
2. **이상 탐지 F1 극도로 낮음** (0.335 vs 목표 0.85) — 레이블 품질 문제, 비지도 학습 한계
3. **LLM 한국어 코드스위칭** — Qwen2.5의 중국어 기본 언어 특성
4. **단일 GPU 제약** — RTX 3070 8GB로 추론 속도 5~13 tok/s

### 11.2 개선 방향

1. 한국공항공사 ACDM 실데이터 확보
2. Autoencoder 기반 이상 탐지 모델 변경
3. 한국어 특화 LLM (SOLAR, KULLM) 전환
4. GPU 업그레이드 (A100) 및 분산 서빙

---

## 12. 결론

SkyOps Intelligence는 15주간의 캡스톤디자인 프로젝트로, 실시간 항공 운항 데이터 파이프라인부터 AI 모델, LLM 파인튜닝, RAG 통합, API 서빙, 프론트엔드 대시보드까지 엔드투엔드 시스템을 단독으로 설계·구현하였다.

일부 성능 지표(RMSE, IF F1)가 목표에 미달하였으나, 이는 데이터 한계와 모델 특성에 기인하며 개선 방향을 명확히 제시하였다. 특히 QLoRA + DPO를 통한 항공 도메인 LLM 자체 개발, Kafka/Flink 실시간 스트리밍, Next.js 관제 대시보드 구현은 학부 수준에서 차별화된 성과이다.

본 시스템은 파일럿 도입을 통해 실제 공항 환경에서의 효용성을 검증할 수 있으며, 장기적으로 대한민국 항공 관제 안전성 향상에 기여할 수 있을 것으로 기대한다.

---

## 13. 참고문헌

Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L. (2023). QLoRA: Efficient Finetuning of Quantized Language Models. *Advances in Neural Information Processing Systems*, 36.

Rafailov, R., Sharma, A., Mitchell, E., Ermon, S., Manning, C. D., & Finn, C. (2023). Direct Preference Optimization: Your Language Model is Secretly a Reward Model. *Advances in Neural Information Processing Systems*, 36.

Chen, T., & Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System. *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 785-794.

Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). Isolation Forest. *2008 Eighth IEEE International Conference on Data Mining*, 413-422.

Rebollo, J. J., & Balakrishnan, H. (2014). Characterization and Prediction of Air Traffic Delays. *Transportation Research Part C: Emerging Technologies*, 44, 231-241.

Olive, X., & Basora, L. (2019). Identifying Anomalies in Past en-Route Trajectories with Clustering and Outlier Detection Methods. *ATM Seminar*.

Lundberg, S. M., & Lee, S. I. (2017). A Unified Approach to Interpreting Model Predictions. *Advances in Neural Information Processing Systems*, 30.

Kwon, W., Li, Z., Zhuang, S., et al. (2023). Efficient Memory Management for Large Language Model Serving with PagedAttention. *Proceedings of the 29th Symposium on Operating Systems Principles*.

Radford, A., Kim, J. W., Xu, T., et al. (2023). Robust Speech Recognition via Large-Scale Weak Supervision. *Proceedings of the 40th International Conference on Machine Learning*.

Federal Aviation Administration. (2024). Aeronautical Information Manual (AIM). US Department of Transportation.

International Civil Aviation Organization. (2022). Procedures for Air Navigation Services (PANS-ATM, Doc 4444). ICAO.

Akiba, T., Sano, S., Yanase, T., Ohta, T., & Koyama, M. (2019). Optuna: A Next-Generation Hyperparameter Optimization Framework. *Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*.
