<div align="center">

# ✈️ SkyOps Intelligence

**실시간 항공 운항 이상 탐지 및 AI 관제 보조 플랫폼**

*2026학년도 1학기 캡스톤디자인 | DoubleJ팀 | 빅데이터과*

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-1.2-1C3C3C?style=flat-square&logo=langchain&logoColor=white)](https://langchain.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-FF6600?style=flat-square)](https://xgboost.ai)
[![Qwen2.5](https://img.shields.io/badge/LLM-Qwen2.5--7B-7B68EE?style=flat-square)](https://huggingface.co/Qwen)
[![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-FF4B4B?style=flat-square)](https://chromadb.com)
[![Apache Kafka](https://img.shields.io/badge/Streaming-Kafka-231F20?style=flat-square&logo=apachekafka&logoColor=white)](https://kafka.apache.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## 📌 프로젝트 개요

SkyOps Intelligence는 **항공 관제사를 위한 실시간 AI 파트너**입니다.

- 🛫 **15분 선행 지연 예측** — XGBoost + Kafka/Flink 스트리밍 파이프라인
- 🚨 **실시간 이상 탐지** — Isolation Forest + CEP 룰 앙상블
- 🤖 **자연어 원인 설명** — 항공 도메인 특화 LLM (Qwen2.5-7B QLoRA+DPO) + RAG
- 📡 **REST API 서빙** — FastAPI + vLLM + ChromaDB

> *"이상을 탐지하고, 원인을 설명하고, 대응 절차를 5초 이내에 자동 생성합니다."*

---

## 🏗️ 시스템 아키텍처 (5-Layer)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Layer 1 · 데이터 수집                         │
│  OpenSky ADS-B API  ·  METAR/TAF (NOAA)  ·  FAA/ASPM  ·  Kaggle   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  Apache Kafka Topics
┌──────────────────────────▼──────────────────────────────────────────┐
│                      Layer 2 · 스트리밍 처리                          │
│         PyFlink  ·  5분 윈도우 집계  ·  Redis 상태 캐싱               │
│                   CEP 룰 엔진 (이상 패턴 감지)                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  Feature Vector
┌──────────────────────────▼──────────────────────────────────────────┐
│                        Layer 3 · AI 모델                             │
│   XGBoost (지연 예측)   ·   Isolation Forest (이상 탐지)              │
│   Qwen2.5-7B QLoRA+DPO (AviationLLM)   ·   vLLM 서빙               │
│            ChromaDB + LangChain RAG (FAA SOP / NOTAM)               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  FastAPI REST / WebSocket
┌──────────────────────────▼──────────────────────────────────────────┐
│                        Layer 4 · 서빙                                │
│    POST /predict/delay  ·  POST /detect/anomaly  ·  POST /chat       │
│              Prometheus /metrics  ·  Batch /predict/delay/batch      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                       Layer 5 · 대시보드                              │
│   Next.js 관제 대시보드  ·  Kepler.gl H3 혼잡도 히트맵  ·  챗봇 UI    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 실측 성능 지표

| 모델 | 지표 | 목표 | **실측값** |
|------|------|------|-----------|
| XGBoost | RMSE | ≤ 15분 | **24.64분** |
| XGBoost | 분류 정확도 | ≥ 75% | **88.3%** |
| XGBoost | 학습 시간 | — | **10.4초** |
| Isolation Forest | F1 Score | ≥ 0.85 | **0.345** |
| AviationLLM (QLoRA) | Train Loss | — | **0.1053** |
| AviationLLM (QLoRA) | Eval Token Acc | — | **97.88%** |
| AviationLLM (DPO) | Eval Loss | — | **0.02943** |
| AviationLLM (DPO) | Rewards Accuracy | — | **100%** |
| AviationLLM (평가) | ROUGE-L | — | **0.169** |
| AviationLLM (평가) | BLEU-1 | — | **0.121** |

> 데이터셋: 자체 구축 **13,969건** 항공 도메인 데이터 (ATC 교신 + ICAO 문서 + GPT-4 QA 생성)

---

## 🗂️ 디렉토리 구조

```
SkyOps Intelligence/
│
├── 📡 pipeline/                  # Layer 2 · Kafka/Flink 스트리밍
│   ├── opensky_producer.py       # ADS-B 실시간 수집
│   ├── metar_producer.py         # METAR 기상 수집
│   ├── flink_processor.py        # PyFlink 5분 윈도우 집계
│   └── cep_rules.py              # Complex Event Processing 룰
│
├── 🔬 analysis/                  # Phase 1~2 · 모델링
│   ├── download_dataset.py       # Kaggle 데이터 다운로드
│   ├── prepare_dataset.py        # 전처리 및 Feature Engineering
│   ├── feature_engineering.py    # 20개 수치 + 3개 범주 Feature
│   ├── xgboost_model.py          # XGBoost + Optuna 하이퍼파라미터 탐색
│   ├── shap_analysis.py          # SHAP TreeExplainer 해석
│   └── isolation_forest.py       # Isolation Forest 이상 탐지
│
├── 🧠 llm_data/                  # Phase 2 · LLM 데이터 구축
│   ├── download_liveatc.py       # LiveATC 녹취 수집
│   ├── transcribe_whisper.py     # Whisper large-v3 STT
│   ├── clean_atc_text.py         # ATC 약어 복원 정제
│   ├── parse_icao_pdf.py         # ICAO 문서 PDF 파싱
│   ├── generate_qa_gpt4.py       # GPT-4 QA 쌍 자동 생성 (~60K건)
│   ├── generate_anomaly_nl.py    # 이상 탐지 자연어 설명 생성
│   ├── generate_passenger_ann.py # 승객 안내문 생성
│   └── fine_tune_qlora.py        # QLoRA SFTTrainer (9시간 / RTX 3070)
│
├── 🎯 dpo/                       # Phase 2 · 선호도 정렬
│   ├── build_dpo_pairs.py        # chosen/rejected 페어 구성
│   └── train_dpo.py              # DPOTrainer (12시간 / RTX 3070)
│
├── 📈 evaluation/                # Phase 2 · 벤치마크 평가
│   ├── build_benchmark.py        # 벤치마크셋 500건 구성
│   ├── evaluate_model.py         # ROUGE-L / BLEU 평가
│   └── compare_models.py         # Base vs Fine-tuned 비교
│
├── 🔄 airflow/                   # MLOps · 재학습 스케줄링
│   └── dags/                     # 일 1회 재학습 DAG
│
├── 📉 monitoring/                # MLOps · 모니터링
│   ├── drift_detector.py         # EvidentlyAI 드리프트 감지
│   └── slack_notifier.py         # Slack Webhook 알림
│
├── 🚀 serving/                   # Phase 3 · 서빙 (10주차)
│   ├── 01_merge_model.py         # LoRA 어댑터 병합
│   ├── 02_quantize_awq.py        # AWQ 4-bit 양자화
│   ├── 03_run_vllm.sh            # vLLM 서버 실행 (GPU/CPU 모드)
│   ├── 03_test_vllm.py           # vLLM API 동작 테스트
│   ├── 04_build_vectordb.py      # ChromaDB 벡터 DB 구축
│   ├── 05_rag_chain.py           # LangChain RAG 체인
│   ├── api.py                    # FastAPI 메인 애플리케이션
│   └── requirements.txt          # 서빙 의존성
│
├── docker-compose.yml            # Kafka + Zookeeper + Redis
└── README.md                     # 이 파일
```

---

## ⚡ 빠른 시작

### 사전 요구사항

- Python 3.11+
- CUDA 호환 GPU (vLLM 서빙 시 / CPU 모드 가능)
- Docker & Docker Compose (Kafka 스택)

### 1. Kafka 스택 기동

```bash
docker-compose up -d
```

### 2. 서빙 환경 설치

```bash
cd serving
pip install -r requirements.txt
```

### 3. GPU 서빙 (풀 파이프라인)

```bash
# ① LoRA 어댑터 병합
python 01_merge_model.py

# ② AWQ 4-bit 양자화
python 02_quantize_awq.py

# ③ ChromaDB 구축
python 04_build_vectordb.py

# ④ vLLM 서버 기동 (백그라운드)
bash 03_run_vllm.sh awq

# ⑤ vLLM 동작 확인
python 03_test_vllm.py

# ⑥ FastAPI 서버
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 4. CPU 데모 (GPU 없이)

```bash
# ChromaDB 구축 (CPU)
python 04_build_vectordb.py

# FastAPI 서버 바로 실행 (/predict/delay, /detect/anomaly 사용 가능)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔌 API 엔드포인트

서버 기동 후 → **`http://localhost:8000/docs`** (Swagger UI 자동 생성)

### `GET /health`
서버 상태 및 로드된 모델 확인

```bash
curl http://localhost:8000/health
```

### `POST /predict/delay` — 지연 예측

```bash
curl -X POST http://localhost:8000/predict/delay \
  -H "Content-Type: application/json" \
  -d '{
    "dep_hour": 18, "dep_minute": 30, "dep_dayofweek": 4,
    "dep_month": 7, "dep_dayofyear": 195, "is_weekend": 0,
    "distance_miles": 850, "sched_elapsed_min": 120,
    "prev_dep_delay_min": 15, "prev_arr_delay_min": 10, "is_prev_delayed": 1,
    "origin_hourly_departures": 12, "dest_hourly_arrivals": 10,
    "dep_month_weather_score": 0.3,
    "origin_weather_hist_delay": 5.2, "dest_weather_hist_delay": 3.1,
    "carrier_hist_delay": 8.4, "origin_hist_delay": 6.1,
    "dest_hist_delay": 4.9, "route_hist_delay": 7.2,
    "carrier_code": "AA", "origin": "JFK", "dest": "LAX"
  }'
```

**응답:**
```json
{
  "flight_id": null,
  "predicted_delay_minutes": 18.4,
  "is_delayed": true,
  "delay_probability": 0.73,
  "risk_level": "warning",
  "model_version": "xgboost_v1"
}
```

### `POST /detect/anomaly` — 이상 탐지

```bash
curl -X POST http://localhost:8000/detect/anomaly \
  -H "Content-Type: application/json" \
  -d '{
    "dep_hour": 2, "dep_dayofweek": 6, "distance_miles": 4500,
    "sched_elapsed_min": 600, "prev_dep_delay_min": 180,
    "prev_arr_delay_min": 200, "is_prev_delayed": 1,
    "origin_hourly_departures": 1, "dest_hourly_arrivals": 1,
    "dep_month_weather_score": 0.9,
    "origin_weather_hist_delay": 25, "dest_weather_hist_delay": 20,
    "carrier_hist_delay": 30, "origin_hist_delay": 28,
    "dest_hist_delay": 22, "route_hist_delay": 35
  }'
```

**응답:**
```json
{
  "flight_id": null,
  "is_anomaly": true,
  "anomaly_score": -0.31,
  "risk_level": "critical",
  "message": "비정상 운항 패턴 감지됨"
}
```

### `POST /chat` — AI 관제 어시스턴트 (vLLM 필요)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "KE123편 고도 급변 이상 탐지 시 대응 절차를 알려주세요.", "use_rag": true}'
```

### `POST /predict/delay/batch` — 배치 예측 (최대 100건)

```bash
curl -X POST http://localhost:8000/predict/delay/batch \
  -H "Content-Type: application/json" \
  -d '{"flights": [{ ... }, { ... }]}'
```

### `GET /metrics` — Prometheus 메트릭

```bash
curl http://localhost:8000/metrics
```

---

## 🛠️ 기술 스택

| 레이어 | 기술 |
|--------|------|
| **데이터 수집** | OpenSky API, NOAA METAR, FAA ASPM, Kaggle |
| **스트리밍** | Apache Kafka, PyFlink (5분 윈도우), Redis |
| **ML 모델** | XGBoost + Optuna, Isolation Forest, SHAP |
| **LLM** | Qwen2.5-7B-Instruct, QLoRA (TRL SFTTrainer), DPO |
| **LLM 서빙** | vLLM (AWQ 4-bit), OpenAI 호환 API |
| **RAG** | LangChain, ChromaDB, BAAI/bge-m3 임베딩 |
| **API** | FastAPI, Pydantic v2, Uvicorn |
| **MLOps** | MLflow, Airflow, EvidentlyAI, Prometheus + Grafana |
| **인프라** | Docker, GCP Cloud Run, GitHub Actions |
| **대시보드** | Next.js, Kepler.gl, WebSocket |

---

## 📅 개발 일지

| 주차 | 완료 내용 | 핵심 산출물 |
|------|-----------|------------|
| 1주차 | 시스템 설계, Kafka 파이프라인 구성 | `pipeline/` |
| 2주차 | OpenSky ADS-B + METAR 실시간 수집 | `opensky_producer.py` |
| 3주차 | PyFlink 윈도우 집계 + CEP 룰 | `flink_processor.py`, `cep_rules.py` |
| 4주차 | Kaggle 데이터셋 + Feature Engineering (20개) | `prepare_dataset.py` |
| 5주차 | XGBoost + Optuna / MLflow 실험 추적 | RMSE **24.64분** |
| 6주차 | SHAP 해석 + Isolation Forest 이상 탐지 | IF F1 **0.345** |
| 7주차 | ATC 교신 STT + ICAO 파싱 + GPT-4 QA 생성 | 데이터셋 **13,969건** |
| 8주차 | Qwen2.5-7B QLoRA 파인튜닝 (9시간) | Train Loss **0.1053** |
| 9주차 | ROUGE-L 평가 + DPO 정렬 (12시간) + Airflow DAG | ROUGE-L **0.169** |
| 10주차 | vLLM 서빙 + ChromaDB RAG + FastAPI 완성 | `serving/api.py` |

---

## 👥 팀

| 역할 | 이름 |
|------|------|
| 팀장 / 풀스택 | 정재원 |

**지도교수:** 빅데이터과 담당 교수님
**학교:** 캡스톤디자인 2026학년도 1학기

---

## 📄 라이선스

MIT License — 학술 목적 자유 사용 가능. 상업적 이용 시 문의.

---

<div align="center">

**SkyOps Intelligence** · DoubleJ팀 · 2026

*Built with ❤️ for safer skies*

</div>
