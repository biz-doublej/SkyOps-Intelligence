"""
SkyOps Intelligence — NOTAM Producer (P4+ · 2026-04-15)
=========================================================
`docs/event_model.md` 2.6 NOTAMEvent schema 준수.

모드:
    NOTAM_MODE=mock (default) — 샘플 NOTAM 120초마다 emit
    NOTAM_MODE=api            — FAA NOTAM API / KAC AIS 연동 (P5 이연)

실행:
    python pipeline/notam_producer.py

Topic: `notam`
Partition key: notam_id
"""

from __future__ import annotations

import json
import logging
import os
import random
import signal
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("notam_producer")
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("NOTAM_TOPIC", "notam")
INTERVAL_SEC = int(os.getenv("NOTAM_INTERVAL_SEC", "120"))
MODE = os.getenv("NOTAM_MODE", "mock").lower()
SCHEMA_VERSION = "2.0"


# ── Mock NOTAM pool ────────────────────────────────────────────────────
MOCK_NOTAMS = [
    {
        "notam_series": "A",
        "affected_location": {"type": "RUNWAY", "identifier": "RKSI/RWY15L-33R"},
        "notam_class": "AD",
        "traffic_direction": "BOTH",
        "text_raw": "RWY 15L/33R CLOSED DUE TO PAVEMENT REPAIR",
        "text_en": "Runway 15L/33R closed due to pavement repair. Alt RWY 15R/33L available.",
        "text_ko": "활주로 15L/33R 노면 보수 폐쇄. 대체 활주로 15R/33L 사용 가능.",
        "operational_impact_score": 0.7,
        "icao_code": "RKRR",
        "fir_code": "RKRR",
    },
    {
        "notam_series": "A",
        "affected_location": {"type": "NAVAID", "identifier": "RKSS/VOR-GMP"},
        "notam_class": "NAV",
        "traffic_direction": "BOTH",
        "text_raw": "VOR GMP (114.10) U/S DUE TO GROUND EQUIP MAINT",
        "text_en": "VOR GMP (114.10 MHz) unserviceable due to ground equipment maintenance.",
        "text_ko": "VOR GMP (114.10 MHz) 지상 장비 정비로 사용 불가.",
        "operational_impact_score": 0.4,
        "icao_code": "RKRR",
        "fir_code": "RKRR",
    },
    {
        "notam_series": "B",
        "affected_location": {"type": "AIRPORT", "identifier": "EGLL"},
        "notam_class": "AD",
        "traffic_direction": "BOTH",
        "text_raw": "ILS CAT III RWY 09L U/S. CAT I ONLY",
        "text_en": "ILS CAT III RWY 09L unserviceable. Only CAT I available. DH 200 ft, RVR 550 m minimum.",
        "text_ko": "RWY 09L ILS CAT III 사용 불가. CAT I만 가능. 최저 DH 200ft, RVR 550m.",
        "operational_impact_score": 0.8,
        "icao_code": "EGTT",
        "fir_code": "EGTT",
    },
    {
        "notam_series": "C",
        "affected_location": {"type": "AIRSPACE", "identifier": "ZOA-SECTOR-15"},
        "notam_class": "AS",
        "traffic_direction": "BOTH",
        "text_raw": "ZOA SECTOR 15 RESTRICTED DUE TO WILDFIRE SMOKE FL100-FL240",
        "text_en": "Oakland Center Sector 15 restricted FL100-FL240 due to wildfire smoke reducing visibility.",
        "text_ko": "오클랜드 센터 15 섹터 FL100~FL240 구간 산불 연기로 가시거리 저하, 제한 운영.",
        "operational_impact_score": 0.6,
        "icao_code": "KZOA",
        "fir_code": "KZOA",
    },
    {
        "notam_series": "A",
        "affected_location": {"type": "TAXIWAY", "identifier": "RKSI/TWY-B3"},
        "notam_class": "AD",
        "traffic_direction": "BOTH",
        "text_raw": "TWY B3 CLOSED AT RKSI",
        "text_en": "Taxiway B3 at Incheon closed for construction. Use TWY B2 or B4 as alternates.",
        "text_ko": "인천공항 유도로 B3 건설로 폐쇄. 대체 TWY B2 또는 B4 사용.",
        "operational_impact_score": 0.3,
        "icao_code": "RKRR",
        "fir_code": "RKRR",
    },
    {
        "notam_series": "F",
        "affected_location": {"type": "WAYPOINT", "identifier": "NOHEE"},
        "notam_class": "FDC",
        "traffic_direction": "BOTH",
        "text_raw": "WPT NOHEE TEMPORARILY UNAVAILABLE",
        "text_en": "Waypoint NOHEE (North Pacific) temporarily unavailable. File alternate route via FUKUE.",
        "text_ko": "웨이포인트 NOHEE (북태평양) 일시 사용 불가. FUKUE 경유 대체 경로 제출 필요.",
        "operational_impact_score": 0.5,
        "icao_code": "RJJJ",
        "fir_code": "RJJJ",
    },
]


def make_kafka_producer():
    try:
        from kafka import KafkaProducer
    except ImportError:
        logger.error("kafka-python 미설치. pip install kafka-python")
        sys.exit(1)

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        key_serializer=lambda v: v.encode("utf-8") if v else None,
        acks="all",
        retries=3,
        compression_type="gzip",
    )
    logger.info(f"✅ Kafka producer connected: {KAFKA_BOOTSTRAP}")
    return producer


