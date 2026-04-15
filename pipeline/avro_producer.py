"""SkyOps AvroProducer wrapper (P8-B · 2026-04-15).

Thin adapter around `confluent_kafka.SerializingProducer` that:
  1. Pulls the Avro schema for the topic from Confluent Schema Registry
  2. Serializes payload with fastavro
  3. Produces to Kafka with schema_id header

Backward compat:
  SCHEMA_REGISTRY_URL unset → falls back to plain JSON producer
  (identical bytes-on-wire as P5+/P6 producers)

Env:
  SCHEMA_REGISTRY_URL    — e.g. http://localhost:8081
  KAFKA_BOOTSTRAP_SERVERS
  AVRO_ENFORCE=1         — 1: raise on validation failure; 0: log + skip

Usage:
    from pipeline.avro_producer import build_producer, produce_avro
    producer = build_producer(topic="notam")
    produce_avro(producer, topic="notam", key="A1234/26", value=event)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
AVRO_ENFORCE = os.getenv("AVRO_ENFORCE", "0") == "1"


def _avro_available() -> bool:
    try:
        import confluent_kafka  # noqa: F401
        import fastavro  # noqa: F401
        return bool(SCHEMA_REGISTRY_URL)
    except ImportError:
        return False


class _JSONAdapter:
    """Fallback producer — emits JSON (backward compat with P5+)."""

    def __init__(self):
        try:
            from kafka import KafkaProducer
        except ImportError as e:
            raise ImportError("kafka-python 미설치. pip install kafka-python") from e
        self._inner = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False, default=str).encode(),
            key_serializer=lambda v: str(v).encode() if v is not None else None,
            acks="all",
            retries=3,
            compression_type="gzip",
        )

    def produce(self, topic: str, key: Any, value: Any) -> None:
        fut = self._inner.send(topic, key=key, value=value)
        fut.get(timeout=10)

    def flush(self, timeout: float = 10.0) -> None:
        self._inner.flush(timeout)

    def close(self) -> None:
        try:
            self._inner.close(timeout=5)
        except Exception:
            pass


class _AvroAdapter:
    """Real Avro producer — pulls schema from registry, validates, serializes."""

    def __init__(self, topic: str):
        from confluent_kafka.schema_registry import SchemaRegistryClient
        from confluent_kafka.schema_registry.avro import AvroSerializer
        from confluent_kafka.serialization import StringSerializer
        from confluent_kafka import SerializingProducer
        from pipeline.schema_registry import load_schema

        self._sr = SchemaRegistryClient({"url": SCHEMA_REGISTRY_URL})
        self._schema = load_schema(topic)
        schema_str = json.dumps(self._schema)

        self._key_ser = StringSerializer("utf-8")
        self._val_ser = AvroSerializer(
            self._sr,
            schema_str=schema_str,
        )
        self._producer = SerializingProducer({
            "bootstrap.servers": KAFKA_BOOTSTRAP,
            "key.serializer": self._key_ser,
            "value.serializer": self._val_ser,
            "acks": "all",
            "retries": 3,
            "compression.type": "gzip",
        })
        logger.info("AvroProducer ready: topic=%s, schema=%s",
                    topic, self._schema.get("name"))

    def produce(self, topic: str, key: Any, value: Any) -> None:
        # fastavro pre-validation for helpful errors
        try:
            import fastavro
            fastavro.validate(value, fastavro.parse_schema(self._schema),
                              raise_errors=AVRO_ENFORCE)
        except Exception as e:  # noqa: BLE001
            if AVRO_ENFORCE:
                raise
            logger.warning("avro validation soft-fail on %s: %s", topic, e)
            return
        self._producer.produce(topic=topic, key=str(key) if key else None, value=value)

    def flush(self, timeout: float = 10.0) -> None:
        self._producer.flush(timeout)

    def close(self) -> None:
        self.flush(5.0)


def build_producer(topic: str):
    """Return an Avro producer if configured, else JSON fallback."""
    if _avro_available():
        try:
            return _AvroAdapter(topic)
        except Exception as e:  # noqa: BLE001
            logger.warning("AvroProducer init failed (%s) — fallback to JSON", e)
    return _JSONAdapter()


def produce_avro(producer, topic: str, key: Any, value: Any) -> None:
    """Convenience — works for both Avro and JSON fallback."""
    producer.produce(topic=topic, key=key, value=value)


def health() -> dict[str, Any]:
    return {
        "schema_registry_url": SCHEMA_REGISTRY_URL or None,
        "avro_available": _avro_available(),
        "enforce": AVRO_ENFORCE,
    }
