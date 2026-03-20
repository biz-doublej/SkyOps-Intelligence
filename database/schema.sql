-- =============================================================
-- SkyOps Intelligence — PostgreSQL DDL
-- =============================================================

-- ── 확장 ──────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE; -- 시계열 최적화 (선택)

-- ── ENUM 타입 ─────────────────────────────────────────────────
CREATE TYPE event_type_enum AS ENUM (
    'altitude_spike',     -- 고도 급변 (±500ft/30sec)
    'velocity_spike',     -- 속도 이상 (±100knot/1min)
    'route_deviation',    -- 경로 이탈 (10km 이상)
    'ground_proximity'    -- 비정상 저고도 접근
);

CREATE TYPE severity_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- ── 1. airports (공항) ────────────────────────────────────────
CREATE TABLE airports (
    airport_code    VARCHAR(4)   PRIMARY KEY,         -- IATA/ICAO 코드
    airport_name    VARCHAR(100) NOT NULL,
    city            VARCHAR(100),
    country         VARCHAR(100),
    latitude        DECIMAL(9, 6) NOT NULL,
    longitude       DECIMAL(9, 6) NOT NULL,
    timezone        VARCHAR(50)  DEFAULT 'Asia/Seoul'
);

COMMENT ON TABLE airports IS '공항 기본 정보';

-- ── 2. airlines (항공사) ──────────────────────────────────────
CREATE TABLE airlines (
    carrier_code    VARCHAR(3)   PRIMARY KEY,         -- IATA 코드 (예: KE)
    carrier_name    VARCHAR(100) NOT NULL,
    country         VARCHAR(100)
);

COMMENT ON TABLE airlines IS '항공사 기본 정보';

