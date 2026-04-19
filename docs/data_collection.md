# 📦 SkyOps Intelligence — 데이터 수집 명세서

> **최종 업데이트**: 2026-04-19 (v2.2.0 · Strategic Review Stage 1–4 완료 기준)
> **이전 개정**: 2026-04-03 (10주차 MVP)

v2.2.0 기준 반영 사항:
- **P5+** FAA SWIM 실연동 (Solace JMS / AIXM 5.1 / 219건 60 s 수신 검증)
- **P6-B** Confluent Avro Schema Registry 6 토픽 BACKWARD 호환
- **P6-D** Apache Iceberg Bronze / Silver / Gold medallion (v2.1.8 REST catalog)
- **P6-A** Feast Feature Store (offline parquet + online Redis db=1)
- **P7** OpenLineage + Marquez 학습·데이터 lineage
- **Stage 2 (ADR-005)** Rotation feature 5 종 production 투입 + Graph topology / Upstream delay state candidate bundle
- **Stage 2 (ADR-005)** CQR 보정기 (`conformal_calibrator_cqr.pkl`) 서빙 연동

---

## 목차

1. [전체 데이터 파이프라인 개요](#1-전체-데이터-파이프라인-개요)
2. [실시간 스트리밍 데이터](#2-실시간-스트리밍-데이터)
   - 2.1 OpenSky ADS-B — 항공기 위치
   - 2.2 NOAA / KMA METAR — 공항 기상
   - 2.3 FAA SWIM — NOTAM / ATFM (P5+ 실연동)
   - 2.4 한국공항공사 ACDM — 공공데이터포털 (P7-E)
3. [Kafka + Avro Schema Registry](#3-kafka--avro-schema-registry)
4. [정적 / 배치 데이터](#4-정적--배치-데이터)
   - 4.1 Kaggle Flight Delay Dataset
   - 4.2 FAA / ASPM 운항 통계
5. [LLM 학습용 데이터](#5-llm-학습용-데이터)
   - 5.1 LiveATC 교신 음성
   - 5.2 Whisper STT
   - 5.3 ATC 텍스트 정제
   - 5.4 ICAO / FAA PDF 파싱
   - 5.5 GPT-4 QA 쌍 생성
   - 5.6 이상 탐지 자연어 설명
   - 5.7 승객 안내문
6. [Feature Store / Iceberg / OpenLineage](#6-feature-store--iceberg--openlineage)
7. [최종 데이터셋 구성](#7-최종-데이터셋-구성)
8. [데이터 디렉토리 구조](#8-데이터-디렉토리-구조)
9. [환경 변수 및 인증](#9-환경-변수-및-인증)

---

## 1. 전체 데이터 파이프라인 개요

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            외부 데이터 소스                              │
│  OpenSky │ NOAA+KMA METAR │ FAA SWIM (JMS) │ KAC ACDM │ Kaggle │ LiveATC │
└─────┬────────┬────────────────┬───────────────┬─────────┬────────┬──────┘
      │        │                │               │         │        │
  [30초 폴링] [30분] [Solace JMS subscribe]  [API 폴링]  [1회]   [mp3]
      │        │                │               │         │        │
      ▼        ▼                ▼               ▼         ▼        ▼
  ┌───────────────────────────────────────────┐ flights. Whisper
  │       Kafka + Avro Schema Registry        │  csv(배치)  STT
  │  6 토픽 · BACKWARD 호환 정책 (P6-B)       │     │         │
  │ flight-position / weather-event / notam / │     │         │
  │ atfm-restriction / alert-decision /       │     │         │
  │ acdm-milestone                            │     │         │
  └───────────┬────────────────────────┬──────┘     │         │
              │                        │            │         │
              ▼                        ▼            ▼         ▼
          PyFlink                 CEP rules      Feature   GPT-4 QA
         5분 집계                  (alerts)      Engineering  생성
              │                        │            │         │
              ▼                        ▼            ▼         ▼
  ┌──────────────────────────────────────────────────────────┐
  │    Apache Iceberg  (Bronze / Silver / Gold · P6-D)       │
  │  SQL catalog (dev) OR Nessie REST + MinIO S3 (warehouse) │
  │  + OpenLineage 이벤트 → Marquez (P7)                     │
  └──────────────────────────────────────────────────────────┘
              │                        │            │
              ▼                        ▼            ▼
          Feast FV           ChromaDB 161 chunks   Alpaca 통합
       (online Redis db=1)     (BAAI/bge-m3)     (aviation_alpaca.jsonl)
```

---

## 2. 실시간 스트리밍 데이터

### 2.1 OpenSky ADS-B — 항공기 위치

| 항목 | 내용 |
|------|------|
| **소스** | [OpenSky Network](https://opensky-network.org) REST API |
| **엔드포인트** | `GET /api/states/all?lamin=33.0&lomin=124.0&lamax=38.9&lomax=130.0` |
| **수집 스크립트** | `pipeline/opensky_producer.py` · Avro 전송: `pipeline/avro_producer.py` |
| **수집 주기** | 30초 폴링 |
| **Kafka 토픽** | `flight-position` (Avro 스키마 v2.0) |
| **커버리지** | 한반도 바운딩 박스 (위도 33.0~38.9 / 경도 124.0~130.0) |
| **인증** | OpenSky 계정 (무료 / 익명 접근 가능, 제한 있음) |
| **Avro 스키마** | `pipeline/schemas/flight_position.avsc` |

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

**Kafka 메시지 스키마 (Avro, v2.0):**

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
  "event_timestamp": "2026-04-19T09:00:00Z",
  "source": "opensky"
}
```

**실행:**
```bash
# .env 설정 후
python pipeline/opensky_producer.py
# 또는 Avro+Schema Registry 경유
python -m pipeline.avro_producer --topic flight-position
```

---

### 2.2 NOAA / KMA METAR — 공항 기상

| 항목 | 내용 |
|------|------|
| **소스** | [NOAA Aviation Weather API](https://aviationweather.gov/api/data/metar) + 기상청 (KMA) 공공데이터 |
| **엔드포인트** | NOAA: `GET /api/data/metar?ids=RKSI,RKSS,...&format=json` · KMA: 공공데이터포털 |
| **수집 스크립트** | `pipeline/metar_producer.py` |
| **수집 주기** | 30분 폴링 (METAR 발행 주기 동일) |
| **Kafka 토픽** | `weather-event` (Avro) |
| **인증** | NOAA 불필요 · KMA `KMA_API_KEY` 필요 |
| **Avro 스키마** | `pipeline/schemas/weather_event.avsc` |

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

---

### 2.3 FAA SWIM — NOTAM / ATFM (P5+ 실연동)

> 🎯 **프로젝트의 플래그십 성과** — 대학 프로젝트로서는 드물게 FAA 공식 프로덕션
> 브로커에 JMS 구독을 맺고 실시간 NOTAM 219 건을 60 초 안에 수신 (parse_err=0) 검증.

| 항목 | 내용 |
|------|------|
| **소스** | [FAA System Wide Information Management (SWIM)](https://www.faa.gov/air_traffic/technology/swim) |
| **프로토콜** | Solace PubSub+ SMF over TLS 1.2 |
| **엔드포인트** | `smf://ems2.swim.faa.gov:55443` (프로덕션) |
| **수집 스크립트** | `pipeline/notam_producer.py` · `pipeline/atfm_producer.py` |
| **Kafka 토픽** | `notam` · `atfm-restriction` (Avro) |
| **TLS trust store** | c_rehash 형식 + DigiCert Global Root G2 수동 import |
| **인증** | FAA SWIM 구독 계약 (client cert) — 자세한 발급 절차는 `docs/runbooks/faa-swim-onboarding.md` |

**페이로드 포맷:**
- NOTAM: AIXM 5.1 XML + `faa event:` namespace
- ATFM: GroundDelay / ReroutingAdvisory / TrafficManagementInit XSD

**Q-code 매핑 (일부):**

| Q-code | 의미 |
|---|---|
| `QMRLC` | 활주로 폐쇄 |
| `QNDAS` | NAV 시설 서비스 불가 |
| `QIPAS` | 계기 접근 정지 |
| `QWAAS` | 공역 경고 (활성) |

**수집 검증 (2026-04-15 P5+):**

```
received=219  published=219  parse_err=0   (60s window)
```

**실행:**
```bash
# SWIM_CLIENT_CERT / SWIM_CLIENT_KEY / SWIM_VPN 설정 필수
python pipeline/notam_producer.py --queue swim/faa/notam
python pipeline/atfm_producer.py --queue swim/faa/tfm
```

---

### 2.4 한국공항공사 ACDM — 공공데이터포털 (P7-E)

| 항목 | 내용 |
|------|------|
| **소스** | 한국공항공사 A-CDM (Airport Collaborative Decision Making) REST API |
| **포털** | [data.go.kr — 한국공항공사 운항정보](https://www.data.go.kr) |
| **수집 스크립트** | `pipeline/kac_acdm_client.py` |
| **Kafka 토픽** | `acdm-milestone` (Avro, P8 추가) |
| **인증** | `KAC_API_KEY` (공공데이터포털 신청) |
| **상태** | 코드 준비 완료 · **API key 승인 대기 중** (ADR-003 follow-up) |

**A-CDM 마일스톤 필드:**
- `target_off_block_time` (TOBT)
- `target_startup_approval_time` (TSAT)
- `actual_off_block_time` (AOBT)
- `target_landing_time` (TLDT)

EUROCONTROL NM B2B 대체 경로로 한국 traffic 의 지연 상황 추정에 활용.

---

## 3. Kafka + Avro Schema Registry

P6-B (2026-04-15) 에서 Confluent Schema Registry 도입. JSON 파이프라인 →
Avro BACKWARD 호환 정책으로 이관 완료.

### 3.1 토픽 구성 (6개)

| 토픽 | 스키마 | 생산자 | 소비자 | 용도 |
|---|---|---|---|---|
| `flight-position` | `flight_position.avsc` | opensky_producer | Flink, ModelStore | ADS-B 실시간 위치 |
| `weather-event` | `weather_event.avsc` | metar_producer | Flink, 대시보드 | METAR 관측 |
| `notam` | `notam.avsc` | notam_producer (SWIM) | 대시보드, ICAO 영향도 계산 | FAA 공지 |
| `atfm-restriction` | `atfm_restriction.avsc` | atfm_producer (SWIM) | CEP rules | 교통 흐름 제한 |
| `alert-decision` | `alert_decision.avsc` | CEP rules / serving | Redis stream, OpenLineage | 이상 탐지 결정 |
| `acdm-milestone` | `acdm_milestone.avsc` | kac_acdm_client | Flink | 한국 A-CDM 마일스톤 |

### 3.2 Schema Registry 서비스

- Docker Compose: `docker-compose.yml:61` `confluentinc/cp-schema-registry:7.5.0` (profile `schema`, port 8081)
- 호환성 정책: **BACKWARD** — 새 스키마는 과거 consumer 가 기본값으로 읽을 수 있어야 함
- Producer: `pipeline/avro_producer.py::SerializingProducer` + `AvroSerializer`
- CLI: `skyops-schema-registry` (pyproject.toml 엔트리포인트)
- 스키마 문서: `pipeline/schema_doc.md`

### 3.3 실행

```bash
# Schema Registry 포함 기동
docker compose --profile schema up -d

# 스키마 업로드 / 조회
skyops-schema-registry register --topic flight-position \
  --schema pipeline/schemas/flight_position.avsc
skyops-schema-registry list
```

---

## 4. 정적 / 배치 데이터

### 4.1 Kaggle Flight Delay Dataset

| 항목 | 내용 |
|------|------|
| **소스** | [Kaggle — 2015 Flight Delays and Cancellations](https://www.kaggle.com/datasets/usdot/flight-delays) |
| **출처** | U.S. DOT Bureau of Transportation Statistics |
| **수집 스크립트** | `analysis/download_dataset.py` |
| **다운로드 방식** | Kaggle API (`kaggle datasets download`) |
| **파일명** | `data/raw/flights.csv` |
| **크기** | 5.7 M 행 × 31 컬럼 (~580 MB) |

**원본 주요 컬럼:**

| 컬럼 | 설명 |
|------|------|
| `FL_DATE` | 운항 날짜 (ADR-004 / ADR-005 의 chronological split 기준) |
| `AIRLINE` | 항공사 코드 (IATA 2자리) |
| `FLIGHT_NUMBER` | 편명 |
| `ORIGIN_AIRPORT` | 출발 공항 (IATA) |
| `DESTINATION_AIRPORT` | 도착 공항 (IATA) |
| `CRS_DEP_TIME` / `CRS_ARR_TIME` | 예정 출발·도착 시각 (HHMM) |
| `DEP_DELAY` / `ARR_DELAY` | 출발·도착 지연 (분) |
| `DISTANCE` | 비행 거리 (마일) |
| `AIR_TIME` | 비행 시간 (분) |
| `WEATHER_DELAY` | 기상 귀책 지연 (분) |
| `LATE_AIRCRAFT_DELAY` | 전편 지연 귀책 (분) |
| `CANCELLED` | 취소 여부 |

**EDA 요약 (전처리 후 500,000 편 샘플 기준):**

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

> ℹ️ **ADR-005 D1** — "전편 지연 39.6%" 가 P1 Rotation features 5 종 추가의 도메인
> 근거. 실제 성능은 Test R² 0.0996 → 0.4328 (+335%).

**다운로드 방법:**
```bash
# kaggle.json 설정 후
python analysis/download_dataset.py
```

---

### 4.2 FAA / ASPM 운항 통계

| 항목 | 내용 |
|------|------|
| **소스** | FAA Aviation System Performance Metrics (ASPM) |
| **URL** | https://aspm.faa.gov/opsnet/sys/Airport.asp |
| **활용** | Feature Engineering — `origin_hourly_departures`, `dest_hourly_arrivals` 등 이력 Feature |
| **형태** | 수동 다운로드 CSV → `data/raw/aspm_*.csv` |

---

## 5. LLM 학습용 데이터

### 5.1 LiveATC 교신 음성 수집

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
python llm_data/download_liveatc.py --hours 10 --airports KJFK KLAX KORD
```

---

### 5.2 Whisper STT 변환

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

---

### 5.3 ATC 텍스트 정제

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

### 5.4 ICAO / FAA PDF 파싱

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

> ChromaDB 적재 대상. 초기 6 chunks → P6 95 → **P6-F 최종 161 chunks**
> (FAA AIM 26 · ICAO Annex 20 · SOP 25 · runbook 18 · RKSI 특화 15 등)

---

### 5.5 GPT-4 QA 쌍 생성

| 항목 | 내용 |
|------|------|
| **수집 스크립트** | `llm_data/generate_qa_gpt4.py` |
| **사용 모델** | `gpt-4o` (OpenAI API) |
| **비용** | ~$50 (1회성) |
| **총 생성량** | 약 60,000건 (프로젝트 목표) |
| **환경 변수** | `OPENAI_API_KEY` |

**생성 유형별 수량:**

| 유형 | 수량 | 설명 |
|------|------|------|
| A. 규정 QA | ~25,000건 | FAR / ICAO 규정 조항 기반 |
| B. ATC 절차 QA | ~20,000건 | 관제 절차·교신 시나리오 기반 |
| C. 이상 상황 QA | ~10,000건 | 비상 절차·비정상 운항 기반 |
| D. 용어 정의 QA | ~5,000건 | 항공 용어 해설 |

---

### 5.6 이상 탐지 자연어 설명

| 항목 | 내용 |
|------|------|
| **수집 스크립트** | `llm_data/generate_anomaly_nl.py` |
| **생성량** | ~10,000 건 |
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

### 5.7 승객 안내문

| 항목 | 내용 |
|------|------|
| **수집 스크립트** | `llm_data/generate_passenger_ann.py` |
| **생성량** | ~5,000 건 |
| **출력** | `data/qa/passenger_ann.jsonl` |

지연·이상 상황별 한/영 승객 안내 방송문 페어 생성.

---

## 6. Feature Store / Iceberg / OpenLineage

운영 환경의 training-serving skew 와 lineage 공백을 닫기 위해 도입한 데이터
인프라 3 종.

### 6.1 Apache Iceberg — Bronze / Silver / Gold (P6-D · v2.1.8)

ADR-004 D3 결정. `feature_store/iceberg_bootstrap.py::_build_catalog_config()` 가
env `ICEBERG_CATALOG` 에 따라 두 모드 지원:

| 모드 | env | 사용 환경 |
|---|---|---|
| `sql` (기본) | `ICEBERG_CATALOG=sql` | 로컬 dev — SQLite catalog + local file warehouse |
| `rest` | `ICEBERG_CATALOG=rest` | 학습·스테이징 — **Nessie** REST + **MinIO** S3 |

REST 모드는 `docker compose --profile warehouse up -d` 로 nessie / minio /
minio-init 기동.

**Medallion 10 테이블:**

| Layer | 테이블 | 용도 |
|---|---|---|
| Bronze | `flight_position_raw` / `weather_event_raw` / `notam_raw` / `atfm_restriction_raw` | 원본 JSON/AIXM 그대로 저장 |
| Silver | `flight_features` / `aircraft_phase` / `airport_context` | 정제 + 피처 결합 (학습 input) |
| Gold | `delay_train_split` / `inference_log` / `anomaly_decisions` | 모델 소비 + 감사용 |

Writer: `feature_store/iceberg_writer.py` (`write_bronze_event`,
`write_silver_features`, `write_gold_inference_log`,
`write_gold_anomaly_decision`).

### 6.2 Feast Feature Store (P6-A)

Offline parquet + Online Redis db=1 2계층. Feature View 정의:
`feature_store/feature_views.py`.

| Feature View | 엔티티 | 소스 | 용도 |
|---|---|---|---|
| `flight_rotation` | aircraft | `data/processed/rotation_features.parquet` | P1 Rotation 5종 (production) |
| `live_position` | icao24 | `data/feast/live_position.parquet` | ADS-B 스냅샷 + 단계 분류 |
| `airport_congestion` | airport | `data/feast/airport_congestion.parquet` | 시간당 이·착륙 편수 |
| `notam_impact` | airport | `data/feast/notam_impact.parquet` | FAA SWIM 기반 공항 영향도 |
| `airport_graph` | airport | `data/feast/airport_graph.parquet` | **Stage 2 후보** — topology |
| `upstream_delay` | airport | `data/feast/upstream_delay.parquet` | **Stage 2 후보** — 롤링 지연 상태 |

**Feature Service 2종:**
- `delay_prediction_v2` — 현 production 모델 (rotation + congestion + notam)
- `delay_prediction_v3_network` — **Stage 2 candidate** (Graph topology + Upstream delay state 포함)

### 6.3 OpenLineage + Marquez (P7)

학습 실행 = OpenLineage START + COMPLETE 이벤트 쌍 발행 →
`monitoring/lineage.py::emit_train_run_*`. Input 은 Iceberg Silver 테이블,
Output 은 Gold. Marquez UI 는 `docker-compose.prod.yml` 의 서비스로 노출 (port 5000).

v2.1.8 부터 `model_version` 필드가 **MLflow Model Registry 버전** (`skyops-delay-xgb/v{N}`)
과 join 되어 "어느 dataset snapshot 으로 학습한 어느 모델 버전이 서빙 중인가"
를 Registry ↔ Marquez 두 UI 에서 모두 답변 가능.

---

## 7. 최종 데이터셋 구성

### 7.1 ML 모델 학습 데이터 (delay prediction)

| 항목 | 수치 |
|------|------|
| 원본 데이터 | 5.7 M 행 (Kaggle flights.csv) |
| 전처리 후 | 500,000 편 (10% 샘플링) |
| **Validation** 방식 | `TimeSeriesSplit(n_splits=5)` — ADR-004 D1 (shuffle 금지) |
| 학습셋 | 400,000 편 (80%) |
| 검증셋 (calibration 포함) | 50,000 편 (10%) |
| 테스트셋 | 50,000 편 (10%) |
| **Feature 수 (v2.1.9 기준)** | **25 numeric + 3 categorical = 28** |

**25개 수치 Feature (`serving/common/constants.py::NUMERIC_FEATURES`):**

```python
NUMERIC_FEATURES = [
    # 시간·거리 20개 (P0 base set)
    "dep_hour", "dep_minute", "dep_dayofweek", "dep_month",
    "dep_dayofyear", "is_weekend",
    "distance_miles", "sched_elapsed_min",
    "prev_dep_delay_min", "prev_arr_delay_min", "is_prev_delayed",
    "origin_hourly_departures", "dest_hourly_arrivals",
    "dep_month_weather_score",
    "origin_weather_hist_delay", "dest_weather_hist_delay",
    "carrier_hist_delay", "origin_hist_delay",
    "dest_hist_delay", "route_hist_delay",
    # Rotation features 5개 (P1 · 2026-04-14 · +335% R²)
    "rotation_depth", "prev_leg_arr_delay_min",
    "scheduled_turnaround_min", "actual_turnaround_min",
    "is_first_leg_of_day",
]
CATEGORICAL_FEATURES = ["carrier_code", "origin", "dest"]
```

### 7.2 Network-aware feature bundle (Stage 2, 다음 retrain 후보)

**현 production 모델에는 미포함** — `serving/common/constants.py::NETWORK_FEATURES`
에 정의되어 Feature Service `delay_prediction_v3_network` 로 묶여 있음.

```python
GRAPH_FEATURES_AIRPORT = [
    "origin_degree_total", "origin_pagerank", "origin_airport_hub_score",
    "dest_degree_total", "dest_pagerank", "dest_airport_hub_score",
]
GRAPH_FEATURES_ROUTE = [
    "route_volume", "route_rank", "route_degree_product", "route_hub_to_hub",
]
UPSTREAM_DELAY_FEATURES = [
    "origin_recent_delay_avg_60m", "origin_recent_delay_p95_60m",
    "origin_recent_volume_60m",
    "dest_recent_delay_avg_60m", "dest_recent_volume_60m",
    "origin_hub_congestion_ratio",
]
NETWORK_FEATURES = (
    GRAPH_FEATURES_AIRPORT + GRAPH_FEATURES_ROUTE + UPSTREAM_DELAY_FEATURES
)
```

산출 스크립트:
- `analysis/graph_features.py` — NetworkX DiGraph + pagerank / betweenness → `data/models/graph_features_{airports,routes}.csv`
- `analysis/upstream_delay.py` — 60-min leak-free rolling (`closed='left'`) → `data/models/upstream_delay_features.csv`

### 7.3 LLM 파인튜닝 데이터셋 (Alpaca 포맷)

| 출처 | 수량 | 비율 |
|------|------|------|
| 이상 탐지 자연어 설명 | 10,000건 | 66.7% |
| 승객 안내문 | 5,000건 | 33.3% |
| **Alpaca 데이터셋 소계** | **15,000건** | — |
| GPT-4 QA 쌍 (별도) | ~60,000건 | 별도 코퍼스 |
| **실 투입 학습 샘플 (QLoRA)** | **13,969건** | Filter 후 |

> 실제 학습 로그 기준 `dataset_stats.json` 의 **13,969 건** 이 QLoRA SFT 에 투입됨
> (Eval Token Accuracy 97.88%). Alpaca 15,000 건 중 일부는 품질 필터로 제거됨.

**Train / Val / Test 분할:**

| 분할 | 수량 |
|------|------|
| Train | 12,750건 (85%) |
| Validation | 1,500건 (10%) |
| Test | 750건 (5%) |

### 7.4 DPO 선호도 데이터

| 항목 | 내용 |
|------|------|
| **생성 스크립트** | `dpo/build_dpo_pairs.py` |
| **수량** | 1,000건 (chosen / rejected 페어) · P7 에서 추가 3,500건 시드 생성 (재학습 대기) |
| **출력** | `data/dpo/dpo_pairs.jsonl` |
| **Split** | HF `dataset.train_test_split(test_size=0.05, seed=42)` — 선호쌍은 시계열 이벤트 아니므로 random split 예외 (ADR-004 주석) |

### 7.5 벤치마크 평가셋

| 항목 | 내용 |
|------|------|
| **생성 스크립트** | `evaluation/build_benchmark.py` |
| **수량** | 500건 |
| **출력** | `data/eval/benchmark_eval.jsonl` |
| **RAGAs 결과** | `data/eval/ragas_results.json` — **v2.2.0** GitHub Actions `ragas_eval.yml` 로 주간 자동 실행 + PR 자동 실행 (ADR-007 D1) |

| 유형 | 수량 |
|------|------|
| 이상 탐지 설명 | 331건 (66.2%) |
| 승객 안내문 | 125건 (25.0%) |
| 규정 QA | 44건 (8.8%) |

---

## 8. 데이터 디렉토리 구조

```
data/
├── raw/
│   └── flights.csv                 # Kaggle 원본 (5.7M 행)
├── processed/
│   ├── train.parquet               # 학습셋 (TimeSeriesSplit 기준)
│   ├── val.parquet
│   ├── test.parquet
│   └── rotation_features.parquet   # P1 · Feast flight_rotation source
├── liveatc/
│   ├── audio/                      # mp3 원본 (10시간)
│   ├── transcripts/                # Whisper STT 결과
│   ├── index.csv
│   ├── transcripts_index.csv
│   └── corpus_clean.jsonl
├── pdfs/                           # ICAO / FAA 원본 PDF
├── icao/
│   ├── chunks.jsonl                # PDF 파싱 청크
│   └── toc.csv
├── qa/                             # LLM 학습용 QA
│   ├── regulation_qa.jsonl         # ~25K
│   ├── procedure_qa.jsonl          # ~20K
│   ├── emergency_qa.jsonl          # ~10K
│   ├── terminology_qa.jsonl        # ~5K
│   ├── anomaly_nl.jsonl            # 10K
│   └── passenger_ann.jsonl         # 5K
├── alpaca/
│   ├── aviation_alpaca_train.jsonl # 12,750건
│   ├── aviation_alpaca_val.jsonl   # 1,500건
│   ├── aviation_alpaca_test.jsonl  # 750건
│   └── dataset_stats.json          # 실제 13,969건 투입 기록
├── dpo/
│   └── dpo_pairs.jsonl             # 1K + 3,500 시드 (재학습 대기)
├── eval/
│   ├── benchmark_eval.jsonl        # 500건
│   ├── results_eval.json           # ROUGE-L / BLEU / 길이
│   ├── ragas_results.json          # v2.2.0 — CI 자동 생성
│   └── comparison_table_sim.md
├── analyst_feedback/               # P2 / v2.1.10
│   └── feedback.jsonl              # True/False positive 라벨 (HITL)
├── models/                         # v2.1.9+ 실제 아티팩트
│   ├── xgboost_best.pkl            # 현 production 모델
│   ├── isolation_forest.pkl        # base IF (phase fallback)
│   ├── isolation_forest_TAXI.pkl       # Per-phase IF × 7 (v2.1.10 routing)
│   ├── isolation_forest_TAKEOFF.pkl
│   ├── isolation_forest_CLIMB.pkl
│   ├── isolation_forest_CRUISE.pkl
│   ├── isolation_forest_DESCENT.pkl
│   ├── isolation_forest_APPROACH.pkl
│   ├── isolation_forest_LANDING.pkl
│   ├── ml_phase_classifier.pkl     # silver-label phase classifier
│   ├── conformal_calibrator.pkl    # symmetric split conformal
│   ├── conformal_calibrator_cqr.pkl  # v2.1.9 — asymmetric CQR (우선 로드)
│   ├── quantile_lower.pkl          # GBR loss=quantile α=0.05
│   ├── quantile_upper.pkl          # GBR loss=quantile α=0.95
│   ├── graph_features_airports.csv # v2.1.9 Stage 2
│   ├── graph_features_routes.csv   # v2.1.9 Stage 2
│   ├── upstream_delay_features.csv # v2.1.9 Stage 2 (sample)
│   ├── .reload_signal              # P6-C hot-reload trigger
│   └── llm/                        # QLoRA adapter + DPO weights
├── iceberg/                        # P6-D · local SQL catalog 모드
│   ├── catalog.db
│   └── <warehouse files>
├── feast/                          # P6-A · offline parquet + online Redis
│   ├── live_position.parquet
│   ├── airport_congestion.parquet
│   ├── notam_impact.parquet
│   ├── airport_graph.parquet       # v2.1.9 Stage 2
│   └── upstream_delay.parquet      # v2.1.9 Stage 2
├── vectordb/
│   └── chroma.sqlite3              # ChromaDB · 161 chunks (P6-F 최종)
├── figures/                        # EDA / SHAP 시각화
└── eda_summary.txt
```

---

## 9. 환경 변수 및 인증

프로젝트 루트의 `.env` 파일에 설정:

```env
# ── OpenSky API (선택 — 익명 접근 가능하나 요청 제한) ────────────────────
OPENSKY_USERNAME=your_username
OPENSKY_PASSWORD=your_password

# ── Kafka ──────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_FLIGHT_POSITION=flight-position
KAFKA_TOPIC_WEATHER_EVENT=weather-event
KAFKA_TOPIC_NOTAM=notam
KAFKA_TOPIC_ATFM=atfm-restriction
KAFKA_TOPIC_ALERT=alert-decision
KAFKA_TOPIC_ACDM=acdm-milestone

# ── Schema Registry (P6-B) ─────────────────────────────────────────────
SCHEMA_REGISTRY_URL=http://localhost:8081
SCHEMA_COMPAT=BACKWARD

# ── METAR 수집 공항 ────────────────────────────────────────────────────
METAR_STATIONS=RKSI,RKSS,RKPC,RKPK,RKTN,RKTU,RKJJ,RKJB
KMA_API_KEY=                # 공공데이터포털에서 발급

# ── FAA SWIM (P5+ 실연동) ─────────────────────────────────────────────
SWIM_BROKER_URL=smf://ems2.swim.faa.gov:55443
SWIM_VPN=SWIM-PROD-01
SWIM_CLIENT_CERT=/etc/swim/client.pem
SWIM_CLIENT_KEY=/etc/swim/client.key
SWIM_TRUST_STORE=/etc/swim/trust/     # c_rehash 형식 디렉토리
SWIM_NOTAM_QUEUE=swim/faa/notam
SWIM_TFM_QUEUE=swim/faa/tfm

# ── 한국공항공사 ACDM ──────────────────────────────────────────────────
KAC_API_KEY=                # 공공데이터포털 신청 대기 중

# ── GPT-4 QA 생성 ──────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...

# ── vLLM 서빙 ──────────────────────────────────────────────────────────
VLLM_BASE_URL=http://localhost:8001/v1
LLM_MODEL_ID=aviation-llm

# ── Iceberg (ADR-004 D3) ───────────────────────────────────────────────
ICEBERG_CATALOG=sql                    # "sql" (dev) | "rest" (학습/staging)
# rest 모드일 때만 필요:
# ICEBERG_CATALOG_URI=http://nessie:19120/iceberg/v1
# ICEBERG_WAREHOUSE_S3=s3://skyops-iceberg/
# AWS_S3_ENDPOINT=http://minio:9000
# AWS_ACCESS_KEY_ID=skyops
# AWS_SECRET_ACCESS_KEY=skyops-dev-only

# ── Serving model path override (ADR-004 D1) ──────────────────────────
SKYOPS_DATA_DIR=                # e.g. /app/data (컨테이너), 비우면 repo layout

# ── MLflow Registry (ADR-004 D4) ──────────────────────────────────────
MLFLOW_TRACKING_URI=            # file:// URI 또는 HTTP mlflow server
REGISTER_R2_THRESHOLD=0.40      # test_r2 ≥ 이 값이면 Staging 자동 승격

# ── OpenTelemetry (ADR-007 D3) ────────────────────────────────────────
OTEL_ENABLED=1
OTEL_OTLP_EXPORTER=1
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAME=skyops-api
# 개별 계측 off:
# OTEL_INSTRUMENT_KAFKA=0
# OTEL_INSTRUMENT_REDIS=0
# OTEL_INSTRUMENT_HTTPX=0

# ── RBAC (ADR-007 D4a) ────────────────────────────────────────────────
SKYOPS_AUTH_ENFORCE=0           # 0 = WARN log only (dev) · 1 = 403 (prod)

# ── Alert Discipline (ADR-006) ────────────────────────────────────────
IF_SCORE_ENTER=-0.15            # hysteresis 진입 (더 엄격)
IF_SCORE_EXIT=-0.05             # hysteresis 탈출 (더 관대)
IF_HYSTERESIS_TTL_SEC=900       # 15 min 무활동 시 state 자동 만료
SUPPRESSION_ENABLED=1           # config/alert_suppression.yaml 활성화

# ── NAS 경량 모드 전용 (Synology / P8 NAS 배포) ───────────────────────
# RAG_RETRIEVE_DISABLED=1       # 800MB 제한에서 bge-m3 로드 금지 (canned topic 응답)
# LLM_MODE=fallback             # vLLM 없으므로 templated 응답
# ICEBERG_ENABLED=0             # NAS 에서는 off
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

## Change Log

- **2026-04-19 (v2.2.0)** · Stage 1–4 완료 반영
  - FAA SWIM / ACDM / Schema Registry / Iceberg / Feast / OpenLineage 섹션 추가
  - NUMERIC_FEATURES 20 → 25 (Rotation 5종), NETWORK_FEATURES 후보 bundle 추가
  - CQR 보정기 + Per-phase IF × 7 + phase classifier 파일 트리 반영
  - TimeSeriesSplit / ChronologicalCutoff 기준 명시 (ADR-004 D1)
  - env 섹션 전면 개정 (SWIM / Iceberg / MLflow / OTel / RBAC / Alert Discipline)
- **2026-04-03** · 10주차 MVP 최초 작성

---

*본 문서는 SkyOps Intelligence 프로젝트의 데이터 수집 전 과정을 기록합니다.*
*문의: doublej.biz01@gmail.com*
