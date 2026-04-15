"""SkyOps Schema Registry helper (P6-B · 2026-04-15).

Thin wrapper around Confluent Schema Registry client + fastavro validation.
Stays optional: if SCHEMA_REGISTRY_URL is unset, producers keep emitting
plain JSON (backward compatible with P5+).

Usage — register all schemas:
    python -m pipeline.schema_registry register-all --registry-url http://localhost:8081

Usage — in producers:
    from pipeline.schema_registry import load_schema, validate_event

    schema = load_schema("notam")
    validate_event(schema, payload)   # raises on mismatch
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"
REGISTRY_URL_ENV = "SCHEMA_REGISTRY_URL"

# topic → schema file
TOPIC_SCHEMA = {
    "flight-position":   "flight_position.avsc",
    "weather-event":     "weather_event.avsc",
    "notam":             "notam.avsc",
    "atfm-restriction":  "atfm_restriction.avsc",
    "alert-decision":    "alert_decision.avsc",
    "acdm-milestone":    "acdm_milestone.avsc",  # P8-F (2026-04-15)
}


def load_schema(name: str) -> dict[str, Any]:
    """Load a schema by name (stem) or topic name.

    Accepts 'notam', 'notam.avsc', or 'notam_topic' lookups via TOPIC_SCHEMA.
    """
    if name in TOPIC_SCHEMA:
        name = TOPIC_SCHEMA[name]
    if not name.endswith(".avsc"):
        name = f"{name}.avsc"
    path = SCHEMAS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_event(schema: dict[str, Any], payload: dict[str, Any]) -> None:
    """Validate payload against Avro schema. Raises on mismatch."""
    try:
        import fastavro
    except ImportError as e:
        raise ImportError(
            "fastavro 미설치. `pip install -e \".[schema]\"` 실행."
        ) from e

    parsed = fastavro.parse_schema(schema)
    # fastavro.validate returns True/False; use validation for raises
    if not fastavro.validate(payload, parsed, raise_errors=True):
        raise ValueError(f"Avro validation failed for {schema.get('name')}")


def _make_registry_client(url: str):
    try:
        from confluent_kafka.schema_registry import SchemaRegistryClient
    except ImportError as e:
        raise ImportError(
            "confluent-kafka[schemaregistry] 미설치. "
            "`pip install -e \".[schema]\"` 실행."
        ) from e
    return SchemaRegistryClient({"url": url})


def register_all(registry_url: str, compatibility: str = "BACKWARD") -> int:
    """Register every schema in pipeline/schemas/ to the registry.

    Subject naming: topic-value strategy (e.g. 'notam-value').
    Returns the count of successfully registered schemas.
    """
    from confluent_kafka.schema_registry import Schema  # type: ignore

    client = _make_registry_client(registry_url)
    registered = 0
    for topic, fname in TOPIC_SCHEMA.items():
        schema = load_schema(fname)
        subject = f"{topic}-value"
        schema_str = json.dumps(schema)
        try:
            schema_id = client.register_schema(
                subject_name=subject,
                schema=Schema(schema_str=schema_str, schema_type="AVRO"),
            )
            logger.info("registered %s → id=%d", subject, schema_id)
            registered += 1
        except Exception as e:  # noqa: BLE001
            logger.error("failed to register %s: %s", subject, e)

        # Compatibility setting
        try:
            client.set_compatibility(subject, compatibility)
            logger.info("compatibility(%s) = %s", subject, compatibility)
        except Exception as e:  # noqa: BLE001
            logger.warning("compat set failed %s: %s", subject, e)

    return registered


def main() -> int:
    parser = argparse.ArgumentParser(description="SkyOps Schema Registry CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    reg = sub.add_parser("register-all", help="Register every .avsc to the registry")
    reg.add_argument("--registry-url",
                     default=os.getenv(REGISTRY_URL_ENV, "http://localhost:8081"))
    reg.add_argument("--compatibility", default="BACKWARD",
                     choices=["BACKWARD", "FORWARD", "FULL", "NONE"])

    val = sub.add_parser("validate", help="Validate a JSON payload against a schema")
    val.add_argument("--schema", required=True, help="Schema name (e.g. 'notam')")
    val.add_argument("--payload", required=True, help="Path to JSON file")

    ls = sub.add_parser("list", help="List available schemas")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.cmd == "list":
        for topic, fname in TOPIC_SCHEMA.items():
            schema = load_schema(fname)
            print(f"  {topic:20s} → {fname:30s}  ({schema['name']})")
        return 0

    if args.cmd == "validate":
        schema = load_schema(args.schema)
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        try:
            validate_event(schema, payload)
            print(f"✅ payload conforms to {schema['name']}")
            return 0
        except Exception as e:  # noqa: BLE001
            print(f"❌ validation failed: {e}")
            return 2

    if args.cmd == "register-all":
        n = register_all(args.registry_url, args.compatibility)
        print(f"\n✅ Registered {n}/{len(TOPIC_SCHEMA)} schemas with "
              f"compatibility={args.compatibility}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
