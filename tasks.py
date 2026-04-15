"""SkyOps Intelligence — Cross-platform task runner (P6-H · 2026-04-15).

Mirror of Makefile for Windows where `make` may be missing.
Python is the only hard dependency.

Usage:
    python tasks.py                # list targets
    python tasks.py setup
    python tasks.py train-quick
    python tasks.py smoke
    python tasks.py up
    python tasks.py obs

Each target is a thin wrapper around shell commands. Stops on first
non-zero exit. PYTHONIOENCODING=utf-8 is set automatically on Windows.
"""
from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
import sys
from typing import Callable

# Force UTF-8 stdout on Windows
if platform.system() == "Windows":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

PYTHON = sys.executable


def sh(cmd: str, env: dict | None = None) -> int:
    """Run cmd in a subshell, stream output, return exit code."""
    print(f"  $ {cmd}")
    full_env = {**os.environ, **(env or {})}
    return subprocess.call(cmd, shell=True, env=full_env)


# ─────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────
def setup() -> int:
    """Editable install with serving + ml + otel + pipeline + dev"""
    return sh(f'"{PYTHON}" -m pip install -e ".[serving,otel,pipeline,ml,rag,eval,dev]"')


def setup_all() -> int:
    """Editable install with [all] extras (incl. feast, schema, iceberg)"""
    return sh(f'"{PYTHON}" -m pip install -e ".[all,dev]"')


# ─────────────────────────────────────────────────────────────────────
# Data + Models
# ─────────────────────────────────────────────────────────────────────
def features() -> int:
    """Build features.parquet (5.7M rows) + train/val/test split"""
    rc = sh(f'"{PYTHON}" analysis/feature_engineering.py')
    if rc:
        return rc
    return sh(f'"{PYTHON}" analysis/prepare_dataset.py')


def train_quick() -> int:
    """XGBoost with 5 Optuna trials (~1m)"""
    return sh(f'"{PYTHON}" analysis/xgboost_model.py --trials 5')


def train() -> int:
    """XGBoost with 30 Optuna trials (~5m)"""
    return sh(f'"{PYTHON}" analysis/xgboost_model.py --trials 30')


def conformal() -> int:
    return sh(f'"{PYTHON}" analysis/conformal_calibration.py --mode split')


def cqr() -> int:
    rc = sh(f'"{PYTHON}" analysis/quantile_regression.py --alpha 0.1')
    if rc:
        return rc
    return sh(f'"{PYTHON}" analysis/conformal_calibration.py --mode cqr')


def ml_phase() -> int:
    return sh(f'"{PYTHON}" analysis/ml_phase_classifier.py --n-samples 200000')


def per_phase_if() -> int:
    return sh(f'"{PYTHON}" analysis/per_phase_isolation_forest.py --n-samples 30000')


def chromadb() -> int:
    return sh(f'"{PYTHON}" serving/04_build_vectordb.py --reset --show-stats')


# ─────────────────────────────────────────────────────────────────────
# P6 · Feature Store + Schema + Iceberg
# ─────────────────────────────────────────────────────────────────────
def feast_apply() -> int:
    return sh(f'"{PYTHON}" -m feature_store.apply')


def feast_mat() -> int:
    return sh(f'"{PYTHON}" -m feature_store.materialize --lookback-days 7')


def iceberg_init() -> int:
    return sh(f'"{PYTHON}" -m feature_store.iceberg_bootstrap')


def schema_list() -> int:
    return sh(f'"{PYTHON}" -m pipeline.schema_registry list')


def schema_register() -> int:
    url = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
    return sh(f'"{PYTHON}" -m pipeline.schema_registry register-all --registry-url {url}')


# ─────────────────────────────────────────────────────────────────────
# Test + Lint
# ─────────────────────────────────────────────────────────────────────
def smoke() -> int:
    """In-process FastAPI smoke test (5 endpoints)"""
    code = """
import sys, importlib.util
sys.path.insert(0, 'serving')
spec = importlib.util.spec_from_file_location('api', 'serving/api.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
from fastapi.testclient import TestClient
c = TestClient(mod.app)
print('/health   :', c.get('/health').json())
print('/notam    :', len(c.get('/notam/recent').json()), 'items')
print('/al/next  :', c.get('/active-learning/next?top_k=3').json())
print('/aircraft :', len(c.get('/aircraft/live').json()), 'aircraft')
"""
    return sh(f'"{PYTHON}" -c "{code.strip().replace(chr(10), "; ")}"',
              env={"OTEL_ENABLED": "0"})


def lint() -> int:
    return sh("ruff check .")


def fmt() -> int:
    return sh("ruff format .")


# ─────────────────────────────────────────────────────────────────────
# Docker / k8s
# ─────────────────────────────────────────────────────────────────────
def up() -> int:
    rc = sh("docker compose up -d")
    if rc == 0:
        print("\n  Kafka UI: http://localhost:8080")
    return rc


