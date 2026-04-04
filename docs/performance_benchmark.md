# SkyOps Intelligence — 시스템 전체 성능 벤치마크

## 1. 지연 예측 모델 (XGBoost)

### 1.1 모델 성능 비교표 (Validation Set)

| 모델 | RMSE (분) | MAE (분) | R² | 지연 정확도 | 학습 시간 |
|------|-----------|----------|-----|-----------|-----------|
| DummyMean (기준선) | 27.13 | 17.52 | -0.104 | 88.8% | 2.1초 |
| LinearRegression | 25.34 | 11.49 | 0.038 | 87.8% | 22.8초 |
| RidgeRegression | 25.33 | 11.49 | 0.038 | 87.9% | 3.8초 |
| RandomForest (depth=10) | 24.69 | 11.29 | 0.086 | 88.2% | 620초 |
| **XGBoost + Optuna** | **24.64** | **11.50** | **0.090** | **88.3%** | **10.4초** |

### 1.2 XGBoost 최종 성능 (데이터셋별)

| 데이터셋 | RMSE (분) | MAE (분) | R² | 지연 정확도 |
|----------|-----------|----------|-----|-----------|
| Training | 31.30 | 15.49 | 0.290 | 81.0% |
| Validation | 24.64 | 11.50 | 0.090 | 88.3% |
| Test | 36.59 | 15.30 | 0.096 | 83.9% |
| 5-Fold CV | 32.18 ± 0.30 | 15.56 ± 0.05 | 0.249 ± 0.009 | — |

### 1.3 Optuna 최적 하이퍼파라미터

| 파라미터 | 값 |
|----------|-----|
| n_estimators | 500 |
| max_depth | 7 |
| learning_rate | 0.05 |
| subsample | 0.8 |
| colsample_bytree | 0.8 |
| min_child_weight | 5 |
| reg_alpha | 0.1 |
| reg_lambda | 1.0 |

### 1.4 모델 파일 크기

| 모델 | 크기 |
|------|------|
| xgboost_best.pkl | 6.9 MB |
| isolation_forest.pkl | 2.1 MB |
| baseline_randomforest.pkl | 5.2 MB |

---

## 2. 이상 탐지 모델 (Isolation Forest)

### 2.1 최적 임계값 성능 (15th percentile)

| 지표 | 값 |
|------|-----|
| Precision | 0.359 |
| Recall | 0.314 |
| F1 Score | 0.335 |
| Contamination | 0.05 (5%) |
| n_estimators | 200 |
| Threshold | -0.517 |

### 2.2 CEP 룰 엔진 이상 탐지 기준

| 룰 | 기준값 | 설명 |
|----|--------|------|
| ALTITUDE_SPIKE | 152m/30초 (500ft/30s) | 고도 급변 감지 |
| VELOCITY_SPIKE | 50m/s/30초 | 속도 이상 감지 |
| PATH_DEVIATION | 5km 이상 | 경로 이탈 감지 |

### 2.3 심각도 분류 기준

| 심각도 | 기준 |
|--------|------|
| LOW | 기준치 1.0~1.5배 초과 |
| MEDIUM | 기준치 1.5~2.0배 초과 |
| HIGH | 기준치 2.0배 이상 초과 |

---

## 3. LLM 파인튜닝 (AviationLLM)

### 3.1 QLoRA SFT 학습 결과

| 항목 | 값 |
|------|-----|
| 베이스 모델 | Qwen/Qwen2.5-7B-Instruct |
| GPU | RTX 3070 8GB |
| 양자화 | 4-bit NF4 (bitsandbytes) |
| LoRA rank | 64 |
| LoRA alpha | 16 |
| 학습 데이터 | 12,750건 (학습) / 1,500건 (검증) |
| Total Steps | 1,594 (2 epochs) |
| **Train Loss** | **0.1053** |
| **Eval Loss** | **0.0445** |
| **Eval Token Accuracy** | **97.88%** |
| Train Runtime | 32,389초 (약 9시간) |
| Samples/sec | 0.787 |
| 학습 파라미터 | 40,370,176 (전체의 0.92%) |
| Adapter 크기 | 155 MB |

