# SkyOps Intelligence — 한계 및 개선 방향 분석

## 1. 지연 예측 모델 한계

### 1.1 RMSE 목표 미달
| 항목 | 목표 | 실측 (Validation) | 차이 |
|------|------|------|------|
| RMSE | 15분 이하 | **24.60분** (2026-04-14 TimeSeriesCV 기준) | +9.60분 |

**원인 분석:**
- Kaggle 데이터셋(13,969건)은 미국 국내선 기준으로, 한국 공항 특성이 반영되지 않음
- 실시간 기상 데이터(METAR)가 직접 Feature로 포함되지 않고 월별 기상 이력으로 간접 반영
- 지연 분포의 극단적 비대칭성 (대부분 0~5분, 소수 60분+)으로 RMSE가 이상치에 민감

**개선 방향:**
1. 한국공항공사 ACDM API 연동으로 국내 공항 실데이터 확보
2. 실시간 METAR/TAF를 Feature로 직접 투입 (풍속, 시정, 운고)
3. 지연 구간별 분류 모델 (0~15분, 15~60분, 60분+) 앙상블 전략
4. LightGBM/CatBoost 추가 비교 실험

### 1.2 과적합 경향
- Train R² (0.2255) vs Test R² (0.0996) 격차가 큼
- Optuna 최적화가 Validation Set에 과적합되었을 가능성

**개선 방향:**
1. Nested Cross-Validation 적용
2. ✅ **시간 기반 분할 (Time Series Split) 도입 완료 (2026-04-14)** — `analysis/xgboost_model.py`의 `run_manual_xgb_cv()` 내부를 `KFold(shuffle=True)` → `TimeSeriesSplit(n_splits=N)`으로 교체. Optuna HPO와 최종 CV 모두 walk-forward validation을 수행하도록 변경. 결과: CV 표준편차가 ±0.30 → ±6.14로 20배 증가하여 이전 shuffle이 숨기고 있던 **시간대별 성능 변동성**이 정직하게 드러남. 자세한 숫자는 `performance_benchmark.md` 1.2절 참고.
3. Feature Selection (Boruta, RFECV) 적용으로 노이즈 Feature 제거
4. **[신규 · 2026-04-14]** Val-Test 갭 12분 잔존 → 시간축 leakage가 아닌 **Rotation/Turnaround/ATFM/NOTAM 등 운항 네트워크 feature 부족**이 주원인으로 추정. Strategic Review 4번 병목 참고. P1 후속 과제.
5. **[신규 · 2026-04-14]** 단일 point estimate 대신 **Conformalized Quantile Regression** 도입으로 prediction interval 제공 검토. Strategic Review 2번 병목 참고. P1 후속 과제.

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

**개선 방향:**
1. 비행 단계(이륙/순항/접근/착륙)별 차등 임계값 적용
2. 공항 반경 30NM 내 이착륙 구간 예외 처리
3. 연속 2회 이상 감지 시에만 알림 발생 (디바운싱)

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