-- ── 3. flights (항공편) ───────────────────────────────────────
CREATE TABLE flights (
    flight_id           BIGSERIAL    PRIMARY KEY,
    callsign            VARCHAR(10),
    icao24              VARCHAR(10),                  -- 항공기 고유 ICAO 24비트 주소
    carrier_code        VARCHAR(3)   REFERENCES airlines(carrier_code),
    origin_airport      VARCHAR(4)   REFERENCES airports(airport_code),
    dest_airport        VARCHAR(4)   REFERENCES airports(airport_code),
    scheduled_dep_time  TIMESTAMPTZ,
    scheduled_arr_time  TIMESTAMPTZ,
    actual_dep_time     TIMESTAMPTZ,
    actual_arr_time     TIMESTAMPTZ,
    dep_delay_min       INT          DEFAULT 0,
    arr_delay_min       INT          DEFAULT 0,
    distance_miles      DECIMAL(8,2),
    flight_date         DATE         NOT NULL,
    created_at          TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX idx_flights_icao24      ON flights(icao24);
CREATE INDEX idx_flights_callsign    ON flights(callsign);
CREATE INDEX idx_flights_flight_date ON flights(flight_date);
CREATE INDEX idx_flights_origin      ON flights(origin_airport);
CREATE INDEX idx_flights_dest        ON flights(dest_airport);

COMMENT ON TABLE flights IS '항공편 스케줄 및 지연 정보';

-- ── 4. flight_positions (실시간 위치) ─────────────────────────
CREATE TABLE flight_positions (
    position_id     BIGSERIAL    PRIMARY KEY,
    icao24          VARCHAR(10)  NOT NULL,
    callsign        VARCHAR(10),
    flight_id       BIGINT       REFERENCES flights(flight_id),
    position_time   TIMESTAMPTZ  NOT NULL,
    latitude        DECIMAL(9,6),
    longitude       DECIMAL(9,6),
    baro_altitude   DECIMAL(8,2),                     -- 기압고도 (m)
    geo_altitude    DECIMAL(8,2),                     -- 지오고도 (m)
    velocity        DECIMAL(7,2),                     -- 속도 (m/s)
    true_track      DECIMAL(6,2),                     -- 진행 방향 (도)
    vertical_rate   DECIMAL(7,2),                     -- 수직 속도 (m/s)
    on_ground       BOOLEAN      DEFAULT FALSE,
    squawk          VARCHAR(4),
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX idx_positions_icao24        ON flight_positions(icao24);
CREATE INDEX idx_positions_time          ON flight_positions(position_time DESC);
CREATE INDEX idx_positions_flight_id     ON flight_positions(flight_id);
CREATE INDEX idx_positions_geo           ON flight_positions(latitude, longitude);

-- TimescaleDB 하이퍼테이블 변환 (TimescaleDB 설치 시)
-- SELECT create_hypertable('flight_positions', 'position_time');

COMMENT ON TABLE flight_positions IS 'OpenSky Network 실시간 항공기 위치 데이터 (30초 폴링)';

-- ── 5. weather_observations (기상 관측) ───────────────────────
CREATE TABLE weather_observations (
    obs_id              BIGSERIAL    PRIMARY KEY,
    airport_code        VARCHAR(4)   REFERENCES airports(airport_code),
    observed_at         TIMESTAMPTZ  NOT NULL,
    wind_speed_knots    DECIMAL(5,1),
    wind_direction_deg  SMALLINT,
    visibility_miles    DECIMAL(5,2),
    ceiling_ft          INT,
    temperature_c       DECIMAL(5,1),
    dewpoint_c          DECIMAL(5,1),
    altimeter_inhg      DECIMAL(6,2),
    precipitation_inch  DECIMAL(5,2) DEFAULT 0,
    raw_metar           TEXT,
    created_at          TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX idx_weather_airport  ON weather_observations(airport_code);
CREATE INDEX idx_weather_time     ON weather_observations(observed_at DESC);

COMMENT ON TABLE weather_observations IS 'METAR 기상 관측 데이터 (NOAA Aviation Weather API)';

-- ── 6. anomaly_events (이상 이벤트) ──────────────────────────
CREATE TABLE anomaly_events (
    event_id            BIGSERIAL       PRIMARY KEY,
    icao24              VARCHAR(10)     NOT NULL,
    flight_id           BIGINT          REFERENCES flights(flight_id),
    position_id         BIGINT          REFERENCES flight_positions(position_id),
    detected_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    event_type          event_type_enum NOT NULL,
    severity            severity_enum   NOT NULL DEFAULT 'LOW',
    latitude            DECIMAL(9,6),
    longitude           DECIMAL(9,6),
    altitude_m          DECIMAL(8,2),
    velocity_ms         DECIMAL(7,2),
    description         TEXT,
    llm_explanation     TEXT,            -- LLM 자연어 설명
    response_procedure  TEXT,            -- LLM 생성 대응 절차
    is_resolved         BOOLEAN         DEFAULT FALSE,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX idx_anomaly_icao24      ON anomaly_events(icao24);
CREATE INDEX idx_anomaly_detected_at ON anomaly_events(detected_at DESC);
CREATE INDEX idx_anomaly_severity    ON anomaly_events(severity);
CREATE INDEX idx_anomaly_type        ON anomaly_events(event_type);
CREATE INDEX idx_anomaly_unresolved  ON anomaly_events(is_resolved) WHERE is_resolved = FALSE;

COMMENT ON TABLE anomaly_events IS 'AI 이상 탐지 결과 및 LLM 설명 저장';

-- ── 초기 데이터: 주요 공항 ────────────────────────────────────
INSERT INTO airports (airport_code, airport_name, city, country, latitude, longitude, timezone) VALUES
    ('RKSI', '인천국제공항',   '인천', '대한민국', 37.4602, 126.4407, 'Asia/Seoul'),
    ('RKSS', '김포국제공항',   '서울', '대한민국', 37.5583, 126.7906, 'Asia/Seoul'),
    ('RKPC', '제주국제공항',   '제주', '대한민국', 33.5113, 126.4930, 'Asia/Seoul'),
    ('RKTN', '대구국제공항',   '대구', '대한민국', 35.8964, 128.6589, 'Asia/Seoul'),
    ('RJTT', '도쿄 하네다공항', '도쿄', '일본',     35.5494, 139.7798, 'Asia/Tokyo'),
    ('ZBAA', '베이징 수도공항', '베이징', '중국',   40.0799, 116.6031, 'Asia/Shanghai')
ON CONFLICT DO NOTHING;

-- ── 초기 데이터: 주요 항공사 ──────────────────────────────────
INSERT INTO airlines (carrier_code, carrier_name, country) VALUES
    ('KE', '대한항공',   '대한민국'),
    ('OZ', '아시아나항공', '대한민국'),
    ('7C', '제주항공',   '대한민국'),
    ('LJ', '진에어',     '대한민국'),
    ('NH', 'ANA',       '일본'),
    ('CA', '중국국제항공', '중국')
ON CONFLICT DO NOTHING;
