# SkyOps Intelligence — 한계 및 개선 방향 분석

## 1. 지연 예측 모델 한계

### 1.1 RMSE 목표 미달
| 항목 | 목표 | 실측 (Validation) | 차이 |
|------|------|------|------|
| RMSE (P0) | 15분 이하 | 24.60분 (2026-04-14 TimeSeriesCV 기준) | +9.60분 |
| **RMSE (P1)** | 15분 이하 | **22.61분** (2026-04-14 +Rotation +Full dataset) | **+7.61분** (-1.99분 개선) |

**원인 분석:**
- Kaggle 데이터셋(13,969건)은 미국 국내선 기준으로, 한국 공항 특성이 반영되지 않음
- 실시간 기상 데이터(METAR)가 직접 Feature로 포함되지 않고 월별 기상 이력으로 간접 반영
- 지연 분포의 극단적 비대칭성 (대부분 0~5분, 소수 60분+)으로 RMSE가 이상치에 민감

**개선 방향:**
1. 한국공항공사 ACDM API 연동으로 국내 공항 실데이터 확보
2. 실시간 METAR/TAF를 Feature로 직접 투입 (풍속, 시정, 운고)
3. 지연 구간별 분류 모델 (0~15분, 15~60분, 60분+) 앙상블 전략
4. LightGBM/CatBoost 추가 비교 실험

### 1.2 과적합 경향 (P0 시점)
- Train R² (0.2255) vs Test R² (0.0996) 격차가 큼
- Optuna 최적화가 Validation Set에 과적합되었을 가능성

### 1.2b P1 이후 (2026-04-14 Rotation + Full Dataset)
- ✅ **Test R² 0.0996 → 0.4328** (+335% 향상) — rotation features + 5.7M 데이터로 일반화 성능 크게 개선
- ✅ **Val-Test gap 12분 → 5.5분** — 과적합/일반화 문제가 근본적으로 완화
- ✅ **CV std 6.14 → 1.51** — 시간대별 변동성도 안정화

**개선 방향:**
1. Nested Cross-Validation 적용
2. ✅ **시간 기반 분할 (Time Series Split) 도입 완료 (2026-04-14)** — `analysis/xgboost_model.py`의 `run_manual_xgb_cv()` 내부를 `KFold(shuffle=True)` → `TimeSeriesSplit(n_splits=N)`으로 교체. Optuna HPO와 최종 CV 모두 walk-forward validation을 수행하도록 변경. 결과: CV 표준편차가 ±0.30 → ±6.14로 20배 증가하여 이전 shuffle이 숨기고 있던 **시간대별 성능 변동성**이 정직하게 드러남. 자세한 숫자는 `performance_benchmark.md` 1.2절 참고.
3. Feature Selection (Boruta, RFECV) 적용으로 노이즈 Feature 제거
4. ✅ **[2026-04-14 P1 완료]** Rotation feature 5종 도입 — `tail_number` 기반 `rotation_depth`, `prev_leg_arr_delay_min`, `scheduled_turnaround_min`, `actual_turnaround_min`, `is_first_leg_of_day`. 전체 데이터셋(5.7M행)으로 재학습하여 Best Optuna RMSE 31.80 → ~27.72분 개선 (약 4분 감소). Strategic Review 4번 병목 부분 해소. 후속: ATFM/NOTAM 연동 (P2~P3).
5. ✅ **[2026-04-14 P1 완료]** Conformal Prediction 도입 — MAPIE 1.3 `SplitConformalRegressor`(prefit, absolute residual) 기반 90% prediction interval. `analysis/conformal_calibration.py` 스크립트, `data/models/conformal_calibrator.pkl` 아티팩트, `serving/api.py`의 `/predict/delay` 응답에 `prediction_interval: {lower_min, upper_min, confidence, width_min, method}` 반환. Val set 72,308건에서 empirical coverage **90.00%** (목표 90%), avg interval width 38.74분. Strategic Review 2번 병목 해소. 후속: Conformalized Quantile Regression (비대칭 interval) (P2).

---

## 2. 이상 탐지 모델 한계

### 2.1 F1 Score 극도로 낮음
| 항목 | 목표 | 실측 | 차이 |
|------|------|------|------|
| F1 Score | 0.85 이상 | 0.335 | -0.515 |

**원인 분석:**
- Isolation Forest는 비지도 학습이므로 레이블 없이 이상치를 탐지하나, 평가 시 사용한 레이블의 품질이 불확실
- Contamination 5% 설정이 실제 이상 비율과 불일치할 수 있음
- 배치 데이터(Kaggle) 기반 학습이라 실시간 ADS-B 패턴과 분포 차이 존재

