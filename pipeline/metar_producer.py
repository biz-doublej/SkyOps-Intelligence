"""
SkyOps Intelligence — KMA METAR Kafka Producer
===============================================
기상청 API Hub (apihub.kma.go.kr) 에서 METAR 기상 데이터를 수집하여
Kafka 'weather-event' 토픽으로 전송합니다.

사용 API:
  1. METAR/SPECI 조회   — AmmIwxxmService/getMetar  (구조화 XML/JSON)
  2. 항공통계자료 조회  — kma_air_tm.php             (디코딩 기상 테이블)

실행 방법:
    pip install -r requirements.txt
    python metar_producer.py

전제 조건:
    - docker compose up -d (Kafka 실행 중)
    - .env 파일에 KMA_AUTH_KEY 입력
"""

import json
import logging
import os
import re
import signal
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# ── 환경 변수 로드 ────────────────────────────────────────────
load_dotenv()

# ── 로거 설정 ─────────────────────────────────────────────────
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
KAFKA_BOOTSTRAP_SERVERS  = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_WEATHER_EVENT      = os.getenv("KAFKA_TOPIC_WEATHER_EVENT", "weather-event")
KMA_AUTH_KEY             = os.getenv("KMA_AUTH_KEY", "")
KMA_METAR_URL            = os.getenv("KMA_METAR_URL",
    "https://apihub.kma.go.kr/api/typ02/openApi/AmmIwxxmService/getMetar")
KMA_AIRTM_URL            = os.getenv("KMA_AIRTM_URL",
    "https://apihub.kma.go.kr/api/typ01/url/kma_air_tm.php")
POLL_INTERVAL_SEC        = int(os.getenv("METAR_POLL_INTERVAL_SEC", "1800"))

# 수집 대상 공항 목록
STATIONS_RAW = os.getenv("METAR_STATIONS", "RKSI,RKSS,RKPC,RKPK,RKTN,RKTU,RKJJ,RKJB")
STATIONS = [s.strip() for s in STATIONS_RAW.split(",")]

# 공항 한글명 매핑
AIRPORT_NAMES = {
    "RKSI": "인천국제공항",
    "RKSS": "김포국제공항",
    "RKPC": "제주국제공항",
    "RKPK": "김해국제공항",
    "RKTN": "대구국제공항",
    "RKTU": "청주국제공항",
    "RKJJ": "광주공항",
    "RKJB": "무안국제공항",
    "RKNY": "양양국제공항",
    "RKPS": "사천공항",
    "RKPU": "울산공항",
    "RKJY": "여수공항",
}

