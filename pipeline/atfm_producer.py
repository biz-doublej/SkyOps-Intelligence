"""
SkyOps Intelligence — ATFM Restriction Producer (P4+ · 2026-04-15)
===================================================================
Strategic Review 4번 병목 — 운항 네트워크 feature 확장의 일환.
`docs/event_model.md` 2.5 ATFMRestrictionEvent schema 준수하는 Kafka producer.

모드:
    ATFM_MODE=mock (default) — 샘플 이벤트 60초마다 emit
    ATFM_MODE=api            — EUROCONTROL NM B2B / FAA CSS-Wx 연동 (P5 이연)

실행:
    python pipeline/atfm_producer.py
    ATFM_MODE=mock KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python pipeline/atfm_producer.py

Topic: `atfm-restriction`
Partition key: restriction_id
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

logger = logging.getLogger("atfm_producer")
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)

# ── Kafka 설정 ─────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("ATFM_TOPIC", "atfm-restriction")
INTERVAL_SEC = int(os.getenv("ATFM_INTERVAL_SEC", "60"))
MODE = os.getenv("ATFM_MODE", "mock").lower()
SCHEMA_VERSION = "2.0"


# ── Mock scenario pool (5~10 시나리오) ─────────────────────────────────
MOCK_SCENARIOS = [
    {
        "restriction_type": "GROUND_DELAY_PROGRAM",
        "affected_airports": ["KLAX"],
        "affected_airspace": [],
        "reason": "WEATHER",
        "delay_expectation_min": 45,
        "issuing_authority": "FAA",
        "initiative_name": "LAX GDP — Low Ceilings",
    },
    {
        "restriction_type": "GROUND_DELAY_PROGRAM",
        "affected_airports": ["KJFK", "KEWR"],
        "affected_airspace": [],
        "reason": "TRAFFIC_CONGESTION",
        "delay_expectation_min": 30,
        "issuing_authority": "FAA",
        "initiative_name": "NYC Metro GDP",
    },
    {
        "restriction_type": "DEPARTURE_SLOT",
        "affected_airports": ["EGLL"],
        "affected_airspace": [],
        "reason": "RUNWAY_CLOSURE",
        "delay_expectation_min": 20,
        "issuing_authority": "EUROCONTROL",
        "initiative_name": "LHR SW Runway Maintenance",
    },
    {
        "restriction_type": "SPEED_RESTRICTION",
        "affected_airports": [],
        "affected_airspace": ["EDYY-SECTOR-9"],
        "reason": "TRAFFIC_CONGESTION",
        "delay_expectation_min": 10,
        "issuing_authority": "EUROCONTROL",
        "initiative_name": "DE Sector 9 MIT",
    },
    {
        "restriction_type": "REROUTING",
        "affected_airports": [],
        "affected_airspace": ["LKPR-AREA"],
        "reason": "WEATHER",
        "delay_expectation_min": 15,
        "issuing_authority": "EUROCONTROL",
        "initiative_name": "Central EU Thunderstorm Reroute",
    },
    {
        "restriction_type": "CLOSURE",
        "affected_airports": ["RJTT"],
        "affected_airspace": [],
        "reason": "EQUIPMENT_OUTAGE",
        "delay_expectation_min": 60,
        "issuing_authority": "CAAC",
        "initiative_name": "Haneda 34R ILS Outage",
    },
    {
        "restriction_type": "ALTITUDE_RESTRICTION",
        "affected_airports": [],
        "affected_airspace": ["RKRR-UPPER-5"],
        "reason": "SECURITY",
        "delay_expectation_min": 5,
        "issuing_authority": "KAC",
        "initiative_name": "Seoul TMA altitude cap",
    },
]


# ── Kafka Producer 초기화 ──────────────────────────────────────────────
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


# ── Mock event 생성 ────────────────────────────────────────────────────
def build_mock_event(scenario: dict) -> dict:
    """ATFMRestrictionEvent schema (event_model.md 2.5)."""
    now = datetime.now(timezone.utc)
    effective_from = now + timedelta(minutes=random.randint(0, 30))
    duration = scenario["delay_expectation_min"] + random.randint(10, 60)
    effective_until = effective_from + timedelta(minutes=duration)

    event_id = str(uuid.uuid4())
    restriction_id = f"ATFM-{now.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    event = {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id,
        "restriction_id": restriction_id,
        "restriction_type": scenario["restriction_type"],
        "affected_airports": scenario["affected_airports"],
        "affected_airspace": scenario["affected_airspace"],
        "reason": scenario["reason"],
        "effective_from": effective_from.isoformat(),
        "effective_until": effective_until.isoformat(),
        "expected_duration_min": duration,
        "delay_expectation_min": scenario["delay_expectation_min"],
        "issuing_authority": scenario["issuing_authority"],
        "initiative_name": scenario["initiative_name"],
        "fetched_at": now.isoformat(),
        "_mock": True,  # 명시적 mock 플래그 (P5 실 연동 시 제거)
    }
    return event


# ── Main loop ──────────────────────────────────────────────────────────
def main():
    if MODE != "mock":
        logger.error(f"ATFM_MODE={MODE} 미지원. 'mock'만 지원 (P5에서 'api' 추가 예정).")
        sys.exit(1)

    producer = make_kafka_producer()

    stopping = False

    def _handle_sigint(*_):
        nonlocal stopping
        logger.info("SIGINT — shutting down")
        stopping = True

    signal.signal(signal.SIGINT, _handle_sigint)
    try:
        signal.signal(signal.SIGTERM, _handle_sigint)
    except AttributeError:
        pass  # Windows

    logger.info(f"⚙️  ATFM producer (mode={MODE}) → topic={TOPIC}, interval={INTERVAL_SEC}s")
    count = 0
    while not stopping:
        scenario = random.choice(MOCK_SCENARIOS)
        event = build_mock_event(scenario)
        try:
            fut = producer.send(TOPIC, key=event["restriction_id"], value=event)
            fut.get(timeout=10)
            count += 1
            logger.info(
                f"📤 [{count}] {event['restriction_type']:25s} {event['initiative_name'][:50]:50s} "
                f"duration={event['expected_duration_min']:3d}m "
                f"delay={event['delay_expectation_min']:3d}m"
            )
        except Exception as e:
            logger.error(f"Kafka send 실패: {e}")

        for _ in range(INTERVAL_SEC):
            if stopping:
                break
            time.sleep(1)

    producer.flush(10)
    producer.close()
    logger.info(f"✅ 종료 — 총 {count}건 발행")


if __name__ == "__main__":
    main()
