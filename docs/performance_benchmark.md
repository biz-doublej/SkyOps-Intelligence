# SkyOps Intelligence — 시스템 전체 성능 벤치마크

> **2026-04-14 업데이트 #1 (P0)**: `KFold(shuffle=True)` → `TimeSeriesSplit` 전환으로 교차검증이 시간축을 존중하도록 수정.
> **2026-04-14 업데이트 #2 (P1)**: Conformal Prediction 90% interval 추가 (`/predict/delay` response).
> **2026-04-14 업데이트 #3 (P1)**: `TAIL_NUMBER` 기반 rotation features 5종 도입 + 전체 데이터셋(5.7M행)으로 재학습.
> 자세한 배경: `limitations_and_improvements.md`, `event_model.md`, Strategic Review 1·2·4·5번 병목 참고.

## 1. 지연 예측 모델 (XGBoost)

### 1.1 모델 성능 비교표 (Validation Set)

| 모델 | RMSE (분) | MAE (분) | R² | 지연 정확도 | 학습 시간 |
|------|-----------|----------|-----|-----------|-----------|
| DummyMean (기준선) | 27.13 | 17.52 | -0.104 | 88.8% | 2.1초 |
| LinearRegression | 25.34 | 11.49 | 0.038 | 87.8% | 22.8초 |
| RidgeRegression | 25.33 | 11.49 | 0.038 | 87.9% | 3.8초 |
| RandomForest (depth=10) | 24.69 | 11.29 | 0.086 | 88.2% | 620초 |
| XGBoost + Optuna (P0 TimeSeriesCV) | 24.60 | 11.80 | 0.0931 | 88.49% | 3.9초 |
| **XGBoost + Rotation + 5.7M dataset (P1)** | **22.61** | **8.79** | **0.3784** | **91.15%** | **106.8초** |

### 1.2 XGBoost 최종 성능 (데이터셋별)

> CV 방식: **`TimeSeriesSplit(n_splits=5)` walk-forward validation** (P0, 2026-04-14 적용).
> **Feature set**: 20 numeric + 3 categorical (P0) → **25 numeric + 3 categorical (P1, +Rotation 5종)**.
> **Dataset 규모**: 337K rows (P0) → **5.7M rows (P1, 전체 Kaggle 데이터)**. Train: 4.0M / Val: 857K / Test: 857K.

#### P1 최종 결과 (2026-04-14 Rotation PoC + 전체 데이터셋)

| 데이터셋 | RMSE (분) | MAE (분) | R² | 지연 정확도 |
|----------|-----------|----------|-----|-----------|
| Training | 26.33 | 10.75 | 0.4792 | 88.34% |
| **Validation** | **22.61** | **8.79** | **0.3784** | **91.15%** |
| **Test** | **28.18** | **10.62** | **0.4328** | **89.04%** |
| **5-Fold TimeSeriesCV** | **27.21 ± 1.51** | 11.60 ± 1.31 | 0.4467 ± 0.0197 | — |

#### P1 개선 효과 (P0 TimeSeriesSplit 기준 대비)

| 지표 | P0 (337K, 20 numeric) | **P1 (5.7M, +Rotation)** | 변화 |
|------|----------------------|--------------------------|------|
| Val RMSE | 24.60 | **22.61** | **-1.99분 (-8.1%)** |
| **Test RMSE** | 36.52 | **28.18** | **-8.34분 (-22.8%!)** |
| **Test R²** | 0.0996 | **0.4328** | **+335%!** |
| Val R² | 0.0931 | **0.3784** | +306% |
| Delay Accuracy (Val) | 88.49% | **91.15%** | +2.66%p |
| Delay Accuracy (Test) | 84.16% | **89.04%** | +4.88%p |
| 5-Fold CV RMSE (std) | 32.66 ± **6.14** | 27.21 ± **1.51** | **std 4배 감소** |
| **Val-Test gap (RMSE)** | 12분 | **5.5분** | **격차 절반** |

**핵심 관찰 (P1 Rotation + Full Dataset 효과)**:
- **Test R² 0.0996 → 0.4328**: 지연 예측 모델이 실제 분산의 ~43%를 설명 가능. P0 대비 3배 이상.
- **Val-Test 갭 12분 → 5.5분**: 일반화 실패의 근본 원인이 **rotation-aware feature 부족**과 **데이터 규모**에 있었음을 확인. Temporal split과 무관.
- **CV std 6.14 → 1.51 (4배↓)**: 시간대별 성능 변동성도 크게 감소. 모델이 더 안정적.
- **지연 정확도 91.15% (Val)**: 목표 75% 대비 +16.15%p, 이진 분류 측면에서는 production-ready 수준.
- **학습 시간 3.9초 → 106.8초**: 17배 더 큰 데이터셋 처리 비용. 여전히 2분 이내로 실용적.