### 3.2 DPO 선호도 정렬 결과

| 항목 | 값 |
|------|-----|
| DPO beta | 0.1 |
| Total Steps | 119 (1 epoch) |
| **Train Loss** | **0.101** |
| **Eval Loss** | **0.02943** |
| **Rewards/Accuracies** | **1.0 (100%)** |
| **Rewards/Margins** | **0.80 → 8.91** |
| Mean Token Accuracy | 0.9166 |
| Train Runtime | 43,420초 (약 12시간) |

### 3.3 도메인 벤치마크 평가 (500건)

| 유형 | n | ROUGE-L | BLEU-1 | BLEU-2 | BLEU-4 |
|------|---|---------|--------|--------|--------|
| **전체** | 500 | **0.169** | **0.121** | 0.083 | 0.062 |
| 이상 탐지 설명 | 331 | 0.159 | 0.111 | — | — |
| 승객 안내문 | 125 | **0.225** | **0.170** | — | — |
| 규정 QA | 44 | 0.090 | 0.064 | — | — |

### 3.4 AWQ 양자화 + vLLM 서빙

| 항목 | 값 |
|------|-----|
| 양자화 방식 | AWQ 4-bit (autoawq) |
| 양자화 시간 | 47분 (RTX 3070) |
| vLLM 커널 | awq_marlin |
| GPU 메모리 사용 | 5.2 GiB / 8.0 GiB |
| Max Model Length | 2,048 토큰 |
| KV Cache | 3,680 토큰 |
| 최대 동시 요청 | 1.80x |
| Avg Prompt Throughput | 4~6 tok/s |
| Avg Generation Throughput | 5~13 tok/s |

---

## 4. API 응답 성능

### 4.1 엔드포인트별 응답 시간

| 엔드포인트 | 평균 응답 시간 | 비고 |
|-----------|-------------|------|
| POST /predict/delay | ~11ms | XGBoost 단일 예측 |
| POST /detect/anomaly | ~15ms | Isolation Forest |
| POST /chat (RAG) | ~24,000ms | 임베딩 검색 + vLLM 생성 |
| POST /chat (직접) | ~960ms | vLLM 직접 호출 |
| POST /explain/anomaly | ~3,000~5,000ms | vLLM 이상 설명 생성 |
| POST /generate/announcement | ~3,000~5,000ms | vLLM 안내문 생성 |
| GET /aircraft/live | ~5ms | Redis 조회 |
| GET /aircraft/h3 | ~10ms | Redis + H3 집계 |
| WS /ws/aircraft | 3초 간격 push | WebSocket |

### 4.2 시스템 리소스

| 항목 | 값 |
|------|-----|
| GPU | NVIDIA RTX 3070 8GB |
| vLLM VRAM 사용 | 5.2 GiB |
| Redis 메모리 | 512 MB (LRU) |
| Kafka 파티션 | 3 × 3 토픽 |
| 항공기 추적 용량 | 최대 200대 동시 |
| 이상 이벤트 버퍼 | 최근 1,000건 |

---

## 5. 데이터셋 규모

| 데이터 | 규모 |
|--------|------|
| Kaggle Flight Delay | 13,969건 |
| OpenSky 실시간 수집 | 60~80대/30초 (한국 영공) |
| ATC 교신 STT (Whisper) | 10시간 녹취 |
| GPT-4 QA 자동 생성 | ~60,000건 |
| 이상 탐지 자연어 설명 | ~10,000건 |
| 승객 안내문 한/영 | ~5,000건 |
| DPO 선호 페어 | 13,969건 |
| ChromaDB 임베딩 문서 | FAA SOP + NOTAM |
| 벤치마크 평가셋 | 500건 |