# P6-G: also LPUSH to Redis so dashboard /notam/recent can read instantly
_redis_client = None


def _publish_to_redis(event: dict) -> None:
    """Best-effort LPUSH + LTRIM to Redis skyops:notam:stream (max 500)."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis  # type: ignore
            _redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True,
                socket_connect_timeout=2,
            )
            _redis_client.ping()
        except Exception as e:
            logger.warning("Redis 비활성 (%s) — dashboard /notam/recent는 비어있음", e)
            _redis_client = False  # sentinel: skip future tries
            return
    if _redis_client is False:
        return

    # Project to /notam/recent expected shape (event_model.md 2.6)
    payload = {
        "notam_number": event.get("notam_id"),
        "notam_class": event.get("notam_class"),
        "location_icao": event.get("icao_code") or (
            event.get("affected_location", {}).get("identifier")
            if isinstance(event.get("affected_location"), dict) else None
        ),
        "fir_icao": event.get("fir_code"),
        "text_raw": event.get("text_raw"),
        "text_english": event.get("text_en"),
        "text_korean": event.get("text_ko"),
        "effective_start": event.get("effective_from"),
        "effective_end": event.get("effective_until"),
        "severity": _severity_from_impact(event.get("operational_impact_score", 0.0)),
        "selection_code": event.get("selection_code"),
        "_mock": event.get("_mock", False),
    }
    try:
        _redis_client.lpush("skyops:notam:stream", json.dumps(payload, ensure_ascii=False))
        _redis_client.ltrim("skyops:notam:stream", 0, 499)
    except Exception as e:
        logger.warning("Redis LPUSH 실패: %s", e)


def _severity_from_impact(impact: float) -> str:
    """Map 0-1 operational_impact_score to NOTAM severity enum."""
    if impact >= 0.7:
        return "CRITICAL"
    if impact >= 0.4:
        return "WARNING"
    if impact >= 0.2:
        return "ADVISORY"
    return "INFO"


def build_mock_notam(template: dict) -> dict:
    """NOTAMEvent schema (event_model.md 2.6)."""
    now = datetime.now(timezone.utc)
    issue_date = now - timedelta(hours=random.randint(1, 12))
    effective_from = now - timedelta(hours=random.randint(0, 6))
    effective_until = now + timedelta(hours=random.randint(3, 48))

    notam_id = f"{template['notam_series']}{random.randint(1000, 9999)}/{now.strftime('%y')}"

    event = {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "notam_id": notam_id,
        "notam_series": template["notam_series"],
        "issue_date": issue_date.isoformat(),
        "effective_from": effective_from.isoformat(),
        "effective_until": effective_until.isoformat(),
        "affected_location": template["affected_location"],
        "notam_class": template["notam_class"],
        "traffic_direction": template["traffic_direction"],
        "text_raw": template["text_raw"],
        "text_en": template["text_en"],
        "text_ko": template["text_ko"],
        "operational_impact_score": template["operational_impact_score"],
        "icao_code": template["icao_code"],
        "fir_code": template["fir_code"],
        "fetched_at": now.isoformat(),
        "_mock": True,
    }
    return event


def main():
    if MODE == "swim":
        logger.info("NOTAM_MODE=swim → FAA SWIM subscriber로 전환")
        # Delegate to swim_subscriber
        try:
            from pathlib import Path
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "swim_subscriber", Path(__file__).resolve().parent / "swim_subscriber.py"
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.main()
        except SystemExit as e:
            # swim_subscriber exits with code 2 on connection failure
            if e.code == 2:
                logger.warning("SWIM connection failed → fallback to mock mode")
                globals()["MODE"] = "mock"
            else:
                raise
        else:
            return  # SWIM run completed normally

    if MODE != "mock":
        logger.error(f"NOTAM_MODE={MODE} 미지원. 'mock' or 'swim'.")
        sys.exit(1)

    producer = make_kafka_producer()

    stopping = False

    def _handle_sigint(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, _handle_sigint)
    try:
        signal.signal(signal.SIGTERM, _handle_sigint)
    except AttributeError:
        pass

    logger.info(f"⚙️  NOTAM producer (mode={MODE}) → topic={TOPIC}, interval={INTERVAL_SEC}s")
    count = 0
    while not stopping:
        template = random.choice(MOCK_NOTAMS)
        event = build_mock_notam(template)
        try:
            fut = producer.send(TOPIC, key=event["notam_id"], value=event)
            fut.get(timeout=10)
            count += 1
            loc = event["affected_location"]
            logger.info(
                f"📤 [{count}] {event['notam_id']:12s} {event['notam_class']:4s} "
                f"{loc['type']:10s} {loc['identifier']:30s} impact={event['operational_impact_score']:.2f}"
            )
        except Exception as e:
            logger.error(f"Kafka send 실패: {e}")

        # P6-G: dashboard fanout — best-effort, never blocks Kafka path
        _publish_to_redis(event)

        for _ in range(INTERVAL_SEC):
            if stopping:
                break
            time.sleep(1)

    producer.flush(10)
    producer.close()
    logger.info(f"✅ 종료 — 총 {count}건 발행")


if __name__ == "__main__":
    main()