def nas_up() -> int:
    """Launch NAS-optimized low-memory stack (no vLLM, 1.8GB total)."""
    rc = sh("docker compose -f docker-compose.nas.yml up -d")
    if rc == 0:
        print("\n  API:       http://<NAS-IP>:8000/docs")
        print("  Dashboard: http://<NAS-IP>:3000")
        print("  Grafana:   http://<NAS-IP>:3001  (admin/skyops)")
    return rc


def nas_down() -> int:
    return sh("docker compose -f docker-compose.nas.yml down")


def nas_logs() -> int:
    return sh("docker compose -f docker-compose.nas.yml logs -f --tail 100")


def evidence_drift() -> int:
    """Generate drift alert evidence bundle."""
    return sh(f'"{PYTHON}" docs/evidence/drift_alert/evidently_drift_demo.py')


def evidence_load() -> int:
    """Run k6 load test (requires k6 installed)."""
    return sh("k6 run docs/evidence/load_test/k6_delay_prediction.js")


def dr_drill() -> int:
    """Run DR drill (local mode, dry-run)."""
    return sh("bash docs/runbooks/dr_drill.sh local --dry-run")


def helm_lint() -> int:
    """Helm chart syntax check per environment."""
    rc = 0
    for env in ["dev", "staging", "prod"]:
        r = sh(f"helm lint k8s/helm/skyops -f k8s/helm/skyops/values.{env}.yaml")
        if r != 0:
            rc = r
    return rc


def helm_template_dev() -> int:
    """Render Helm templates for dev env (dry-run)."""
    return sh("helm template skyops k8s/helm/skyops -f k8s/helm/skyops/values.dev.yaml")


def up_prod() -> int:
    rc = sh("docker compose -f docker-compose.prod.yml up -d")
    if rc == 0:
        print("\n  API:       http://localhost:8000  (Swagger /docs)")
        print("  Dashboard: http://localhost:3000")
    return rc


def obs() -> int:
    rc = sh("docker compose -f docker-compose.prod.yml --profile observability up -d")
    if rc == 0:
        print("\n  Jaeger:     http://localhost:16686")
        print("  Prometheus: http://localhost:9090")
        print("  Grafana:    http://localhost:3001  (admin / skyops)")
    return rc


def schema_up() -> int:
    rc = sh("docker compose --profile schema up -d schema-registry")
    if rc == 0:
        print("\n  Schema Registry: http://localhost:8081")
    return rc


def down() -> int:
    sh("docker compose down")
    return sh("docker compose -f docker-compose.prod.yml down")


def k8s_smoke() -> int:
    rc = sh("kubectl apply -f k8s/local/redis-only.yaml")
    if rc:
        return rc
    rc = sh("kubectl wait --for=condition=ready pod -n skyops-local -l app=redis --timeout=120s")
    if rc:
        return rc
    return sh("kubectl run smoke-test --image=redis:7.2-alpine -n skyops-local "
              "--restart=Never --rm -i --tty=false --command -- redis-cli -h redis ping")


# ─────────────────────────────────────────────────────────────────────
# Streaming
# ─────────────────────────────────────────────────────────────────────
def opensky() -> int:
    return sh(f'"{PYTHON}" pipeline/opensky_producer.py')


def metar() -> int:
    return sh(f'"{PYTHON}" pipeline/metar_producer.py')


def swim() -> int:
    return sh(f'"{PYTHON}" pipeline/swim_subscriber.py',
              env={"SWIM_TRUSTSTORE_PATH": "./data/secrets/swim_trust"})


def notam_mock() -> int:
    return sh(f'"{PYTHON}" pipeline/notam_producer.py',
              env={"NOTAM_MODE": "mock"})


def atfm_mock() -> int:
    return sh(f'"{PYTHON}" pipeline/atfm_producer.py',
              env={"ATFM_MODE": "mock"})


# ─────────────────────────────────────────────────────────────────────
# Active Learning
# ─────────────────────────────────────────────────────────────────────
def al_report() -> int:
    return sh(f'"{PYTHON}" analysis/active_learning.py')


def al_retrain() -> int:
    return sh(f'"{PYTHON}" -m analysis.active_learning_retrain')


def al_retrain_dry() -> int:
    return sh(f'"{PYTHON}" -m analysis.active_learning_retrain --dry-run')


# ─────────────────────────────────────────────────────────────────────
# Eval
# ─────────────────────────────────────────────────────────────────────
def ragas_bench() -> int:
    return sh(f'"{PYTHON}" -m evaluation.ragas_bench --n 30 --judge proxy')