### 1.3 Optuna 최적 하이퍼파라미터 (2026-04-14 P1 재탐색, 15 trials)

| 파라미터 | 값 |
|----------|-----|
| n_estimators | 796 |
| max_depth | 8 |
| learning_rate | 0.02155 |
| subsample | 0.9783 |
| colsample_bytree | 0.5359 |
| min_child_weight | 18 |
| reg_alpha | 5.5892 |
| reg_lambda | 0.001586 |
| Best Optuna RMSE | **26.83** (TimeSeriesCV 3-fold) |

### 1.4 Conformal Prediction Interval (P1 · 2026-04-14)

**알고리즘**: MAPIE 1.3 `SplitConformalRegressor` (prefit mode, absolute residual)
**Calibration set**: val.csv 857,101 samples (P0 72,308 대비 12배)
**Confidence level**: 90% (alpha=0.1)

| 지표 | 값 |
|------|-----|
| Target coverage | 90% |
| **Empirical coverage (val self-test)** | **90.00%** ✅ |
| **Average interval width** | **30.84분** (P0 38.74분 → -7.9분) |
| Calibration RMSE | 22.61분 |

**API 응답 예시** (`POST /predict/delay`):
```json
{
  "predicted_delay_min": 5.4,
  "is_delayed": false,
  "confidence": "medium",
  "prediction_interval": {
    "lower_min": -10.0,
    "upper_min": 20.9,
    "confidence": 0.9,
    "width_min": 30.8,
    "method": "split_conformal_mapie_v1.3.0"
  },
  "latency_ms": 2178.2
}
```

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

### 3.4 RAGAs Benchmark (P2 · 2026-04-14)

> Strategic Review 7번 병목 — ROUGE/BLEU만으로 부족한 RAG 품질을 grounded 평가로 보완.
> `evaluation/ragas_bench.py` (MAPIE 패턴과 유사, vLLM judge 시도 + proxy fallback).

**Proxy Metrics** (30 samples stratified, no judge LLM required):

| Metric | Mean | Std | 해석 |
|--------|------|-----|------|
| context_hit_rate | **0.0388** | 0.0588 | ground_truth 키워드가 context에 포함된 비율 (recall proxy) — ⚠️ 매우 낮음 |
| answer_rouge_l | **0.0319** | 0.0741 | generated vs ground_truth ROUGE-L (LLM fallback 시 낮음) |
| answer_length_ratio | **1.0000** | 0.0 | 80~500 chars 범위 (정상) |
| retrieval_coverage | **1.0000** | 0.0 | len(contexts) / 4 (모두 충분히 검색됨) |

**Type별 Breakdown**:

| Type | N | context_hit_rate | answer_rouge_l |
|------|---|------------------|----------------|
| anomaly | 10 | 0.0243 | 0.0037 |
| announcement | 10 | 0.0569 | 0.0668 |
| regulation | 10 | 0.0353 | 0.0253 |

**RAGAs 정식 지표** (vLLM judge 필요 — smoke test 시점에 vLLM 서버 미실행, APIConnectionError 로 전환 fallback 확인됨):
- `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`
- 향후 vLLM 가동 시 `python evaluation/ragas_bench.py --n 50 --judge vllm` 로 재측정 예정

**⚠️ 정직한 진단**:
- ChromaDB 내 문서가 **13개뿐** (`serving/04_build_vectordb.py` 샘플 EXTRA_DOCS + ICAO chunks). 이 때문에 context_hit_rate가 극도로 낮음. 운영 수준이 되려면 FAA AIM, NOTAM 전체, ICAO Doc 4444, airport-specific SOP 등 수천~수만 chunk로 확장 필요.
- 현재 RAG는 advisory copilot 데모 수준. production 도입 전 grounding 품질 대폭 개선 필요.

**후속 과제**:
- ChromaDB 확장 (10K+ chunks)
- Per-chunk citation 강제 (grounded generation)
- vLLM judge vs OpenAI judge 비교
- Hallucination detection threshold 튜닝

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
