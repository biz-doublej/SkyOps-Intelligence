"""SkyOps Iceberg Bronze/Silver/Gold bootstrap (P6-D · 2026-04-15).

Strategic Review 병목 #5 (Data Contract + Lineage) follow-through.

Apache Iceberg gives us:
  - Snapshot / time-travel (each write = new snapshot, can query "as of")
  - Schema evolution (add/rename/reorder column without rewrite)
  - Hidden partitioning (queries don't need partition predicates)

Medallion layout:
  Bronze  raw ingest (flight-position, weather-event, notam, etc.)
  Silver  cleaned + joined (flight_features, alert_decisions)
  Gold    model-ready aggregates (training splits, inference logs)

Run:
    python -m feature_store.iceberg_bootstrap
    python -m feature_store.iceberg_bootstrap --layer bronze
    python -m feature_store.iceberg_bootstrap --namespace custom
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICEBERG_WAREHOUSE = PROJECT_ROOT / "data" / "iceberg"

TABLES = {
    "bronze": {
        "flight_position_raw":  ["event_timestamp", "icao24", "payload_json"],
        "weather_event_raw":    ["event_timestamp", "station_icao", "payload_json"],
        "notam_raw":            ["event_timestamp", "notam_number", "payload_json"],
        "atfm_restriction_raw": ["event_timestamp", "restriction_type", "payload_json"],
    },
    "silver": {
        "flight_features":      ["event_timestamp", "tail_number", "rotation_depth",
                                 "prev_leg_arr_delay_min", "scheduled_turnaround_min"],
        "aircraft_phase":       ["event_timestamp", "icao24", "flight_phase",
                                 "phase_confidence"],
        "airport_context":      ["event_timestamp", "airport_code", "hourly_departures",
                                 "notam_impact_score"],
    },
    "gold": {
        "delay_train_split":    ["event_timestamp", "split_name", "features_json",
                                 "actual_delay_min"],
        "inference_log":        ["event_timestamp", "request_id", "model_version",
                                 "predicted_delay_min", "interval_lower", "interval_upper"],
        "anomaly_decisions":    ["event_timestamp", "alert_id", "anomaly_type",
                                 "severity", "flight_phase", "analyst_label"],
    },
}


def _build_catalog_config() -> dict:
    """Return pyiceberg load_catalog kwargs based on env (v2.1.8 · ADR-004).

    Two modes:

    1. **SQL + local file warehouse** (default, laptop dev).
       - `type=sql`, `uri=sqlite:///…/catalog.db`, warehouse is a local directory.
       - Zero-dep, no docker services needed.

    2. **REST (Nessie) + S3 (MinIO)** — set `ICEBERG_CATALOG=rest`.
       - `type=rest`, `uri=http://nessie:19120/iceberg/v1`.
       - Warehouse points to MinIO bucket `s3://skyops-iceberg/`.
       - Matches the `docker compose --profile warehouse up` services so
         training, serving, and BI can share one catalog.

    The switch is a single env flag so CI / prod can flip without code edits.
    """
    mode = os.getenv("ICEBERG_CATALOG", "sql").lower()

    if mode == "rest":
        # Nessie exposes Iceberg REST catalog endpoint on /iceberg/v1.
        uri = os.getenv("ICEBERG_CATALOG_URI", "http://nessie:19120/iceberg/v1")
        warehouse = os.getenv("ICEBERG_WAREHOUSE_S3", "s3://skyops-iceberg/")
        s3_endpoint = os.getenv("AWS_S3_ENDPOINT", "http://minio:9000")
        s3_access = os.getenv("AWS_ACCESS_KEY_ID", "skyops")
        s3_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "skyops-dev-only")
        return {
            "type": "rest",
            "uri": uri,
            "warehouse": warehouse,
            "s3.endpoint": s3_endpoint,
            "s3.access-key-id": s3_access,
            "s3.secret-access-key": s3_secret,
            "s3.path-style-access": "true",
        }

    # Default: SQL catalog, local file warehouse
    ICEBERG_WAREHOUSE.mkdir(parents=True, exist_ok=True)
    return {
        "type": "sql",
        "uri": f"sqlite:///{ICEBERG_WAREHOUSE}/catalog.db",
        "warehouse": f"file://{ICEBERG_WAREHOUSE}",
    }


def bootstrap_pyiceberg(layer_filter: str | None, namespace: str) -> int:
    """Create catalog + namespaces + (empty) tables.

    Backends:
      - `ICEBERG_CATALOG=sql`  (default)  SQLite + local file warehouse.
      - `ICEBERG_CATALOG=rest`            Nessie REST + MinIO (S3) —
        services defined under `warehouse` profile in docker-compose.yml.
    """
    try:
        import pyarrow as pa
        from pyiceberg.catalog import load_catalog
    except ImportError:
        print("❌ pyiceberg 미설치. `pip install -e \".[iceberg]\"` 실행 후 재시도.")
        return 1

    cfg = _build_catalog_config()
    print(f"  Catalog backend: {cfg['type']} @ {cfg.get('uri')}")
    print(f"  Warehouse:       {cfg.get('warehouse')}")
    catalog = load_catalog("skyops", **cfg)

    # Namespace
    ns = (namespace,)
    try:
        catalog.create_namespace(ns)
        print(f"  ✓ namespace '{namespace}' created")
    except Exception as e:  # noqa: BLE001
        logger.debug("namespace already exists: %s", e)

    total = 0
    for layer, tables in TABLES.items():
        if layer_filter and layer != layer_filter:
            continue
        print(f"\n── {layer.upper()} layer ──")
        for name, cols in tables.items():
            full_name = f"{namespace}.{layer}_{name}"
            # Minimal schema: all string except event_timestamp
            fields = []
            for c in cols:
                if c == "event_timestamp":
                    fields.append((c, pa.timestamp("us")))
                else:
                    fields.append((c, pa.string()))
            schema = pa.schema(fields)

            try:
                catalog.create_table(full_name, schema=schema)
                print(f"  ✓ {full_name}")
                total += 1
            except Exception as e:  # noqa: BLE001
                if "already exists" in str(e).lower():
                    print(f"  = {full_name} (already exists)")
                else:
                    logger.error("failed %s: %s", full_name, e)

    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="SkyOps Iceberg bootstrap")
    parser.add_argument("--layer", choices=["bronze", "silver", "gold"], default=None,
                        help="Only bootstrap one layer")
    parser.add_argument("--namespace", default="skyops",
                        help="Iceberg namespace (default: skyops)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 65)
    print(f"  Iceberg bootstrap  warehouse={ICEBERG_WAREHOUSE}")
    print("=" * 65)

    created = bootstrap_pyiceberg(args.layer, args.namespace)

    print("\n" + "=" * 65)
    total_tables = sum(len(t) for t in TABLES.values())
    if args.layer:
        total_tables = len(TABLES[args.layer])
    print(f"  ✅ Created/verified {created}/{total_tables} tables in namespace '{args.namespace}'")
    print("=" * 65)
    print(f"  Catalog:  {ICEBERG_WAREHOUSE}/catalog.db")
    print(f"  Warehouse: file://{ICEBERG_WAREHOUSE}")
    print("\n  Query (pyiceberg):")
    print("    from pyiceberg.catalog import load_catalog")
    print("    cat = load_catalog('skyops', type='sql',")
    print(f"                       uri='sqlite:///{ICEBERG_WAREHOUSE}/catalog.db',")
    print(f"                       warehouse='file://{ICEBERG_WAREHOUSE}')")
    print("    tbl = cat.load_table('skyops.silver_flight_features')")
    print("    df = tbl.scan().to_pandas()")
    return 0


if __name__ == "__main__":
    sys.exit(main())
