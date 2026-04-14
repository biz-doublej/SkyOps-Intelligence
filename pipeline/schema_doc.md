# SkyOps Intelligence — Kafka 토픽 데이터 스키마 문서

> 초판: 2026-03-21  
> **v2.0**: 2026-04-15 (P4+ Sprint) — `atfm-restriction`, `notam` 토픽 추가
> 전체 Canonical Event Model은 [docs/event_model.md](../docs/event_model.md) 참고

---

## 1. `flight-position` 토픽

**설명**: OpenSky Network ADS-B 수신 항공기 실시간 위치 데이터  
**수집 주기**: 30초  
**파티션**: 3 (파티션 키: `icao24`)  
**Producer**: `pipeline/opensky_producer.py`

| 필드명 | 타입 | 단위 | 설명 | 예시 |
|---|---|---|---|---|
| `icao24` | string | - | 항공기 ICAO 24비트 고유 주소 | `"71c007"` |
| `callsign` | string\|null | - | 항공편 콜사인 | `"KAL601"` |
| `origin_country` | string | - | 항공기 등록 국가 | `"Republic of Korea"` |
| `latitude` | float | 도(°) | 위도 (-90 ~ 90) | `37.566` |
| `longitude` | float | 도(°) | 경도 (-180 ~ 180) | `126.795` |
| `baro_altitude` | float\|null | m | 기압 고도 | `9448.8` |
| `geo_altitude` | float\|null | m | 지오이드 기준 고도 | `9432.0` |
| `on_ground` | boolean | - | 지상 여부 | `false` |
| `velocity` | float\|null | m/s | 지표면 기준 속도 | `234.55` |
| `true_track` | float\|null | 도(°) | 진행 방향 (북=0, 시계방향) | `157.83` |
| `vertical_rate` | float\|null | m/s | 수직 속도 (양수=상승) | `14.96` |
| `squawk` | string\|null | - | 트랜스폰더 스쿼크 코드 | `"7050"` |
| `position_source` | int | - | 위치 소스 (0=ADS-B, 1=ASTERIX, 2=MLAT, 3=FLARM) | `0` |
| `time_position` | int | Unix timestamp | 위치 측정 시각 (UTC) | `1774024341` |
| `last_contact` | int | Unix timestamp | 마지막 수신 시각 (UTC) | `1774024341` |
| `fetched_at` | int | Unix timestamp | API 호출 시각 (UTC) | `1774024342` |
| `fetched_at_iso` | string | ISO 8601 | API 호출 시각 (UTC, 문자열) | `"2026-03-20T16:32:22+00:00"` |

**이상 탐지 활용 필드**:
- `baro_altitude` + `vertical_rate` → 고도 급변 감지 (±500ft/30sec)
- `velocity` → 속도 이상 감지 (±100knot/1min)
- `latitude` + `longitude` + `true_track` → 경로 이탈 감지 (10km 이상)

---

## 2. `weather-event` 토픽

**설명**: NOAA Aviation Weather API 기반 공항 METAR 기상 관측 데이터  
**수집 주기**: 1800초 (30분)  
**파티션**: 3 (파티션 키: `icao`)  
**Producer**: `pipeline/metar_producer.py`  
**데이터 원천**: NOAA Aviation Weather (aviationweather.gov)

| 필드명 | 타입 | 단위 | 설명 | 예시 |
|---|---|---|---|---|
| `source` | string | - | 데이터 출처 | `"NOAA"` |
| `icao` | string | - | 공항 ICAO 코드 | `"RKSI"` |
| `airport_name` | string | - | 공항 한글명 | `"인천국제공항"` |
| `observed_at` | string\|null | ISO 8601 UTC | METAR 관측 시각 | `"2026-03-21T05:00:00Z"` |
| `raw_metar` | string\|null | - | METAR 원문 전문 | `"METAR RKSI 210500Z 27007KT..."` |
| `wind_direction_deg` | float\|null | 도(°) | 풍향 (진북 기준, 0~360) | `270.0` |
| `wind_speed_knots` | float\|null | knot | 평균 풍속 | `7.0` |
| `wind_gust_knots` | float\|null | knot | 돌풍 풍속 (없으면 null) | `15.0` |
| `visibility_m` | float\|null | m | 수평 시정 (miles→m 변환) | `8996.2` |
| `temperature_c` | float\|null | ℃ | 기온 | `11.0` |
| `dewpoint_c` | float\|null | ℃ | 이슬점 온도 | `8.0` |
| `altimeter_inhg` | float\|null | inHg | 기압계 수치 (원본) | `29.92` |
| `pressure_hpa` | float\|null | hPa | 기압 (inHg→hPa 변환) | `1013.2` |
| `ceiling_ft` | float\|null | ft | 최저 운고 (BKN/OVC 기준) | `2500.0` |
| `cloud_layers` | array | - | 구름 층 정보 배열 | `[{"cover":"FEW","base":2500}]` |
| `present_weather` | string\|null | - | 현재 날씨 현상 코드 | `"-RA"` (약한 비) |
| `flight_category` | string\|null | - | 비행 기상 등급 | `"VFR"` / `"IFR"` / `"MVFR"` / `"LIFR"` |
| `fetched_at_iso` | string | ISO 8601 | API 호출 시각 (UTC) | `"2026-03-21T05:53:10+00:00"` |

