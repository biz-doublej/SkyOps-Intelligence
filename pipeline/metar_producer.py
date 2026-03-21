"""
SkyOps Intelligence — METAR Kafka Producer (v3)
================================================
NOAA Aviation Weather API (aviationweather.gov) 에서
실시간 METAR 데이터를 수집하여 Kafka 'weather-event' 토픽으로 전송합니다.

- 인증 불필요 (완전 무료 공개 API)
- 전세계 공항 실시간 METAR 지원
- KMA API는 실시간 데이터 권한 필요 → Phase 3에서 별도 신청 후 교체 예정

API:
  https://aviationweather.gov/api/data/metar?ids=RKSI,RKSS,...&format=json

실행:
    pip install -r requirements.txt
    python metar_producer.py
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

load_dotenv()

# ── 로거 ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("metar_producer.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("MetarProducer")

# ── 설정 ──────────────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_WEATHER_EVENT     = os.getenv("KAFKA_TOPIC_WEATHER_EVENT", "weather-event")
POLL_INTERVAL_SEC       = int(os.getenv("METAR_POLL_INTERVAL_SEC", "1800"))

STATIONS_RAW = os.getenv("METAR_STATIONS", "RKSI,RKSS,RKPC,RKPK,RKTN,RKTU,RKJJ,RKJB")
STATIONS     = [s.strip() for s in STATIONS_RAW.split(",")]

NOAA_METAR_URL = "https://aviationweather.gov/api/data/metar"

AIRPORT_NAMES = {
    "RKSI": "인천국제공항", "RKSS": "김포국제공항",
    "RKPC": "제주국제공항", "RKPK": "김해국제공항",
    "RKTN": "대구국제공항", "RKTU": "청주국제공항",
    "RKJJ": "광주공항",     "RKJB": "무안국제공항",
}

# ── Graceful Shutdown ─────────────────────────────────────────
shutdown_requested = False
def handle_signal(s, f):
    global shutdown_requested
    shutdown_requested = True
    logger.info("종료 신호 수신. 다음 폴링 후 종료합니다...")

signal.signal(signal.SIGINT,  handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


# ── Kafka Producer ────────────────────────────────────────────
def create_producer(retries=5, delay=5) -> KafkaProducer:
    for attempt in range(1, retries + 1):
        try:
            p = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all", retries=3, compression_type="gzip",
            )
            logger.info(f"✅ Kafka 연결 성공 — {KAFKA_BOOTSTRAP_SERVERS}")
            return p
        except NoBrokersAvailable:
            logger.warning(f"Kafka 연결 실패 ({attempt}/{retries}). {delay}초 후 재시도...")
            time.sleep(delay)
    logger.error("Kafka 브로커 연결 실패.")
    sys.exit(1)


# ── NOAA METAR API 호출 ───────────────────────────────────────
def fetch_metar_noaa() -> dict:
    """
    NOAA Aviation Weather API에서 전체 공항 METAR를 한 번에 가져옵니다.
    반환: {icao: {parsed metar fields}}
    """
    params = {
        "ids":    ",".join(STATIONS),
        "format": "json",
        "hours":  2,      # 최근 2시간 데이터
        "taf":    "false",
    }
    result = {}
    try:
        resp = requests.get(NOAA_METAR_URL, params=params, timeout=15)
        resp.raise_for_status()
        records = resp.json()  # list of METAR objects

        # 공항별 가장 최신 레코드만 보관
        for rec in records:
            icao = rec.get("icaoId", "").upper()
            if icao not in STATIONS:
                continue
            # 기존 레코드보다 최신이면 교체
            if icao not in result or rec.get("reportTime", "") > result[icao].get("observed_at", ""):
                result[icao] = parse_noaa_record(rec)

        logger.info(f"NOAA API: {len(result)}/{len(STATIONS)}개 공항 수신")

    except requests.exceptions.RequestException as e:
        logger.error(f"NOAA METAR 요청 실패: {e}")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"NOAA METAR 파싱 실패: {e}")

    return result


def parse_noaa_record(rec: dict) -> dict:
    """NOAA JSON 레코드를 SkyOps 표준 weather-event 메시지로 변환."""
    def safe_float(val) -> Optional[float]:
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    icao = rec.get("icaoId", "").upper()

    # 구름 최저층 운고 (ft) — clouds 배열에서 첫 번째 유효층
    ceiling_ft = None
    clouds = rec.get("clouds", [])
    if isinstance(clouds, list):
        for layer in clouds:
            cover = layer.get("cover", "")
            base  = layer.get("base")
            if cover in ("BKN", "OVC", "FEW", "SCT") and base is not None:
                ceiling_ft = safe_float(base)
                break

    return {
        "source":             "NOAA",
        "icao":               icao,
        "airport_name":       AIRPORT_NAMES.get(icao, icao),
        "observed_at":        rec.get("reportTime"),
        "raw_metar":          rec.get("rawOb"),
        # 바람
        "wind_direction_deg": safe_float(rec.get("wdir")),
        "wind_speed_knots":   safe_float(rec.get("wspd")),
        "wind_gust_knots":    safe_float(rec.get("wgst")),
        # 시정 (miles → m 변환, safe_float 결과가 None일 수 있으므로 별도 처리)
        "visibility_m":       round(_v * 1609.34, 1)
                              if (_v := safe_float(rec.get("visib"))) is not None else None,
        # 기온/이슬점
        "temperature_c":      safe_float(rec.get("temp")),
        "dewpoint_c":         safe_float(rec.get("dewp")),
        # 기압 (inHg → hPa 변환)
        "altimeter_inhg":     safe_float(rec.get("altim")),
        "pressure_hpa":       round(_a * 33.8639, 1)
                              if (_a := safe_float(rec.get("altim"))) is not None else None,
        # 구름
        "ceiling_ft":         ceiling_ft,
        "cloud_layers":       clouds,
        # 날씨현상
        "present_weather":    rec.get("wxString"),
        "flight_category":    rec.get("fltcat"),   # VFR / MVFR / IFR / LIFR
        # 메타
        "fetched_at_iso":     datetime.now(tz=timezone.utc).isoformat(),
    }


# ── 폴링 & 전송 ───────────────────────────────────────────────
def poll_and_send(producer: KafkaProducer) -> int:
    metar_data = fetch_metar_noaa()
    sent_count = 0

    for icao in STATIONS:
        if icao in metar_data:
            message = metar_data[icao]
            status  = "✅"
        else:
            # 데이터 없음 → 빈 메시지라도 전송 (수신 쪽에서 처리)
            message = {
                "source": "NOAA", "icao": icao,
                "airport_name": AIRPORT_NAMES.get(icao, icao),
                "fetched_at_iso": datetime.now(tz=timezone.utc).isoformat(),
            }
            status = "⚠️ "

        producer.send(
            TOPIC_WEATHER_EVENT, key=icao, value=message,
        ).add_errback(lambda exc: logger.error(f"Kafka 전송 실패: {exc}"))

        logger.info(
            f"{status} [{icao}] {AIRPORT_NAMES.get(icao, '')} | "
            f"기온:{message.get('temperature_c')}℃  "
            f"풍속:{message.get('wind_speed_knots')}kt  "
            f"시정:{message.get('visibility_m')}m  "
            f"범주:{message.get('flight_category', '-')}"
        )
        sent_count += 1

    producer.flush()
    return sent_count


# ── 메인 루프 ─────────────────────────────────────────────────
def run():
    logger.info("=" * 58)
    logger.info("  SkyOps Intelligence — METAR Kafka Producer v3 (NOAA)")
    logger.info("=" * 58)
    logger.info(f"  브로커    : {KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"  토픽      : {TOPIC_WEATHER_EVENT}")
    logger.info(f"  폴링 주기 : {POLL_INTERVAL_SEC}초 ({POLL_INTERVAL_SEC//60}분)")
    logger.info(f"  공항      : {', '.join(STATIONS)}")
    logger.info(f"  데이터원  : NOAA Aviation Weather (aviationweather.gov)")
    logger.info("=" * 58)

    producer   = create_producer()
    poll_count = 0
    total_sent = 0

    try:
        while not shutdown_requested:
            poll_start  = time.time()
            poll_count += 1
            logger.info(f"[폴링 #{poll_count}] 수집 시작...")

            sent        = poll_and_send(producer)
            total_sent += sent
            elapsed     = time.time() - poll_start

            logger.info(
                f"[폴링 #{poll_count}] 완료 — {sent}건 전송, "
                f"소요 {elapsed:.1f}초 | 누적: {total_sent}건"
            )

            sleep_time = max(0, POLL_INTERVAL_SEC - (time.time() - poll_start))
            if not shutdown_requested and sleep_time > 0:
                next_t = datetime.now() + timedelta(seconds=sleep_time)
                logger.info(f"다음 폴링: {next_t.strftime('%H:%M:%S')}")
                time.sleep(sleep_time)

    finally:
        producer.flush()
        producer.close()
        logger.info(f"정상 종료 — 총 폴링 {poll_count}회 | 총 전송 {total_sent}건")


if __name__ == "__main__":
    run()
