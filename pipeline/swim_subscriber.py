"""
SkyOps Intelligence — FAA SWIM NOTAM Subscriber (P5+ · 2026-04-15)
====================================================================
FAA SWIM (System Wide Information Management) NOTAM JMS 구독 → AIXM 5.1 XML
파싱 → canonical NOTAMEvent schema → Kafka `notam` 토픽 재발행.

- Protocol: Solace SMF (Python client, `solace-pubsubplus==1.11.0`)
- Broker: tcps://ems2.swim.faa.gov:55443 (VPN: AIM_FNS)
- Auth: username/password (no client mTLS in our subscription)
- Queue: 사전 생성된 per-account queue, 예:
  `jaewonjung1004.gmail.com.AIM_FNS.{uuid}.OUT`
- Payload: AIXM 5.1 Message (XML) — `xmlns:aixm="http://www.aixm.aero/schema/5.1"`

실행:
    python pipeline/swim_subscriber.py
    SWIM_RUN_SECONDS=60 python pipeline/swim_subscriber.py  # 1분만

환경변수 (.env):
    SWIM_HOST, SWIM_VPN, SWIM_USERNAME, SWIM_PASSWORD, SWIM_QUEUE
    KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_NOTAM (default: notam)

Graceful fallback: 연결 실패 시 exit code 2, 호출자는 mock으로 폴백 가능.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pathlib import Path

# ── dotenv (optional) ────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger("swim_subscriber")
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)

# ── Environment ──────────────────────────────────────────────────────
SWIM_HOST = os.getenv("SWIM_HOST", "").strip()
SWIM_VPN = os.getenv("SWIM_VPN", "").strip()
SWIM_USERNAME = os.getenv("SWIM_USERNAME", "").strip()
SWIM_PASSWORD = os.getenv("SWIM_PASSWORD", "").strip()
SWIM_QUEUE = os.getenv("SWIM_QUEUE", "").strip()
SWIM_RECONNECT_RETRIES = int(os.getenv("SWIM_RECONNECT_RETRIES", "5"))
SWIM_RECONNECT_INTERVAL_SEC = int(os.getenv("SWIM_RECONNECT_INTERVAL_SEC", "10"))

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC_NOTAM", "notam")
RUN_SECONDS = int(os.getenv("SWIM_RUN_SECONDS", "0"))  # 0 = 무한 (until SIGINT)
SCHEMA_VERSION = "2.0"


def _validate_env() -> bool:
    missing = []
    for k in ("SWIM_HOST", "SWIM_VPN", "SWIM_USERNAME", "SWIM_PASSWORD", "SWIM_QUEUE"):
        if not os.getenv(k, "").strip():
            missing.append(k)
    if missing:
        logger.error(f"Missing env vars: {missing}")
        logger.error("Copy .env.example → .env and fill SWIM credentials.")
        return False
    return True


# ── AIXM 5.1 NOTAM parsing ───────────────────────────────────────────
def parse_aixm_notam(xml_text: str) -> dict[str, Any]:
    """Parse FAA SWIM NOTAM XML → canonical NOTAMEvent schema.

    FAA SWIM publishes NOTAMs using `event:` namespace (not pure AIXM 5.1 aixm:),
    with fields like event:series, event:number, event:selectionCode, event:text.
    We handle both `event:` and `aixm:` prefixes.

    Q-code (selectionCode): e.g. QNDAS = NOTAM class NAV, status unserviceable.
    First char: Q (always), 2-3 chars: subject (MR=runway, NA=airspace, ND=navaid),
    4-5 chars: status (CL=closed, AS=active, LC=limited).

    Returns dict matching `docs/event_model.md` 2.6 NOTAMEvent schema.
    """
    import re

    now_iso = datetime.now(timezone.utc).isoformat()

    def _grab(tag: str) -> Optional[str]:
        m = re.search(rf"<(?:\w+:)?{tag}(?:\s[^>]*)?>(.*?)</(?:\w+:)?{tag}>", xml_text, re.DOTALL)
        return m.group(1).strip() if m else None

    series = (_grab("series") or "A")[:1].upper()
    notam_number = _grab("number")
    notam_year = _grab("year")
    if notam_number and notam_year:
        notam_id = f"{series}{notam_number}/{notam_year[-2:]}"
    elif notam_number:
        notam_id = f"{series}{notam_number}/{datetime.now(timezone.utc).strftime('%y')}"
    else:
        notam_id = f"SWIM-{uuid.uuid4().hex[:8]}"

    # Location parsing — 4-char ICAO or 3-char FAA identifier
    location = _grab("location") or _grab("aerodromeCode") or _grab("ICAO")
    affected_fir = _grab("affectedFIR") or _grab("fir")

    # Q-code (selectionCode) parsing
    sel_code = (_grab("selectionCode") or "").strip()
    # e.g. QNDAS → class=N(AV), status=AS (active)
    notam_class_raw = sel_code[1:2] if len(sel_code) >= 2 else "A"
    class_map = {"A": "AD", "M": "AD", "N": "NAV", "C": "COM", "F": "FDC", "R": "AS"}
    notam_class = class_map.get(notam_class_raw.upper(), "AD")

    # Affected location type inference from Q-code
    subject_char2 = sel_code[2:3] if len(sel_code) >= 3 else ""
    if subject_char2 in ("R",):
        affected_loc_type = "RUNWAY"
    elif subject_char2 in ("A",):
        affected_loc_type = "AIRSPACE"
    elif subject_char2 in ("D", "N"):
        affected_loc_type = "NAVAID"
    else:
        affected_loc_type = "AIRPORT"

    affected_loc_id = location or affected_fir or "UNKNOWN"
    if location and affected_loc_type == "RUNWAY":
        rwy = _grab("runway") or ""
        affected_loc_id = f"{location}/{rwy}" if rwy else location

    # Traffic direction — FAA doesn't always publish; default BOTH
    traffic_direction = _grab("trafficIndicator") or _grab("traffic") or "BOTH"

    # Text extraction: FAA uses <event:text> with actual NOTAM body
    text_raw = _grab("text") or _grab("translatedText") or _grab("notamText") or ""
    text_raw = re.sub(r"<[^>]+>", "", text_raw)  # strip any nested tags
    text_raw = re.sub(r"\s+", " ", text_raw).strip()

    # Validity — FAA uses effectiveStart/End in YYYYMMDDHHMM format
    def _parse_faa_ts(v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip()
        # Strip trailing timezone abbreviation like 'EST', 'UTC'
        m = re.match(r"^(\d{12})", v)
        if not m:
            return v
        try:
            dt = datetime.strptime(m.group(1), "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            return v

    effective_from = _parse_faa_ts(_grab("effectiveStart")) or _grab("timeSliceTimeStart") or now_iso
    effective_until = _parse_faa_ts(_grab("effectiveEnd")) or _grab("timeSliceTimeEnd")
    issue_date = _grab("issued") or _grab("issuance") or now_iso

    # ICAO + FIR
    icao_code = affected_fir or (f"K{location}" if location and len(location) == 3 else location) or "UNKNOWN"
    fir_code = affected_fir or icao_code

    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "notam_id": notam_id,
        "notam_series": series,
        "issue_date": issue_date,
        "effective_from": effective_from,
        "effective_until": effective_until,
        "affected_location": {"type": affected_loc_type, "identifier": affected_loc_id},
        "notam_class": notam_class,
        "traffic_direction": traffic_direction,
        "text_raw": text_raw[:2000],
        "text_en": text_raw[:2000],
        "text_ko": None,  # LLM 번역은 downstream
        "operational_impact_score": None,
        "selection_code": sel_code,  # FAA 고유 Q-code 유지
        "icao_code": icao_code,
        "fir_code": fir_code,
        "fetched_at": now_iso,
        "source": "FAA_SWIM",
        "_raw_xml_length": len(xml_text),
    }


# ── Kafka Producer ───────────────────────────────────────────────────
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
    logger.info(f"✅ Kafka producer: {KAFKA_BOOTSTRAP} → topic={TOPIC}")
    return producer


# ── Solace SMF connection ────────────────────────────────────────────
def connect_solace():
    """Create and start a Solace MessagingService. Raises on failure."""
    from solace.messaging.messaging_service import MessagingService, RetryStrategy
    from solace.messaging.config.solace_properties import (
        transport_layer_properties,
        service_properties,
        authentication_properties,
        transport_layer_security_properties as tls_props,
    )

    broker_props = {
        transport_layer_properties.HOST: SWIM_HOST,
        service_properties.VPN_NAME: SWIM_VPN,
        authentication_properties.SCHEME: "AUTHENTICATION_SCHEME_BASIC",
        authentication_properties.SCHEME_BASIC_USER_NAME: SWIM_USERNAME,
        authentication_properties.SCHEME_BASIC_PASSWORD: SWIM_PASSWORD,
        # TLS server verify (boolean; Python API expects True/False not string)
        tls_props.CERT_VALIDATED: True,
        tls_props.CERT_VALIDATE_SERVERNAME: True,
    }

    # Trust store: user-provided or certifi CA bundle fallback
    trust_store_path = os.getenv("SWIM_TRUSTSTORE_PATH", "").strip()
    if not trust_store_path:
        try:
            import certifi
            # Solace needs a DIRECTORY of PEMs, not a single file — use certifi parent dir.
            # Actually Solace Python accepts a single PEM file too; pass directly.
            trust_store_path = certifi.where()
        except ImportError:
            logger.warning("certifi 미설치 → OS trust store 사용 시도")

    if trust_store_path:
        broker_props[tls_props.TRUST_STORE_PATH] = trust_store_path
        logger.info(f"   TLS trust store: {trust_store_path}")

    service = (
        MessagingService.builder()
        .from_properties(broker_props)
        .with_reconnection_retry_strategy(
            RetryStrategy.parametrized_retry(SWIM_RECONNECT_RETRIES, SWIM_RECONNECT_INTERVAL_SEC * 1000)
        )
        .build()
    )
    logger.info(f"🔌 Connecting to {SWIM_HOST} (VPN={SWIM_VPN})...")
    service.connect()
    logger.info("✅ Connected to SWIM broker")
    return service


def subscribe_queue(service, queue_name: str):
    """Create a persistent receiver on the pre-provisioned queue."""
    from solace.messaging.resources.queue import Queue

    queue = Queue.durable_exclusive_queue(queue_name)
    receiver = (
        service.create_persistent_message_receiver_builder()
        .build(queue)
    )
    receiver.start()
    logger.info(f"📥 Subscribed to queue: {queue_name}")
    return receiver


# ── Main loop ────────────────────────────────────────────────────────
def main():
    if not _validate_env():
        sys.exit(2)

    try:
        service = connect_solace()
    except Exception as e:
        logger.error(f"❌ SWIM connection failed: {e}")
        logger.error("   계정 활성, password 정확, IP 화이트리스트 여부 확인 필요")
        sys.exit(2)

    try:
        receiver = subscribe_queue(service, SWIM_QUEUE)
    except Exception as e:
        logger.error(f"❌ Queue subscription failed: {e}")
        service.disconnect()
        sys.exit(2)

    producer = make_kafka_producer()

    stopping = False

    def _stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, _stop)
    try:
        signal.signal(signal.SIGTERM, _stop)
    except AttributeError:
        pass  # Windows

    logger.info(f"🚀 SWIM subscriber running (RUN_SECONDS={RUN_SECONDS or 'infinite'})")
    start_time = time.time()
    count_received = 0
    count_published = 0
    count_parse_err = 0

    try:
        while not stopping:
            if RUN_SECONDS and (time.time() - start_time) >= RUN_SECONDS:
                logger.info(f"⏰ RUN_SECONDS={RUN_SECONDS} reached")
                break

            # Blocking receive with 1s timeout
            msg = receiver.receive_message(timeout=1000)
            if msg is None:
                continue

            count_received += 1
            try:
                payload = msg.get_payload_as_string()
                if not payload:
                    # Some messages are byte buffers
                    payload = msg.get_payload_as_bytes().decode("utf-8", errors="replace")
            except Exception:
                payload = ""

            try:
                event = parse_aixm_notam(payload)
            except Exception as e:
                logger.warning(f"AIXM parse error: {e}")
                count_parse_err += 1
                continue

            try:
                fut = producer.send(TOPIC, key=event["notam_id"], value=event)
                fut.get(timeout=10)
                count_published += 1
            except Exception as e:
                logger.error(f"Kafka send error: {e}")

            # P6-G: dashboard fanout — best-effort, never blocks Kafka path
            try:
                from pipeline.notam_producer import _publish_to_redis  # type: ignore
                _publish_to_redis(event)
            except Exception:
                pass

            # P7-A: Iceberg Bronze append — best-effort
            try:
                from feature_store.iceberg_writer import write_bronze_event  # type: ignore
                write_bronze_event(
                    "notam_raw",
                    notam_number=event.get("notam_id", ""),
                    payload=event,
                )
            except Exception:
                pass

            if count_received % 10 == 0:
                logger.info(
                    f"📊 received={count_received} published={count_published} "
                    f"parse_err={count_parse_err}"
                )

    except Exception as e:
        logger.error(f"Runtime error: {e}", exc_info=True)
    finally:
        logger.info(
            f"🛑 Shutdown — received={count_received} published={count_published} "
            f"parse_err={count_parse_err}"
        )
        try:
            receiver.terminate()
        except Exception:
            pass
        try:
            service.disconnect()
        except Exception:
            pass
        producer.flush(5)
        producer.close()


if __name__ == "__main__":
    main()