**flight_category 기준**:

| 등급 | 시정 | 운고 | 의미 |
|---|---|---|---|
| `VFR` | > 5 SM | > 3000 ft | 시계 비행 (정상) |
| `MVFR` | 3~5 SM | 1000~3000 ft | 한계 시계 비행 |
| `IFR` | 1~3 SM | 500~1000 ft | 계기 비행 필요 |
| `LIFR` | < 1 SM | < 500 ft | 저시정 계기 비행 (위험) |

---

## 3. `gate-event` 토픽

**설명**: 게이트 이벤트 (출발·도착 상태 변경)  
**수집 주기**: 미구현 (3주차 예정)  
**파티션**: 3  
**상태**: ⏳ 구현 예정

| 필드명 | 타입 | 단위 | 설명 |
|---|---|---|---|
| `flight_id` | string | - | 항공편 ID |
| `callsign` | string | - | 콜사인 |
| `airport_icao` | string | - | 공항 ICAO 코드 |
| `gate` | string | - | 게이트 번호 |
| `event_type` | string | - | `DEPARTURE` / `ARRIVAL` / `DELAY` / `CANCEL` |
| `scheduled_time` | string | ISO 8601 | 예정 시각 |
| `actual_time` | string\|null | ISO 8601 | 실제 시각 |
| `delay_min` | int\|null | 분 | 지연 시간 |
| `timestamp` | string | ISO 8601 | 이벤트 발생 시각 |

---

## 4. `atfm-restriction` 토픽 (P4+ · 2026-04-15)

**설명**: Air Traffic Flow Management 제약 이벤트 — GDP, departure slot, rerouting, closure
**현재 상태**: 🟡 Mock producer (`pipeline/atfm_producer.py`, ATFM_MODE=mock)
**Producer (mock)**: 60초 간격 샘플 이벤트 발행
**Producer (real, P5+ 이연)**: EUROCONTROL NM B2B / FAA CSS-Wx 연동
**Partition key**: `restriction_id`

자세한 스키마는 `docs/event_model.md` 2.5 ATFMRestrictionEvent 참고.

주요 필드:
- `restriction_id`, `restriction_type` (GROUND_DELAY_PROGRAM / DEPARTURE_SLOT / SPEED_RESTRICTION / ALTITUDE_RESTRICTION / REROUTING / CLOSURE)
- `affected_airports`, `affected_airspace`
- `reason` (WEATHER / TRAFFIC_CONGESTION / RUNWAY_CLOSURE / SECURITY / EQUIPMENT_OUTAGE)
- `effective_from`, `effective_until`, `expected_duration_min`, `delay_expectation_min`
- `issuing_authority` (FAA / EUROCONTROL / KAC / CAAC)
- `initiative_name`

---

## 5. `notam` 토픽 (P4+ · 2026-04-15)

**설명**: NOTAM (Notice to Airmen) 이벤트 스트림
**현재 상태**: 🟡 Mock producer (`pipeline/notam_producer.py`, NOTAM_MODE=mock)
**Producer (mock)**: 120초 간격 샘플 발행
**Producer (real, P5+ 이연)**: FAA NOTAM API / KAC AIS 연동
**Partition key**: `notam_id`

자세한 스키마는 `docs/event_model.md` 2.6 NOTAMEvent 참고.

주요 필드:
- `notam_id`, `notam_series` (A/B/C/D/E/F)
- `issue_date`, `effective_from`, `effective_until`
- `affected_location` (type: AIRPORT/RUNWAY/TAXIWAY/WAYPOINT/AIRSPACE/NAVAID + identifier)
- `notam_class` (AD / AS / NAV / COM / FDC)
- `traffic_direction` (INBOUND / OUTBOUND / BOTH / OVERFLIGHT)
- `text_raw`, `text_en`, `text_ko` (LLM 번역)
- `operational_impact_score` (0.0 ~ 1.0)

---

## 공통 규칙

- 모든 타임스탬프: **UTC 기준**
- `null` 값: 해당 센서/필드 데이터 미수신 또는 해당 없음
- 파티션 키: 항공기 `icao24` 또는 공항 `icao`, 제약 이벤트는 `restriction_id` / `notam_id`
- 메시지 압축: **gzip**
- 직렬화: **UTF-8 JSON**
- 모든 이벤트는 `schema_version` 필드 포함 (2026-04-15 현재 "2.0")
- Mock 이벤트는 `_mock: true` 플래그로 식별 (P5에서 제거 예정)
