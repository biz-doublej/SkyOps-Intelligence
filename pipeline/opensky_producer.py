"""
SkyOps Intelligence — OpenSky API Kafka Producer
================================================
OpenSky Network ADS-B 데이터를 30초마다 폴링하여
Kafka 'flight-position' 토픽으로 전송합니다.

실행 방법:
    pip install -r requirements.txt
    python opensky_producer.py

전제 조건:
    - Docker Compose로 Kafka 클러스터 실행 중 (docker compose up -d)
    - .env 파일에 OPENSKY_USERNAME, OPENSKY_PASSWORD 입력
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

# ── 환경 변수 로드 ────────────────────────────────────────────
load_dotenv()

# ── 로거 설정 ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("producer.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("OpenSkyProducer")

# ── 설정 ──────────────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_FLIGHT_POSITION   = os.getenv("KAFKA_TOPIC_FLIGHT_POSITION", "flight-position")
OPENSKY_USERNAME        = os.getenv("OPENSKY_USERNAME", "")
OPENSKY_PASSWORD        = os.getenv("OPENSKY_PASSWORD", "")
POLL_INTERVAL_SEC       = int(os.getenv("OPENSKY_POLL_INTERVAL_SEC", "30"))

# 한반도 + 주변 바운딩 박스
LAT_MIN = float(os.getenv("OPENSKY_LAT_MIN", "33.0"))
LAT_MAX = float(os.getenv("OPENSKY_LAT_MAX", "38.9"))
LON_MIN = float(os.getenv("OPENSKY_LON_MIN", "124.0"))
LON_MAX = float(os.getenv("OPENSKY_LON_MAX", "130.0"))

OPENSKY_BASE_URL = "https://opensky-network.org/api"

# OpenSky states/all 응답 필드 순서
STATE_FIELDS = [
    "icao24", "callsign", "origin_country", "time_position",
    "last_contact", "longitude", "latitude", "baro_altitude",
    "on_ground", "velocity", "true_track", "vertical_rate",
    "sensors", "geo_altitude", "squawk", "spi", "position_source",
]

# ── Graceful Shutdown ─────────────────────────────────────────
shutdown_requested = False

def handle_signal(signum, frame):
    global shutdown_requested
    logger.info(f"종료 신호 수신 (signal={signum}). 다음 폴링 후 종료합니다...")
    shutdown_requested = True

signal.signal(signal.SIGINT,  handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


# ── Kafka Producer 생성 ───────────────────────────────────────
def create_producer(retries: int = 5, delay: int = 5) -> KafkaProducer:
    """Kafka 브로커 연결이 될 때까지 재시도합니다."""
    for attempt in range(1, retries + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",                   # 모든 레플리카 확인 후 ack
                retries=3,                    # 전송 실패 시 재시도
                max_in_flight_requests_per_connection=1,
                compression_type="gzip",      # 메시지 압축
            )
            logger.info(f"✅ Kafka 연결 성공 — {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except NoBrokersAvailable:
            logger.warning(f"Kafka 브로커 연결 실패 ({attempt}/{retries}). {delay}초 후 재시도...")
            time.sleep(delay)
    logger.error("Kafka 브로커에 연결할 수 없습니다. Docker Compose 실행 여부를 확인하세요.")
    sys.exit(1)


# ── OpenSky API 호출 ──────────────────────────────────────────
def fetch_flight_states() -> Optional[dict]:
    """OpenSky Network states/all 엔드포인트 호출."""
    params = {
        "lamin": LAT_MIN, "lomin": LON_MIN,
        "lamax": LAT_MAX, "lomax": LON_MAX,
    }
    auth = (OPENSKY_USERNAME, OPENSKY_PASSWORD) if OPENSKY_USERNAME else None

    try:
        resp = requests.get(
            f"{OPENSKY_BASE_URL}/states/all",
            params=params,
            auth=auth,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    except requests.exceptions.HTTPError as e:
        if resp.status_code == 429:
            logger.warning("⚠️  요청 한도 초과(429). 다음 폴링까지 대기합니다.")
        elif resp.status_code == 401:
            logger.error("❌ 인증 실패(401). .env의 OPENSKY_USERNAME/PASSWORD를 확인하세요.")
        else:
            logger.error(f"HTTP 오류: {e}")
        return None

    except requests.exceptions.Timeout:
        logger.warning("⏱️  OpenSky API 요청 타임아웃.")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"네트워크 오류: {e}")
        return None


# ── 메시지 변환 ───────────────────────────────────────────────
def state_to_message(state: list, fetch_time: int) -> dict:
    """OpenSky 상태 배열을 Kafka 메시지 딕셔너리로 변환."""
    flight = dict(zip(STATE_FIELDS, state))
    return {
        # 식별자
        "icao24":          flight.get("icao24"),
        "callsign":        (flight.get("callsign") or "").strip() or None,
        "origin_country":  flight.get("origin_country"),
        # 위치
        "latitude":        flight.get("latitude"),
        "longitude":       flight.get("longitude"),
        "baro_altitude":   flight.get("baro_altitude"),
        "geo_altitude":    flight.get("geo_altitude"),
        "on_ground":       flight.get("on_ground"),
        # 운동
        "velocity":        flight.get("velocity"),
        "true_track":      flight.get("true_track"),
        "vertical_rate":   flight.get("vertical_rate"),
        # 기타
        "squawk":          flight.get("squawk"),
        "position_source": flight.get("position_source"),
        # 타임스탬프
        "time_position":   flight.get("time_position"),
        "last_contact":    flight.get("last_contact"),
        "fetched_at":      fetch_time,
        "fetched_at_iso":  datetime.fromtimestamp(fetch_time, tz=timezone.utc).isoformat(),
    }


# ── 전송 콜백 ─────────────────────────────────────────────────
def on_send_success(record_metadata):
    logger.debug(
        f"✉️  전송 완료 — topic={record_metadata.topic} "
        f"partition={record_metadata.partition} offset={record_metadata.offset}"
    )

def on_send_error(exc):
    logger.error(f"❌ 전송 실패: {exc}")


# ── 메인 루프 ─────────────────────────────────────────────────
def run():
    logger.info("=" * 55)
    logger.info("  SkyOps Intelligence — OpenSky Kafka Producer 시작")
    logger.info("=" * 55)
    logger.info(f"  Kafka 브로커  : {KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"  토픽          : {TOPIC_FLIGHT_POSITION}")
    logger.info(f"  폴링 주기     : {POLL_INTERVAL_SEC}초")
    logger.info(f"  바운딩 박스   : lat({LAT_MIN}~{LAT_MAX}), lon({LON_MIN}~{LON_MAX})")
    logger.info(f"  인증 모드     : {'인증' if OPENSKY_USERNAME else '익명(제한적)'}")
    logger.info("=" * 55)

    producer = create_producer()

    poll_count   = 0
    total_sent   = 0
    total_errors = 0

    try:
        while not shutdown_requested:
            poll_start = time.time()
            poll_count += 1

            logger.info(f"[폴링 #{poll_count}] OpenSky API 호출 중...")
            data = fetch_flight_states()

            if data:
                states     = data.get("states") or []
                fetch_time = data.get("time", int(time.time()))
                sent_count = 0

                for state in states:
                    if state[6] is None or state[5] is None:  # 위도/경도 없으면 스킵
                        continue

                    message = state_to_message(state, fetch_time)
                    key     = message["icao24"]  # icao24 기준 파티셔닝

                    producer.send(
                        TOPIC_FLIGHT_POSITION,
                        key=key,
                        value=message,
                    ).add_callback(on_send_success).add_errback(on_send_error)

                    sent_count += 1

                producer.flush()
                total_sent += sent_count

                elapsed = time.time() - poll_start
                logger.info(
                    f"[폴링 #{poll_count}] 완료 — 항공기 {len(states)}대 탐지, "
                    f"{sent_count}건 전송, 소요 {elapsed:.2f}초 | 누적 전송: {total_sent}건"
                )
            else:
                total_errors += 1
                logger.warning(f"[폴링 #{poll_count}] 데이터 없음 (누적 오류: {total_errors}회)")

            # 다음 폴링까지 대기 (이미 소요된 시간 제외)
            sleep_time = max(0, POLL_INTERVAL_SEC - (time.time() - poll_start))
            if not shutdown_requested and sleep_time > 0:
                logger.info(f"다음 폴링까지 {sleep_time:.1f}초 대기...")
                time.sleep(sleep_time)

    finally:
        logger.info("Producer를 종료합니다...")
        producer.flush()
        producer.close()
        logger.info(
            f"정상 종료 — 총 폴링 {poll_count}회 | "
            f"총 전송 {total_sent}건 | 오류 {total_errors}회"
        )


if __name__ == "__main__":
    run()