# ─────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────
def clean() -> int:
    """Remove __pycache__, .pyc, .pytest_cache"""
    from pathlib import Path
    root = Path(__file__).resolve().parent
    n = 0
    for p in root.rglob("__pycache__"):
        if "node_modules" in p.parts or ".venv" in p.parts:
            continue
        shutil.rmtree(p, ignore_errors=True)
        n += 1
    for p in root.rglob("*.pyc"):
        p.unlink(missing_ok=True)
        n += 1
    print(f"  removed {n} cache items")
    return 0


# ─────────────────────────────────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────────────────────────────────
TARGETS: dict[str, tuple[Callable[[], int], str]] = {
    # Setup
    "setup":             (setup,             "Editable install with main extras"),
    "setup-all":         (setup_all,         "Editable install with [all] extras"),
    # Data + Models
    "features":          (features,          "Build features.parquet (5.7M)"),
    "train-quick":       (train_quick,       "XGBoost 5 trials (~1m)"),
    "train":             (train,             "XGBoost 30 trials (~5m)"),
    "conformal":         (conformal,         "Calibrate split conformal"),
    "cqr":               (cqr,               "Quantile + CQR calibration"),
    "ml-phase":          (ml_phase,          "Train ML phase classifier"),
    "per-phase-if":      (per_phase_if,      "Train 7 per-phase IF"),
    "chromadb":          (chromadb,          "Rebuild ChromaDB"),
    # P6 · Feature Store / Schema / Iceberg
    "feast-apply":       (feast_apply,       "Register Feast feature views + seed parquet"),
    "feast-mat":         (feast_mat,         "Materialize offline → online (Redis)"),
    "iceberg-init":      (iceberg_init,      "Bootstrap Bronze/Silver/Gold tables"),
    "schema-list":       (schema_list,       "List Avro schemas"),
    "schema-register":   (schema_register,   "Register schemas to Confluent SR"),
    # Test + Lint
    "smoke":             (smoke,             "In-process FastAPI smoke test"),
    "lint":              (lint,              "ruff check"),
    "fmt":               (fmt,               "ruff format"),
    # Docker / k8s
    "up":                (up,                "docker compose up -d (dev)"),
    "up-prod":           (up_prod,           "docker compose -f docker-compose.prod.yml up -d"),
    "obs":               (obs,               "+observability profile"),
    "schema-up":         (schema_up,         "+schema profile"),
    "down":              (down,              "Stop everything"),
    "k8s-smoke":         (k8s_smoke,         "kubectl apply local Redis smoke"),
    # P8 · NAS + IaC + evidence
    "nas-up":            (nas_up,            "P8-C: low-memory NAS stack up"),
    "nas-down":          (nas_down,          "P8-C: NAS stack down"),
    "nas-logs":          (nas_logs,          "P8-C: NAS stack logs -f"),
    "helm-lint":         (helm_lint,         "P8-D: helm lint all envs (dev/staging/prod)"),
    "helm-template-dev": (helm_template_dev, "P8-D: helm template for dev (dry-run)"),
    "evidence-drift":    (evidence_drift,    "P8-E: drift alert demo"),
    "evidence-load":     (evidence_load,     "P8-E: k6 load test (needs k6)"),
    "dr-drill":          (dr_drill,          "P8-H: DR drill local dry-run"),
    # Streaming
    "opensky":           (opensky,           "OpenSky ADS-B producer"),
    "metar":             (metar,             "NOAA/KMA METAR producer"),
    "swim":              (swim,              "FAA SWIM subscriber (real)"),
    "notam-mock":        (notam_mock,        "NOTAM mock producer"),
    "atfm-mock":         (atfm_mock,         "ATFM mock producer"),
    # Active Learning
    "al-report":         (al_report,         "Analyze feedback.jsonl"),
    "al-retrain":        (al_retrain,        "Run retrain loop"),
    "al-retrain-dry":    (al_retrain_dry,    "Dry-run retrain loop"),
    # Eval
    "ragas-bench":       (ragas_bench,       "RAGAs benchmark (proxy)"),
    # Cleanup
    "clean":             (clean,             "Remove __pycache__/*.pyc"),
}


def help_msg() -> int:
    # Plain ASCII so it prints on Windows cp949 without PYTHONIOENCODING set.
    print("SkyOps Intelligence -- task runner (Python, cross-platform)")
    print("Equivalent to Makefile, see also `make help`.\n")
    print(f"  Usage: {sys.executable} tasks.py <target>\n")
    print(f"  {'Target':<22}  Description")
    print(f"  {'-' * 22:<22}  {'-' * 50}")
    for name, (_, desc) in TARGETS.items():
        print(f"  {name:<22}  {desc}")
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        return help_msg()
    target = sys.argv[1]
    if target not in TARGETS:
        print(f"!! Unknown target: {target}\n")
        return help_msg() or 1
    fn, _desc = TARGETS[target]
    rc = fn()
    if rc:
        print(f"!! {target} failed (exit {rc})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