**개선 방향:**
1. CEP 룰 엔진 결과를 pseudo-label로 활용한 반지도 학습
2. Autoencoder 기반 이상 탐지로 모델 변경 (재구성 오차 기반)
3. 실시간 ADS-B 데이터로 온라인 학습 (Incremental Learning)
4. 도메인 전문가 라벨링 + 능동 학습 (Active Learning) 적용

### 2.2 CEP 룰 과민감도
- 실시간 테스트에서 이상 탐지 알림이 과다 발생 (대부분 LOW)
- 이착륙 구간의 정상적 고도 변화를 이상으로 오탐지

**개선 방향 (2026-04-14 진행 상황):**
- ✅ **P3 ADR-001 Migration Phase 1 완료 (2026-04-14)** — `serving/api.py` 1120→107라인, `serving/common/` + `serving/routers/` 구조
- ✅ **P3 OpenTelemetry 계측 완료 (2026-04-14)** — FastAPIInstrumentor + LoggingInstrumentor + Console/OTLP exporter, custom spans per router
- ✅ **P3 Dashboard README 재작성 완료 (2026-04-14)** — Prototype smell 제거, Next.js 16 특화 내용
- ✅ **P3 Active Learning 스크립트 완료 (2026-04-14)** — `analysis/active_learning.py`로 feedback.jsonl 자동 분석 + 권고 생성

**잔여 개선 과제 (P5+ 이연):**

### P4+ 완료 (2026-04-15)
- ✅ **ADR-001 Phase 2**: `pyproject.toml` + editable install (`pip install -e .`), 8개 entry points
- ✅ **ADR-002**: API Gateway 선택 MADR (Traefik v3, 6 microservices routing)
- ✅ **ChromaDB expansion**: 13 → 95 chunks (폴더 기반 loader, FAA AIM/ICAO Annex/NOTAM samples/SOP)
- ✅ **Conformalized Quantile Regression**: `analysis/quantile_regression.py` + `conformal_calibration.py --mode cqr`, asymmetric intervals
- ✅ **Containerization**: Dockerfile.api/dashboard, docker-compose.prod.yml, k8s/ 7 manifests, GitHub Actions CI
- ✅ **Active Learning query**: `/active-learning/next` endpoint + `analysis/active_learning.py next-batch` CLI
- ✅ **ATFM/NOTAM mock producers**: schema v2.0, event_model.md 2.5/2.6 준수, docker-compose.yml topic 추가

### P5+ 완료 (2026-04-15)
- ✅ **FAA SWIM 실연동**: `pipeline/swim_subscriber.py` (Solace SMF + TLS c_rehash trust store), `pipeline/notam_producer.py NOTAM_MODE=swim` 디스패치, AIXM 5.1 + FAA `event:` 네임스페이스 파서. **60초간 219건 실 NOTAM 수신 검증 완료**.
- ✅ **ML phase classifier**: `analysis/ml_phase_classifier.py` — XGBClassifier + silver-label (Kaggle features → 7 phase samples per row). 휴리스틱 대비 90.3% agreement. 이전 heuristic의 cliff edge 분류 문제 해소.
- ✅ **Per-phase Isolation Forest**: `analysis/per_phase_isolation_forest.py` — 7개 IF 모델, phase별 contamination 튜닝 (TAXI 0.02 / APPROACH·LANDING 0.06). serving이 phase 분류 후 해당 IF 호출.
- ✅ **OTel + Jaeger 로컬 검증**: `monitoring/otel-collector-config.yaml`, `docker-compose.prod.yml --profile observability`. `serving/api.py` → OTLP gRPC → Collector → Jaeger UI 전 구간 동작 확인 (`skyops-api` 서비스 등록, 3 traces × 3 spans 수집).
- ✅ **Docker Desktop k8s 검증**: `k8s/local/redis-only.yaml` — namespace + ConfigMap + Redis + Service + smoke pod. Pod → Service → Pod DNS 해결 (`redis-cli -h redis ping → PONG`) 확인.
- ✅ **Reproduction guide**: `docs/reproduction_guide.md` 419 라인 — `git clone` → FAA SWIM live까지 단일 문서. SWIM trust store 셋업 스크립트 + Mermaid 아키텍처 다이어그램 + sprint commit 히스토리 + 트러블슈팅 7종 포함.

### P5+ 이연 → P6 후보 과제

