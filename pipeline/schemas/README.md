# Avro Schema Registry for SkyOps Canonical Events (P6-B · 2026-04-15)

Strategic Review 병목 #5 (Data Contract · Lineage) closure.

## 📂 Schema files

| Topic | Schema | Aligned with |
|-------|--------|--------------|
| `flight-position` | `flight_position.avsc` | event_model.md 2.1 |
| `weather-event` | `weather_event.avsc` | event_model.md 2.4 |
| `notam` | `notam.avsc` | event_model.md 2.6 |
| `atfm-restriction` | `atfm_restriction.avsc` | event_model.md 2.5 |
| `alert-decision` | `alert_decision.avsc` | event_model.md 2.7 |

Namespace: `com.skyops.events.v2`. schema_version 2.0 bumps from v1 (JSON only).

## 🚀 Register to Confluent Schema Registry (local)

```bash
# Start registry (bitnami compose — add to docker-compose.yml as profile 'schema')
docker compose --profile schema up -d schema-registry

# Install confluent-kafka extras
pip install -e ".[schema]"

# Register all
python -m pipeline.schema_registry register-all \
    --registry-url http://localhost:8081

# Verify
curl -s http://localhost:8081/subjects | jq .
```

## 🔒 Compatibility mode

Per-topic compatibility: `BACKWARD` — new schema can read data produced
by old schema. Enforced in registry at register-time.

## 🔄 Evolution rules

1. **Additive only**: new optional fields with default values are safe
2. **Never remove** a required field — deprecate with `doc` and omit from writers
3. **Enum additions**: only at the end of the `symbols` list
4. **Type widening**: `int → long` safe; `long → int` is NOT safe
5. **Rename**: use `aliases` field

## 🧪 Validation

```python
from pipeline.schema_registry import validate_event
from pipeline.schemas import get_schema

validate_event(
    schema=get_schema("flight_position"),
    payload={"icao24": "abc123", ...},
)  # raises on mismatch
```

Producers (`opensky_producer.py`, `notam_producer.py`, etc.) will be
updated in P6-B-2 to use `AvroProducer` with Schema Registry.