# IWXXM 네임스페이스
NS = {
    "iwxxm": "http://icao.int/iwxxm/3.0",
    "om":    "http://www.opengis.net/om/2.0",
    "sams":  "http://www.opengis.net/samplingSpatial/2.0",
    "gml":   "http://www.opengis.net/gml/3.2",
}

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
    for attempt in range(1, retries + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
                compression_type="gzip",
            )
            logger.info(f"✅ Kafka 연결 성공 — {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except NoBrokersAvailable:
            logger.warning(f"Kafka 연결 실패 ({attempt}/{retries}). {delay}초 후 재시도...")
            time.sleep(delay)
    logger.error("Kafka 브로커에 연결할 수 없습니다.")
    sys.exit(1)


# ── API 1: METAR/SPECI 조회 (IWXXM XML) ──────────────────────
def fetch_metar_iwxxm(icao: str) -> Optional[dict]:
    """기상청 METAR/SPECI IWXXM XML을 가져와 파싱합니다."""
    params = {
        "pageNo":    1,
        "numOfRows": 1,
        "dataType":  "XML",
        "icao":      icao,
        "authKey":   KMA_AUTH_KEY,
    }
    try:
        resp = requests.get(KMA_METAR_URL, params=params, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        result_code = root.findtext(".//resultCode", "")
        if result_code != "00":
            result_msg = root.findtext(".//resultMsg", "")
            logger.warning(f"[{icao}] API 오류 — code={result_code}, msg={result_msg}")
            return None

        # METAR 전문 텍스트
        msg_text = root.findtext(".//msgText", "").strip()

        # IWXXM 필드 파싱 (네임스페이스 포함)
        def find_val(tag: str, attr: str = "uom") -> Optional[str]:
            el = root.find(f".//{tag}", NS)
            if el is None:
                return None
            return el.get(attr) or el.text

        def find_text(tag: str) -> Optional[str]:
            el = root.find(f".//{tag}", NS)
            return el.text.strip() if el is not None and el.text else None

        # 관측 시각
        phenomenon_time = find_text("om:phenomenonTime") or \
                          root.findtext(".//om:phenomenonTime", namespaces=NS)

        # 기상 요소
        air_temp_el  = root.find(".//iwxxm:airTemperature",      NS)
        dewp_el      = root.find(".//iwxxm:dewpointTemperature",  NS)
        qnh_el       = root.find(".//iwxxm:qnh",                  NS)
        wind_dir_el  = root.find(".//iwxxm:meanWindDirection",     NS)
        wind_spd_el  = root.find(".//iwxxm:meanWindSpeed",         NS)
        gust_el      = root.find(".//iwxxm:windGustSpeed",         NS)
        vis_el       = root.find(".//iwxxm:AerodromeHorizontalVisibility", NS)

        def safe_float(el) -> Optional[float]:
            if el is not None and el.text:
                try:
                    return float(el.text)
                except ValueError:
                    return None
            return None

        return {
            "source":        "KMA_METAR",
            "icao":          icao,
            "airport_name":  AIRPORT_NAMES.get(icao, icao),
            "observed_at":   phenomenon_time,
            "raw_metar":     msg_text,
            # 기상 요소
            "temperature_c": safe_float(air_temp_el),
            "dewpoint_c":    safe_float(dewp_el),
            "pressure_hpa":  safe_float(qnh_el),
            "wind_direction_deg":  safe_float(wind_dir_el),
            "wind_speed_knots":    safe_float(wind_spd_el),
            "wind_gust_knots":     safe_float(gust_el),
            "visibility_m":        safe_float(vis_el),
            "fetched_at_iso": datetime.now(tz=timezone.utc).isoformat(),
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"[{icao}] METAR 요청 실패: {e}")
        return None
    except ET.ParseError as e:
        logger.error(f"[{icao}] XML 파싱 실패: {e}")
        return None


# ── API 2: 항공통계자료 조회 (디코딩 기상 테이블) ─────────────
def fetch_airtm(icao_list: list) -> dict:
    """
    kma_air_tm.php 로 최근 1시간 항공 기상 테이블을 가져옵니다.
    반환값: {icao: {WD, WS, VS, TA, TD, ...}} 딕셔너리
    """
    # ICAO → 지점번호 매핑 (KMA 내부 번호)
    ICAO_TO_STN = {
        "RKSI": "112", "RKSS": "108", "RKPC": "184",
        "RKPK": "159", "RKTN": "143", "RKTU": "137",
        "RKJJ": "156", "RKJB": "168",
    }

    now_utc  = datetime.now(timezone.utc)
    tm2      = now_utc.strftime("%Y%m%d%H%M")
    tm1      = (now_utc - timedelta(hours=2)).strftime("%Y%m%d%H%M")
    stns     = ":".join(ICAO_TO_STN[c] for c in icao_list if c in ICAO_TO_STN)

    if not stns:
        return {}

    params = {
        "tm1":     tm1,
        "tm2":     tm2,
        "stn":     stns,
        "help":    0,
        "authKey": KMA_AUTH_KEY,
    }
    result = {}
    try:
        resp = requests.get(KMA_AIRTM_URL, params=params, timeout=15)
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()

        # 역방향 ICAO 매핑
        STN_TO_ICAO = {v: k for k, v in ICAO_TO_STN.items()}
        header = None

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                # 헤더 줄 파싱
                if "TM" in line:
                    header = re.split(r"\s+", line.lstrip("#").strip())
                continue
            if header is None:
                continue

            parts = re.split(r"\s+", line)
            if len(parts) < len(header):
                continue

            row = dict(zip(header, parts))
            stn = row.get("STN", "")
            icao = STN_TO_ICAO.get(stn)
            if not icao:
                continue

            def to_float(val) -> Optional[float]:
                try:
                    f = float(val)
                    return None if f in (-9999.0, -999.0, 9999.0) else f
                except (ValueError, TypeError):
                    return None

            result[icao] = {
                "wind_direction_deg": to_float(row.get("WD")),
                "wind_speed_knots":   to_float(row.get("WS")),
                "wind_gust_knots":    to_float(row.get("GST")),
                "visibility_m":       to_float(row.get("VS")),
                "temperature_c":      to_float(row.get("TA")),
                "dewpoint_c":         to_float(row.get("TD")),
                "humidity_pct":       to_float(row.get("HM")),
                "pressure_hpa":       to_float(row.get("PA")),
                "pressure_sea_hpa":   to_float(row.get("PS")),
                "precipitation_mm":   to_float(row.get("RN")),
                "ceiling_ft":         to_float(row.get("CH1")),
                "cloud_cover_oktas":  to_float(row.get("CA1")),
                "observed_at_kst":    row.get("TM"),
            }

    except requests.exceptions.RequestException as e:
        logger.warning(f"항공통계자료 요청 실패: {e}")
    except Exception as e:
        logger.warning(f"항공통계자료 파싱 실패: {e}")

    return result


# ── 메시지 병합 & 전송 ────────────────────────────────────────
def poll_and_send(producer: KafkaProducer) -> int:
    """전체 공항 METAR 수집 후 Kafka로 전송. 전송 건수 반환."""
    sent_count = 0

    # API 2: 전체 공항 통계 한 번에 조회
    airtm_data = fetch_airtm(STATIONS) if KMA_AUTH_KEY else {}

    for icao in STATIONS:
        # API 1: METAR IWXXM (원문 + 구조화)
        metar = fetch_metar_iwxxm(icao) if KMA_AUTH_KEY else None

        if metar is None:
            metar = {
                "source":       "KMA_AIRTM",
                "icao":         icao,
                "airport_name": AIRPORT_NAMES.get(icao, icao),
                "raw_metar":    None,
                "fetched_at_iso": datetime.now(tz=timezone.utc).isoformat(),
            }

        # API 2 데이터로 보완
        if icao in airtm_data:
            for k, v in airtm_data[icao].items():
                if metar.get(k) is None and v is not None:
                    metar[k] = v

        # 위치/메타 추가
        metar["fetched_at_iso"] = datetime.now(tz=timezone.utc).isoformat()

        producer.send(
            TOPIC_WEATHER_EVENT,
            key=icao,
            value=metar,
        ).add_errback(lambda exc: logger.error(f"Kafka 전송 실패: {exc}"))

        logger.debug(
            f"[{icao}] {AIRPORT_NAMES.get(icao, '')} — "
            f"기온:{metar.get('temperature_c')}℃ "
            f"풍속:{metar.get('wind_speed_knots')}kt "
            f"시정:{metar.get('visibility_m')}m"
        )
        sent_count += 1
        time.sleep(0.3)  # API 부하 방지

    producer.flush()
    return sent_count


# ── 메인 루프 ─────────────────────────────────────────────────
def run():
    if not KMA_AUTH_KEY:
        logger.error(
            "❌ KMA_AUTH_KEY 가 설정되지 않았습니다.\n"
            "   .env 파일에 KMA_AUTH_KEY=<인증키> 를 입력하세요.\n"
            "   발급: https://apihub.kma.go.kr/"
        )
        sys.exit(1)

    logger.info("=" * 55)
    logger.info("  SkyOps Intelligence — KMA METAR Kafka Producer 시작")
    logger.info("=" * 55)
    logger.info(f"  Kafka 브로커  : {KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"  토픽          : {TOPIC_WEATHER_EVENT}")
    logger.info(f"  폴링 주기     : {POLL_INTERVAL_SEC}초 ({POLL_INTERVAL_SEC//60}분)")
    logger.info(f"  수집 공항     : {', '.join(STATIONS)}")
    logger.info("=" * 55)

    producer    = create_producer()
    poll_count  = 0
    total_sent  = 0

    try:
        while not shutdown_requested:
            poll_start  = time.time()
            poll_count += 1

            logger.info(f"[폴링 #{poll_count}] {len(STATIONS)}개 공항 METAR 수집 시작...")
            sent = poll_and_send(producer)
            total_sent += sent

            elapsed = time.time() - poll_start
            logger.info(
                f"[폴링 #{poll_count}] 완료 — {sent}건 전송, "
                f"소요 {elapsed:.1f}초 | 누적 전송: {total_sent}건"
            )

            sleep_time = max(0, POLL_INTERVAL_SEC - (time.time() - poll_start))
            if not shutdown_requested and sleep_time > 0:
                next_poll = datetime.now() + timedelta(seconds=sleep_time)
                logger.info(f"다음 폴링: {next_poll.strftime('%H:%M:%S')} ({sleep_time/60:.0f}분 후)")
                time.sleep(sleep_time)

    finally:
        logger.info("Producer 종료 중...")
        producer.flush()
        producer.close()
        logger.info(f"정상 종료 — 총 폴링 {poll_count}회 | 총 전송 {total_sent}건")


if __name__ == "__main__":
    run()
