<div align="center">

# ✈️ SkyOps Intelligence

**실시간 항공 운항 이상 탐지 및 AI 관제 보조 플랫폼**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://python.org)
[![Kafka](https://img.shields.io/badge/Apache_Kafka-7.5.0-231F20?style=flat-square&logo=apachekafka)](https://kafka.apache.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs)](https://nextjs.org)
[![GCP](https://img.shields.io/badge/GCP-Cloud_Run-4285F4?style=flat-square&logo=googlecloud)](https://cloud.google.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

> 2026학년도 1학기 캡스톤디자인 | 빅데이터학과 | 팀 DoubleJ | 정재원

</div>

---

## 📌 프로젝트 개요

**SkyOps Intelligence**는 실시간 항공 운항 데이터(ADS-B, 기상, 게이트 이벤트)를 Kafka/Flink 스트리밍 파이프라인으로 수집·처리하고, XGBoost·Isolation Forest 기반 **지연 예측 및 이상 탐지 AI 모델**과 항공 도메인 특화 **자체 LLM(QLoRA 파인튜닝)** 을 결합하여 관제사·운영자에게 실시간 이상 원인 설명 및 대응 절차를 제공하는 서비스입니다.

### 핵심 기능

- 🔴 **실시간 이상 탐지** — 고도 급변·속도 이상·경로 이탈을 CEP 룰 + Isolation Forest로 탐지
- 📊 **지연 예측** — XGBoost로 15분 선행 지연 예측 (SHAP 해석 포함)
- 🤖 **자체 LLM** — Llama 3.1 8B 기반 QLoRA 파인튜닝으로 항공 도메인 자연어 설명 생성
- 🗺️ **실시간 대시보드** — Next.js + Kepler.gl H3 시공간 지도 관제 화면
- ☁️ **GCP 실서비스** — Cloud Run 배포 + GitHub Actions CI/CD

---

## 🏗️ 시스템 아키텍처 (5-Layer)

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1 — 데이터 수집                                   │
│  OpenSky API · METAR/TAF · FAA ASPM · Kaggle Dataset    │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2 — 스트리밍 파이프라인                           │
│  Apache Kafka (3 topics) → PyFlink (5min window) → Redis │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3 — AI 모델                                       │
│  XGBoost (지연예측) · Isolation Forest (이상탐지)        │
│  QLoRA LLM (Llama 3.1 8B) · RAG (ChromaDB)             │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 4 — MLOps                                         │
│  MLflow · Airflow · EvidentlyAI · Prometheus · Grafana  │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 5 — 서비스 (GCP Cloud Run)                        │
│  FastAPI · Next.js · WebSocket · Docker · GitHub Actions │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ 기술 스택

| 영역 | 기술 |
|---|---|
| 스트리밍 | Apache Kafka 7.5, PyFlink, Redis |
| AI 모델 | XGBoost, Isolation Forest, SHAP |
| 자체 LLM | Llama 3.1 8B, QLoRA (bitsandbytes NF4), vLLM, W&B |
| LLM 정렬 | DPO (TRL DPOTrainer) |
| RAG | LangChain, ChromaDB, Whisper STT |
| 시공간 | Uber H3, GeoPandas, Kepler.gl |
| MLOps | MLflow, Airflow, EvidentlyAI, Prometheus, Grafana |
| 서비스 | FastAPI, Next.js 14, WebSocket |
| 인프라 | Docker Compose, GCP Cloud Run, GitHub Actions |
| 데이터베이스 | PostgreSQL (TimescaleDB), Redis |

---

## 📁 프로젝트 구조

```
SkyOps-Intelligence/
├── database/
│   ├── erd.mermaid          # ERD 다이어그램
│   └── schema.sql           # PostgreSQL DDL
├── pipeline/                # Kafka Producer/Consumer (2주차~)
├── models/                  # AI 모델 코드 (5주차~)
├── llm/                     # QLoRA 파인튜닝 코드 (7주차~)
├── api/                     # FastAPI 서버 (10주차~)
├── dashboard/               # Next.js 프론트엔드 (11주차~)
├── mlops/                   # Airflow DAGs, MLflow (9주차~)
├── docker-compose.yml       # Kafka + Zookeeper 로컬 환경
├── test_opensky_api.py      # OpenSky API 연결 테스트
├── .env.example             # 환경 변수 템플릿
├── .gitignore
└── README.md
```

---

## 🚀 빠른 시작

### 사전 요구사항

- Docker Desktop 4.x 이상
- Python 3.11+
- Git

### 1. 저장소 클론

```bash
git clone https://github.com/biz-doublej/SkyOps-Intelligence.git
cd SkyOps-Intelligence
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 OPENSKY_USERNAME, OPENSKY_PASSWORD 입력
```

### 3. Kafka 클러스터 실행

```bash
docker compose up -d
# Kafka UI: http://localhost:8080
```

### 4. OpenSky API 연결 테스트

```bash
pip install requests python-dotenv
python test_opensky_api.py
```

### 브랜치 전략

```
main   ← 안정 릴리즈 전용 (PR을 통해서만 머지)
 └── dev ← 통합 개발 브랜치
      └── feature/* ← 기능별 작업 브랜치
```

새 기능 작업 시:
```bash
git checkout dev
git checkout -b feature/기능명
# ... 작업 후 dev로 PR
```

---

## 📅 개발 로드맵

| Phase | 기간 | 주요 목표 |
|---|---|---|
| **Phase 1** | 1~4주 | 시스템 설계 · Kafka 파이프라인 · EDA · Feature Engineering |
| **Phase 2** | 5~10주 | XGBoost/IF 모델링 · QLoRA LLM · DPO · MLOps · vLLM 서빙 |
| **Phase 3** | 11~15주 | Next.js 대시보드 · GCP 배포 · CI/CD · 최종발표 |

### Phase 1 진행 현황 (1주차)

- [x] Lean Canvas 초안 작성
- [x] 시스템 아키텍처 다이어그램 (5-Layer)
- [x] Docker Compose로 Kafka + Zookeeper 로컬 클러스터 실행
- [x] OpenSky Network API 키 발급 및 테스트 호출
- [x] GitHub 레포 생성 + 브랜치 전략 정의
- [x] ERD 초안 설계 (항공편·기상·이상이벤트 테이블)
- [x] README 초안 작성

---

## 🗄️ 데이터베이스 ERD

주요 테이블: `airports` · `airlines` · `flights` · `flight_positions` · `weather_observations` · `anomaly_events`

자세한 스키마는 [`database/schema.sql`](database/schema.sql) 및 [`database/erd.mermaid`](database/erd.mermaid) 참조

---

## 🤖 자체 LLM 파인튜닝 전략

| 항목 | 내용 |
|---|---|
| 베이스 모델 | Llama 3.1 8B Instruct |
| 방식 | QLoRA 4-bit NF4 양자화, LoRA rank=64 |
| 학습 데이터 | FAA ATC 교신 Whisper STT + ICAO 문서 GPT-4 QA 생성 (~95K건) |
| 정렬 | DPO (chosen/rejected 안내문 쌍 1K건) |
| 서빙 | vLLM + AWQ 4-bit 추론 (~40 tok/s) |
| 추적 | W&B + MLflow |

---

## 📊 Kafka 토픽 구성

| 토픽 | 설명 | 파티션 |
|---|---|---|
| `flight-position` | OpenSky ADS-B 위치 데이터 (30초 폴링) | 3 |
| `weather-event` | METAR 기상 관측 데이터 | 3 |
| `gate-event` | 게이트 이벤트 (출발·도착 상태) | 3 |

---

## 🌟 기대효과

1. 항공편 지연을 **15분 전 선행 예측**하여 공항 운영 효율 향상
2. 실시간 이상 탐지 + LLM 자연어 설명으로 **관제사 의사결정 지원 시스템(DSS) PoC** 구현
3. 항공 도메인 특화 LLM 자체 개발(QLoRA + DPO)로 **AI 빅데이터 고급 기술 역량** 입증
4. GCP 실서비스 론칭으로 실무 수준의 **MLOps·클라우드 배포 경험** 확보

---

## 👤 팀 정보

| 항목 | 내용 |
|---|---|
| 팀명 | DoubleJ |
| 팀장 | 정재원 |
| 학과 | 빅데이터학과 3학년 |
| 지도교수 | 조상구 교수님 |

---

<div align="center">
  <sub>2026학년도 1학기 캡스톤디자인 — SkyOps Intelligence</sub>
</div>
