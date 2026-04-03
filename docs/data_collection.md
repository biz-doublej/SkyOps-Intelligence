# 📦 SkyOps Intelligence — 데이터 수집 명세서

> **최종 업데이트**: 2026-04-03 (10주차 기준)

---

## 목차

1. [전체 데이터 파이프라인 개요](#1-전체-데이터-파이프라인-개요)
2. [실시간 스트리밍 데이터](#2-실시간-스트리밍-데이터)
   - 2.1 OpenSky ADS-B — 항공기 위치
   - 2.2 NOAA METAR — 공항 기상
3. [정적 / 배치 데이터](#3-정적--배치-데이터)
   - 3.1 Kaggle Flight Delay Dataset
   - 3.2 FAA / ASPM 운항 통계
4. [LLM 학습용 데이터](#4-llm-학습용-데이터)
   - 4.1 LiveATC 교신 음성 수집
   - 4.2 Whisper STT 변환
   - 4.3 ATC 텍스트 정제
   - 4.4 ICAO / FAA 문서 PDF 파싱
   - 4.5 GPT-4 API QA 쌍 생성
   - 4.6 이상 탐지 자연어 설명 생성
   - 4.7 승객 안내문 생성
5. [최종 데이터셋 구성](#5-최종-데이터셋-구성)
6. [데이터 디렉토리 구조](#6-데이터-디렉토리-구조)
7. [환경 변수 및 인증](#7-환경-변수-및-인증)

---

## 1. 전체 데이터 파이프라인 개요

```
┌─────────────────────────────────────────────────────────┐
│                   외부 데이터 소스                        │
│  OpenSky API │ NOAA METAR │ Kaggle │ LiveATC │ ICAO PDF  │
└────────┬─────────┬──────────┬────────┬─────────┬─────────┘
         │         │          │        │         │
    [30초 폴링] [30분 폴링] [1회 다운] [mp3 수집] [PDF 파싱]
         │         │          │        │         │
         ▼         ▼          ▼        ▼         ▼
    Kafka:        Kafka:    flights. Whisper   chunks.
 flight-position weather-   csv(배치)  STT     jsonl
                  event
         │         │          │        │         │
         └────┬────┘          │        └────┬────┘
              ▼               ▼             ▼
         PyFlink          Feature      GPT-4 QA
        5분 집계         Engineering    생성
              │               │             │
              └───────────────┴─────────────┘
                              ▼
                     Alpaca 포맷 통합
                     (aviation_alpaca.jsonl)
```

---

## 2. 실시간 스트리밍 데이터

### 2.1 OpenSky ADS-B — 항공기 위치

| 항목 | 내용 |
|------|------|
| **소스** | [OpenSky Network](https://opensky-network.org) REST API |
| **엔드포인트** | `GET /api/states/all?lamin=33.0&lomin=124.0&lamax=38.9&lomax=130.0` |
| **수집 스크립트** | `pipeline/opensky_producer.py` |
| **수집 주기** | 30초 폴링 |
| **Kafka 토픽** | `flight-position` |
| **커버리지** | 한반도 바운딩 박스 (위도 33.0~38.9 / 경도 124.0~130.0) |
| **인증** | OpenSky 계정 (무료 / 익명 접근 가능, 제한 있음) |

**수집 필드 (OpenSky `states/all` 응답 순서 기준):**

| 인덱스 | 필드명 | 설명 | 단위 |
|--------|--------|------|------|
| 0 | `icao24` | 항공기 ICAO 24비트 주소 | hex |
| 1 | `callsign` | 콜사인 | — |
| 2 | `origin_country` | 등록 국가 | — |
| 3 | `time_position` | 마지막 위치 시간 | Unix UTC |
| 4 | `last_contact` | 마지막 통신 시간 | Unix UTC |
| 5 | `longitude` | 경도 | deg |
| 6 | `latitude` | 위도 | deg |
| 7 | `baro_altitude` | 기압 고도 | m |
| 8 | `on_ground` | 지상 여부 | bool |
| 9 | `velocity` | 대지 속도 | m/s |
| 10 | `true_track` | 진행 방향 | deg |
| 11 | `vertical_rate` | 수직 속도 | m/s |
| 12 | `sensors` | 수신 센서 ID | list |
| 13 | `geo_altitude` | GPS 고도 | m |
| 14 | `squawk` | Squawk 코드 | — |
| 15 | `spi` | 특수 목적 식별자 | bool |
| 16 | `position_source` | 위치 소스 (0=ADS-B) | int |

**Kafka 메시지 스키마 (JSON):**

```json
{
  "icao24": "aa1234",
  "callsign": "KAL123",
  "latitude": 37.46,
  "longitude": 126.44,
  "baro_altitude": 10668.0,
  "velocity": 245.3,
  "vertical_rate": -2.6,
  "on_ground": false,
  "squawk": "2134",
  "collected_at": "2026-04-03T09:00:00Z",
  "source": "opensky"
}
```

**실행:**
```bash
# .env 설정 후
python pipeline/opensky_producer.py

# 환경 변수 직접 주입
OPENSKY_USERNAME=myid OPENSKY_PASSWORD=mypw python pipeline/opensky_producer.py
```

---

### 2.2 NOAA METAR — 공항 기상

| 항목 | 내용 |
|------|------|
| **소스** | [NOAA Aviation Weather API](https://aviationweather.gov/api/data/metar) |
| **엔드포인트** | `GET /api/data/metar?ids=RKSI,RKSS,...&format=json` |
| **수집 스크립트** | `pipeline/metar_producer.py` |
| **수집 주기** | 30분 폴링 (METAR 발행 주기 동일) |
| **Kafka 토픽** | `weather-event` |
| **인증** | 불필요 (완전 무료 공개 API) |

**수집 대상 공항 (ICAO 코드):**

| ICAO | 공항명 |
|------|--------|
| RKSI | 인천국제공항 |
| RKSS | 김포국제공항 |
| RKPC | 제주국제공항 |
| RKPK | 김해국제공항 |
| RKTN | 대구국제공항 |
| RKTU | 청주국제공항 |
| RKJJ | 광주공항 |
| RKJB | 무안국제공항 |

**수집 필드:**

| 필드 | 설명 | 단위 |
|------|------|------|
| `icao` | 공항 ICAO 코드 | — |
| `observed_at` | 관측 시각 | UTC ISO8601 |
| `temp_c` | 기온 | °C |
| `dewpoint_c` | 이슬점 | °C |
| `wind_dir_deg` | 풍향 | deg |
| `wind_speed_kt` | 풍속 | kt |
| `wind_gust_kt` | 돌풍 | kt |
| `visibility_m` | 가시거리 | m |
| `ceiling_ft` | 운저 고도 | ft |
| `flight_category` | 비행 카테고리 | VFR/MVFR/IFR/LIFR |
| `raw_metar` | 원본 METAR 문자열 | — |

**Kafka 메시지 스키마 (JSON):**

```json
{
  "icao": "RKSI",
  "airport_name": "인천국제공항",
  "observed_at": "2026-04-03T09:00:00Z",
  "temp_c": 8.0,
  "wind_speed_kt": 12,
  "visibility_m": 9999,
  "flight_category": "VFR",
  "raw_metar": "RKSI 030900Z 29012KT ...",
  "source": "NOAA"
}
```

---

## 3. 정적 / 배치 데이터

### 3.1 Kaggle Flight Delay Dataset

| 항목 | 내용 |
|------|------|
| **소스** | [Kaggle — 2015 Flight Delays and Cancellations](https://www.kaggle.com/datasets/usdot/flight-delays) |
| **출처** | U.S. DOT Bureau of Transportation Statistics |
| **수집 스크립트** | `analysis/download_dataset.py` |
| **다운로드 방식** | Kaggle API (`kaggle datasets download`) |
| **파일명** | `data/raw/flights.csv` |
| **크기** | 약 5.8M 행 × 31 컬럼 (~580MB) |

**원본 주요 컬럼:**

| 컬럼 | 설명 |
|------|------|
| `YEAR`, `MONTH`, `DAY` | 날짜 |
| `AIRLINE` | 항공사 코드 (IATA 2자리) |
| `FLIGHT_NUMBER` | 편명 |
| `ORIGIN_AIRPORT` | 출발 공항 (IATA) |
| `DESTINATION_AIRPORT` | 도착 공항 (IATA) |
| `SCHEDULED_DEPARTURE` | 예정 출발 시각 (HHMM) |
| `DEPARTURE_DELAY` | 출발 지연 (분) |
| `ARRIVAL_DELAY` | 도착 지연 (분) |
| `DISTANCE` | 비행 거리 (마일) |
| `AIR_TIME` | 비행 시간 (분) |
| `WEATHER_DELAY` | 기상 귀책 지연 (분) |
| `LATE_AIRCRAFT_DELAY` | 전편 지연 귀책 (분) |
| `CANCELLED` | 취소 여부 |

**EDA 요약 (전처리 후 500,000편 샘플 기준):**

| 지표 | 값 |
|------|----|
| 전체 항공편 | 500,000편 |
| 지연 (>0분) | 194,222편 (38.8%) |
| 취소 | 16,824편 (3.4%) |
| 평균 도착 지연 | 6.2분 |
| 중위 도착 지연 | -4.0분 (조기 도착) |
| 표준편차 | 40.5분 |
| 최대 지연 | 1,971분 |

**지연 원인별 기여 비율:**

| 원인 | 비율 |
|------|------|
| 전편 지연 (Cascade) | 39.6% |
| 항공사 귀책 | 31.2% |
| 국가항공시스템 (NAS) | 23.3% |
| 기상 | 5.7% |
| 보안 | 0.1% |

**다운로드 방법:**
```bash
# kaggle.json 설정 후
python analysis/download_dataset.py
```

---

### 3.2 FAA / ASPM 운항 통계

| 항목 | 내용 |
|------|------|
| **소스** | FAA Aviation System Performance Metrics (ASPM) |
| **URL** | https://aspm.faa.gov/opsnet/sys/Airport.asp |
| **활용** | Feature Engineering — `origin_hourly_departures`, `dest_hourly_arrivals` 등 이력 Feature |
| **형태** | 수동 다운로드 CSV → `data/raw/aspm_*.csv` |

---

## 4. LLM 학습용 데이터

### 4.1 LiveATC 교신 음성 수집

| 항목 | 내용 |
|------|------|
| **소스** | [LiveATC.net](https://www.liveatc.net) 공개 아카이브 |
| **수집 스크립트** | `llm_data/download_liveatc.py` |
| **수집량** | 약 10시간 분량 mp3 |
| **출력 경로** | `data/liveatc/audio/` |
| **인덱스** | `data/liveatc/index.csv` |
| **이용약관** | 개인 학습·연구 목적 허용, 상업적 재배포 금지 |

**수집 대상 공항 (ICAO):**

```
KJFK (뉴욕 JFK)  ·  KLAX (로스앤젤레스)  ·  KORD (시카고 오헤어)
KATL (애틀랜타)  ·  KDEN (덴버)
```

**실행:**
```bash
python llm_data/download_liveatc.py
# 공항·시간 지정
python llm_data/download_liveatc.py --hours 10 --airports KJFK KLAX KORD
```

---

### 4.2 Whisper STT 변환

| 항목 | 내용 |
|------|------|
| **모델** | `openai/whisper-large-v3` |
| **수집 스크립트** | `llm_data/transcribe_whisper.py` |
| **입력** | `data/liveatc/audio/*.mp3` |
| **출력** | `data/liveatc/transcripts/*.json` + `transcripts_index.csv` |
| **전처리** | `ffmpeg` 필수 (PATH 등록) |

**출력 스키마:**
```json
{
  "airport": "KJFK",
  "filename": "KJFK_2025-01-15_14-00.mp3",
  "duration_sec": 1800,
  "text": "Delta four twenty-seven heavy, runway two-two left, cleared for takeoff...",
  "segments": [
    {"start": 0.0, "end": 3.4, "text": "Delta four twenty-seven heavy..."}
  ],
  "language": "en",
  "transcribed_at": "2026-01-10T09:00:00Z"
}
```

**실행:**
```bash
# GPU
python llm_data/transcribe_whisper.py --model large-v3

# CPU (느림)
python llm_data/transcribe_whisper.py --device cpu
```

---

### 4.3 ATC 텍스트 정제

| 항목 | 내용 |
|------|------|
| **수집 스크립트** | `llm_data/clean_atc_text.py` |
| **입력** | `data/liveatc/transcripts/*.json` |
| **출력** | `data/liveatc/corpus_clean.jsonl` |

**주요 정제 규칙 (약어 복원):**

| 약어 | 복원 |
|------|------|
| `SQ` | Squawk |
| `HDG` | Heading |
| `ALT` | Altitude |
| `SPD` | Speed |
| `RWY` | Runway |
| `TWY` | Taxiway |
| `ILS` | Instrument Landing System |
| `VOR` | VHF Omnidirectional Range |
| `FL` | Flight Level |
| `kt` | knots |

---

### 4.4 ICAO / FAA 문서 PDF 파싱

| 항목 | 내용 |
|------|------|
| **수집 스크립트** | `llm_data/parse_icao_pdf.py` |
| **입력 디렉토리** | `data/pdfs/` |
| **출력** | `data/icao/chunks.jsonl`, `data/icao/toc.csv` |

**지원 문서:**

| 문서 | 설명 | 입수 경로 |
|------|------|-----------|
| ICAO Doc 8168 (PANS-OPS) | 계기 비행 절차 | icao.int (계정 필요) |
| ICAO Doc 4444 (PANS-ATM) | 관제 절차 | icao.int (계정 필요) |
| FAA AIM | 항공정보 매뉴얼 | faa.gov (무료) |
| FAR Part 91 | 일반 운항 규정 | ecfr.gov (무료) |
| FAR Part 121 | 항공운송 운항 규정 | ecfr.gov (무료) |

**청크 스키마:**
```json
{
  "doc": "FAA_AIM",
  "section": "7-6-4",
  "title": "Emergency Signals",
  "text": "When an aircraft is in distress...",
  "chunk_id": "FAA_AIM_0342"
}
```

**실행:**
```bash
python llm_data/parse_icao_pdf.py
python llm_data/parse_icao_pdf.py --pdf-dir data/pdfs/
```

---

### 4.5 GPT-4 API QA 쌍 생성

| 항목 | 내용 |
|------|------|
| **수집 스크립트** | `llm_data/generate_qa_gpt4.py` |
| **사용 모델** | `gpt-4o` (OpenAI API) |
| **비용** | ~$50 (1회성) |
| **총 생성량** | ~60,000건 |
| **환경 변수** | `OPENAI_API_KEY` |

**생성 유형별 수량:**

| 유형 | 수량 | 설명 |
|------|------|------|
| A. 규정 QA | ~25,000건 | FAR/ICAO 규정 조항 기반 |
| B. ATC 절차 QA | ~20,000건 | 관제 절차·교신 시나리오 기반 |
| C. 이상 상황 QA | ~10,000건 | 비상 절차·비정상 운항 기반 |
| D. 용어 정의 QA | ~5,000건 | 항공 용어 해설 |

**출력 파일:**
```
data/qa/regulation_qa.jsonl
data/qa/procedure_qa.jsonl
data/qa/emergency_qa.jsonl
data/qa/terminology_qa.jsonl
data/qa/all_qa.jsonl          ← 통합본
```

**Alpaca 포맷 예시:**
```json
{
  "instruction": "FAA AIM 7-6-4에 따른 비상 신호 절차를 설명하세요.",
  "input": "",
  "output": "FAA AIM 7-6-4에 따르면, 항공기가 비상 상황 시 Squawk 7700을 설정하고...",
  "source": "FAA_AIM",
  "type": "regulation_qa"
}
```

**실행:**
```bash
python llm_data/generate_qa_gpt4.py
python llm_data/generate_qa_gpt4.py --target 5000   # 빠른 테스트
python llm_data/generate_qa_gpt4.py --resume        # 이어서 생성
```

---

### 4.6 이상 탐지 자연어 설명 생성

| 항목 | 내용 |
|------|------|
| **수집 스크립트** | `llm_data/generate_anomaly_nl.py` |
| **생성량** | ~10,000건 |
| **출력** | `data/qa/anomaly_nl.jsonl` |

Isolation Forest 탐지 결과를 입력받아 관제사용 자연어 경보 설명 생성.

**예시:**
```json
{
  "instruction": "다음 항공 이상 탐지 결과를 관제사에게 자연어로 설명하세요.",
  "input": "항공기 KE123, 고도 급변 감지: FL350→FL290 (60초 내 -1800ft), 속도 정상",
  "output": "KE123편에서 비정상적인 고도 강하 패턴이 감지되었습니다. 60초 이내 1,800피트 강하는 정상 강하율(500fpm)을 초과합니다. FAA AIM 7-6-4에 따라 즉시 조종사 확인 교신이 필요하며, 필요 시 비상 선언 절차(7700 스쿼크)를 준비하십시오.",
  "type": "anomaly_nl"
}
```

---

### 4.7 승객 안내문 생성

| 항목 | 내용 |
|------|------|
| **수집 스크립트** | `llm_data/generate_passenger_ann.py` |
| **생성량** | ~5,000건 |
| **출력** | `data/qa/passenger_ann.jsonl` |

지연·이상 상황별 한/영 승객 안내 방송문 페어 생성.

**예시:**
```json
{
  "instruction": "KE456편 착륙 복행(Go-Around) 상황을 승객에게 안내하세요.",
  "input": "",
  "output": "승객 여러분, 안전한 착륙을 위해 현재 복행 절차를 수행 중입니다. 잠시 후 재착륙 예정이오니 좌석벨트를 매주시기 바랍니다.",
  "type": "passenger_announcement"
}
```

---

## 5. 최종 데이터셋 구성

### ML 모델 학습 데이터

| 항목 | 수치 |
|------|------|
| 원본 데이터 | 5.8M 행 (Kaggle flights.csv) |
| 전처리 후 | 500,000편 (10% 샘플링) |
| 학습셋 | 400,000편 (80%) |
| 검증셋 | 50,000편 (10%) |
| 테스트셋 | 50,000편 (10%) |
| Feature 수 | 20개 수치 + 3개 범주 = **23개** |

**20개 수치 Feature:**

```python
NUMERIC_FEATURES = [
    "dep_hour", "dep_minute", "dep_dayofweek", "dep_month", "dep_dayofyear",
    "is_weekend", "distance_miles", "sched_elapsed_min",
    "prev_dep_delay_min", "prev_arr_delay_min", "is_prev_delayed",
    "origin_hourly_departures", "dest_hourly_arrivals", "dep_month_weather_score",
    "origin_weather_hist_delay", "dest_weather_hist_delay",
    "carrier_hist_delay", "origin_hist_delay", "dest_hist_delay", "route_hist_delay"
]
```

**3개 범주 Feature:**
```python
CATEGORICAL_FEATURES = ["carrier_code", "origin", "dest"]
```

---

### LLM 파인튜닝 데이터셋 (Alpaca 포맷)

| 출처 | 수량 | 비율 |
|------|------|------|
| 이상 탐지 자연어 설명 | 10,000건 | 66.7% |
| 승객 안내문 | 5,000건 | 33.3% |
| **소계 (Alpaca 데이터셋)** | **15,000건** | — |
| QA 쌍 (GPT-4 생성) | ~60,000건 | 별도 |
| **자체 구축 총합** | **약 13,969건** | — |

> `dataset_stats.json` 기준 실제 집계: `anomaly_nl` 10,000건 + `passenger_ann` 5,000건 → 총 **15,000건** Alpaca 포맷

**Train/Val/Test 분할:**

| 분할 | 수량 |
|------|------|
| Train | 12,750건 (85%) |
| Validation | 1,500건 (10%) |
| Test | 750건 (5%) |

**평균 데이터 길이:**
- 평균 instruction 길이: 8.0자
- 평균 output 길이: 26.3자

---

### DPO 선호도 데이터

| 항목 | 내용 |
|------|------|
| **생성 스크립트** | `dpo/build_dpo_pairs.py` |
| **수량** | 1,000건 (chosen / rejected 페어) |
| **출력** | `data/dpo/dpo_pairs.jsonl` |

---

### 벤치마크 평가셋

| 항목 | 내용 |
|------|------|
| **생성 스크립트** | `evaluation/build_benchmark.py` |
| **수량** | 500건 |
| **출력** | `data/eval/benchmark_eval.jsonl` |

| 유형 | 수량 |
|------|------|
| 이상 탐지 설명 | 331건 (66.2%) |
| 승객 안내문 | 125건 (25.0%) |
| 규정 QA | 44건 (8.8%) |

---

## 6. 데이터 디렉토리 구조

```
data/
├── raw/
│   └── flights.csv               # Kaggle 원본 (5.8M 행)
├── processed/
│   ├── train.parquet             # 학습셋 (400K)
│   ├── val.parquet               # 검증셋 (50K)
│   └── test.parquet              # 테스트셋 (50K)
├── liveatc/
│   ├── audio/                    # mp3 원본 (10시간)
│   ├── transcripts/              # Whisper STT 결과 JSON
│   ├── index.csv                 # 다운로드 인덱스
│   ├── transcripts_index.csv     # STT 변환 결과 요약
│   └── corpus_clean.jsonl        # 정제된 ATC 코퍼스
├── pdfs/                         # ICAO / FAA 원본 PDF
├── icao/
│   ├── chunks.jsonl              # PDF 파싱 청크
│   └── toc.csv                   # 문서 목차 구조
├── qa/
│   ├── regulation_qa.jsonl       # 규정 QA (~25K)
│   ├── procedure_qa.jsonl        # 절차 QA (~20K)
│   ├── emergency_qa.jsonl        # 비상 QA (~10K)
│   ├── terminology_qa.jsonl      # 용어 QA (~5K)
│   ├── anomaly_nl.jsonl          # 이상 탐지 설명 (10K)
│   └── passenger_ann.jsonl       # 승객 안내문 (5K)
├── alpaca/
│   ├── aviation_alpaca_train.jsonl  # 학습셋 (12,750건)
│   ├── aviation_alpaca_val.jsonl    # 검증셋 (1,500건)
│   ├── aviation_alpaca_test.jsonl   # 테스트셋 (750건)
│   └── dataset_stats.json           # 통계 요약
├── dpo/
│   └── dpo_pairs.jsonl           # DPO 선호도 페어 (1K건)
├── eval/
│   ├── benchmark_eval.jsonl      # 평가셋 (500건)
│   ├── results_eval.json         # ROUGE-L / BLEU 결과
│   └── comparison_table_sim.md   # Base vs Fine-tuned 비교
├── models/
│   ├── xgboost_best.pkl          # XGBoost 모델 + 전처리기
│   └── isolation_forest.pkl      # Isolation Forest 파이프라인
├── vectordb/
│   └── chroma.sqlite3            # ChromaDB 벡터 스토어
├── figures/                      # EDA / SHAP 시각화
└── eda_summary.txt               # EDA 요약 리포트
```

---

## 7. 환경 변수 및 인증

프로젝트 루트의 `.env` 파일에 설정:

```env
# OpenSky API (선택 — 익명 접근 가능하나 요청 제한)
OPENSKY_USERNAME=your_username
OPENSKY_PASSWORD=your_password

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_FLIGHT_POSITION=flight-position
KAFKA_TOPIC_WEATHER_EVENT=weather-event

# METAR 수집 공항 (쉼표 구분)
METAR_STATIONS=RKSI,RKSS,RKPC,RKPK,RKTN,RKTU,RKJJ,RKJB

# GPT-4 QA 생성
OPENAI_API_KEY=sk-...

# vLLM 서빙
VLLM_BASE_URL=http://localhost:8001/v1
LLM_MODEL_ID=aviation-llm
```

**Kaggle 인증:**
```
Windows: C:\Users\<본인>\AppData\Roaming\kaggle\kaggle.json
Linux/Mac: ~/.kaggle/kaggle.json
```

```json
{"username": "your_kaggle_id", "key": "your_api_key"}
```

---

*본 문서는 SkyOps Intelligence 프로젝트의 데이터 수집 전 과정을 기록합니다.*
*문의: doublej.biz01@gmail.com*