1. ✅ **비행 단계(이륙/순항/접근/착륙)별 차등 임계값 적용 — 2026-04-14 P2 완료**
   - `pipeline/phase_classifier.py` heuristic FlightPhase classifier (7 phases + UNKNOWN)
   - `pipeline/cep_rules.py` PHASE_ALTITUDE/VELOCITY/PATH_MULTIPLIER 적용
   - TAXI는 ALTITUDE/PATH rule 비활성, TAKEOFF/LANDING은 3배 관대, APPROACH는 0.5배 엄격
2. 공항 반경 30NM 내 이착륙 구간 예외 처리 (P3 후보 — Haversine + airport DB 필요)
3. ✅ **연속 2회 이상 감지 시에만 알림 발생 (디바운싱) — 2026-04-14 P2 완료**
   - Redis TTL 60초 key `skyops:anomaly:debounce:{icao24}:{type}`
   - severity=HIGH 은 debounce 면제 (critical 알림 손실 방지)
   - LOW/MEDIUM 은 60초 내 재발생 suppress
4. ✅ **Analyst feedback loop (stub) — 2026-04-14 P2 완료**
   - `POST /anomaly/feedback` 엔드포인트 → `data/analyst_feedback/feedback.jsonl` append
   - 향후 active learning 입력으로 사용

---

## 3. LLM 한계

### 3.1 한국어 품질 문제
- Qwen2.5는 중국어 기반 모델로, 긴 생성 시 중국어로 코드스위칭 발생
- 후처리 필터(`_clean_korean`)로 완화하였으나 근본적 해결은 아님

**개선 방향:**
1. 한국어 특화 모델로 변경 (예: SOLAR, KULLM, Polyglot-Ko)
2. 한국어 코퍼스 비율을 80% 이상으로 학습 데이터 재구성
3. 한국어 SFT 데이터 추가 수집 (항공 관제 한국어 교범, 교통관제 매뉴얼)

### 3.2 추론 속도 제한
- RTX 3070 8GB에서 AWQ 4-bit로도 평균 5~13 tok/s (목표 30 tok/s 이상)
- RAG 포함 시 24초로 실시간 대응에 부적합

**개선 방향:**
1. RTX 4090 또는 A100 GPU로 업그레이드
2. Speculative Decoding 적용 (vLLM 지원)
3. KV Cache 최적화 및 모델 길이 축소 (1024 토큰)
4. 임베딩 모델 경량화 (bge-m3 → bge-small)

### 3.3 벤치마크 점수 해석 주의
- ROUGE-L 0.169, BLEU-1 0.121은 생성형 LLM 특성상 절대적으로 낮게 측정됨
- 동일 의미를 다른 어휘로 표현해도 낮은 점수가 나오는 n-gram 매칭의 한계

**개선 방향:**
1. BERTScore 도입 (의미 유사도 기반 평가)
2. LLM-as-Judge 평가 (GPT-4로 품질 평가)
3. 도메인 전문가 인간 평가 (정확성, 유용성, 안전성 3축)

---

## 4. 시스템 아키텍처 한계

### 4.1 단일 인스턴스 한계
- Kafka 브로커 1대, Redis 단일 노드, GPU 1장
- 대규모 트래픽 처리 불가

**개선 방향:**
1. Kafka 클러스터 확장 (브로커 3대, 레플리카 3)
2. Redis Cluster 또는 Redis Sentinel 구성
3. vLLM 다중 GPU 분산 (Tensor Parallelism)

### 4.2 테스트 부재
- 자동화 테스트(pytest) 미구현
- CI/CD 파이프라인 미구축

**개선 방향:**
1. pytest 단위 테스트 + 통합 테스트 추가
2. GitHub Actions CI/CD 파이프라인 구성
3. API 부하 테스트 (Locust, k6)

### 4.3 보안/인증 미구현
- API 인증 없이 공개 접근 가능
- Rate Limiting 미적용

**개선 방향:**
1. JWT 기반 API 인증
2. Rate Limiting (slowapi 또는 nginx)
3. HTTPS 적용 (Let's Encrypt)

---

## 5. 종합 한계 요약

| 영역 | 한계 | 심각도 | 개선 난이도 |
|------|------|--------|-----------|
| 지연 예측 RMSE | 목표 대비 +9.64분 | 중 | 중 (데이터 확보 필요) |
| IF F1 Score | 목표 대비 -0.515 | 높음 | 높음 (모델 변경 필요) |
| LLM 한국어 | 중국어 코드스위칭 | 중 | 높음 (모델 변경 필요) |
| LLM 속도 | 5~13 tok/s | 중 | 중 (GPU 업그레이드) |
| 테스트 부재 | 자동화 테스트 없음 | 중 | 낮음 |
| 단일 인스턴스 | 확장성 제한 | 낮음 | 중 |
