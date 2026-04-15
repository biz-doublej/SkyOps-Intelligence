# SkyOps Iceberg Warehouse (P6-D · 2026-04-15)

Strategic Review 병목 #5 (Data Contract + Lineage) closure.

## 🏛️ Medallion Architecture

```
Kafka topics ──► Bronze ──► Silver ──► Gold
  (raw)         (ingest)    (clean)    (model-ready)
```

### Bronze (`bronze_*`)
Raw ingestion as-is. Payload JSON + timestamp + primary key.

| Table | Primary key | Source |
|-------|-------------|--------|
| `bronze_flight_position_raw` | (event_timestamp, icao24) | Kafka `flight-position` |
| `bronze_weather_event_raw` | (event_timestamp, station_icao) | Kafka `weather-event` |
| `bronze_notam_raw` | (event_timestamp, notam_number) | Kafka `notam` |
| `bronze_atfm_restriction_raw` | (event_timestamp, restriction_type) | Kafka `atfm-restriction` |

### Silver (`silver_*`)
Cleaned + joined + deduped. Type-enforced via Avro schemas.

| Table | Key | Producer |
|-------|-----|----------|
| `silver_flight_features` | (tail_number, event_timestamp) | feature_engineering.py |
| `silver_aircraft_phase` | (icao24, event_timestamp) | flink_processor.py + ML phase classifier |
| `silver_airport_context` | (airport_code, event_timestamp) | swim_subscriber + metar_producer aggregation |

### Gold (`gold_*`)
Model training splits + inference logs. Consumed by MLflow + active learning.

| Table | Use |
|-------|-----|
| `gold_delay_train_split` | frozen train/val/test splits w/ feature snapshots |
| `gold_inference_log` | production inference log (req_id, model version, interval) |
| `gold_anomaly_decisions` | merged AnomalyEvent + AnalystFeedback |

## 🚀 Bootstrap

```bash
pip install -e ".[iceberg]"
python -m feature_store.iceberg_bootstrap
# → creates data/iceberg/catalog.db + namespace 'skyops' + 10 tables
```

## 📸 Snapshot / Time-travel

```python
from pyiceberg.catalog import load_catalog

cat = load_catalog("skyops", type="sql",
                   uri="sqlite:///data/iceberg/catalog.db",
                   warehouse="file://data/iceberg")
tbl = cat.load_table("skyops.silver_flight_features")

# Current
df_now = tbl.scan().to_pandas()

# As-of snapshot (training reproducibility)
snaps = list(tbl.snapshots())
older = snaps[-5].snapshot_id
df_then = tbl.scan(snapshot_id=older).to_pandas()
```

## 🔄 Write path (future)

```python
# Bronze writer (called by kafka consumer)
import pyarrow as pa
batch = pa.Table.from_pylist([{
    "event_timestamp": pa.scalar(datetime.utcnow(), type=pa.timestamp("us")),
    "icao24": "abc123",
    "payload_json": json.dumps(event),
}])
tbl.append(batch)
# → creates new snapshot atomically
```

Silver transformations land as **overwrite_partitions** with event-time windows.
Gold writes are append-only (inference log is immutable by design).

## 🔗 Integration points

- **feature_engineering.py** writes Silver
- **flink_processor.py** writes Bronze
- **active_learning_retrain.py** reads Gold (analyst feedback → retrain signal)
- **Schema Registry** (P6-B) defines the contract; Iceberg enforces it at write
- **MLflow** stores model_version + inference_log dataset reference via OpenLineage

## 🛣️ Roadmap

| Step | Status |
|------|--------|
| Bootstrap + tables | ✅ P6-D (this PR) |
| Bronze writer from Flink | 🔄 P7 |
| Silver transformer (feature_engineering → Iceberg) | 🔄 P7 |
| Gold inference log (serving emits async) | 🔄 P7 |
| OpenLineage MLflow integration | 🔄 P7 |
| Production catalog (Glue/Hive → Iceberg REST) | 🔄 P7 |
