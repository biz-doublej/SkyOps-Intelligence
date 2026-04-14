# SkyOps Intelligence — 시스템 전체 성능 벤치마크

> **2026-04-14 업데이트**: `KFold(shuffle=True)` → `TimeSeriesSplit` 전환으로 교차검증이 시간축을 존중하도록 수정.
> 보고되는 CV 숫자가 이전보다 정직하게 반영되도록 개선됨. 자세한 배경: `limitations_and_improvements.md` 및 Strategic Review 1번 병목 참고.

## 1. 지연 예측 모델 (XGBoost)

### 1.1 모델 성능 비교표 (Validation Set)

| 모델 | RMSE (분) | MAE (분) | R² | 지연 정확도 | 학습 시간 |
|------|-----------|----------|-----|-----------|-----------|
| DummyMean (기준선) | 27.13 | 17.52 | -0.104 | 88.8% | 2.1초 |
| LinearRegression | 25.34 | 11.49 | 0.038 | 87.8% | 22.8초 |
| RidgeRegression | 25.33 | 11.49 | 0.038 | 87.9% | 3.8초 |
| RandomForest (depth=10) | 24.69 | 11.29 | 0.086 | 88.2% | 620초 |
| **XGBoost + Optuna (TimeSeriesCV)** | **24.60** | **11.80** | **0.0931** | **88.49%** | **3.9초** |

### 1.2 XGBoost 최종 성능 (데이터셋별)

> CV 방식: **`TimeSeriesSplit(n_splits=5)` walk-forward validation** (2026-04-14 적용).
> 이전 `KFold(shuffle=True)`는 미래 데이터 누수 위험이 있어 교체됨.

| 데이터셋 | RMSE (분) | MAE (분) | R² | 지연 정확도 |
|----------|-----------|----------|-----|-----------|
| Training | 32.68 | 16.34 | 0.2255 | 79.39% |
| Validation | **24.60** | 11.80 | 0.0931 | **88.49%** |
| Test | **36.52** | 15.46 | **0.0996** | 84.16% |
| 5-Fold TimeSeriesCV | **32.66 ± 6.14** | 18.07 ± 4.31 | 0.0947 ± 0.0407 | — |

**핵심 관찰 (TimeSeriesSplit 전환 효과)**:
- CV RMSE 표준편차가 **±0.30 → ±6.14**로 20배 증가. 이전 shuffle 기반 CV가 **숨기고 있던 시간대별 성능 변동성**이 정직하게 드러남.
- Val/Test 절대값은 거의 동일 (`prepare_dataset.py`의 train/val/test 분할이 이미 fl_date 기준 temporal split이었기 때문).
- Val-Test 갭 12분 (24.60 → 36.52)은 시간축 leakage가 아닌 **test 기간의 난이도 차이** 또는 feature 자체 한계에서 기인. 후속 개선 과제 (Rotation/ATFM/NOTAM feature, Conformal Prediction).

### 1.3 Optuna 최적 하이퍼파라미터 (2026-04-14 재탐색)

| 파라미터 | 값 |
|----------|-----|
| n_estimators | 219 |
| max_depth | 7 |
| learning_rate | 0.01374 |
| subsample | 0.7428 |
| colsample_bytree | 0.6358 |
| min_child_weight | 9 |
| reg_alpha | 0.01806 |
| reg_lambda | 0.01865 |

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
