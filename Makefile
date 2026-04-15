# SkyOps Intelligence — Makefile (P6-H · 2026-04-15)
# ============================================================================
# Engineering Package 마감 — 한 명령어로 setup / train / test / serve / clean.
# Strategic Review #9 closure.
#
# Usage:
#   make help               # show all targets
#   make setup              # install editable + ML extras
#   make train-quick        # 5-trial XGBoost smoke
#   make smoke              # FastAPI in-process smoke test
#   make up                 # docker compose up (dev)
#   make obs                # +profile observability (Jaeger/Prom/Grafana)
#   make swim-trust         # bootstrap c_rehash trust store for FAA SWIM

PYTHON := python
PIP := pip
DOCKER_COMPOSE := docker compose
PROFILE_OBS := --profile observability
PROFILE_SCHEMA := --profile schema

# Set UTF-8 on Windows by default
ifeq ($(OS),Windows_NT)
	export PYTHONIOENCODING := utf-8
endif

.PHONY: help
help:
	@echo "SkyOps Intelligence — Make targets"
	@echo ""
	@echo "  Setup"
	@echo "    setup           Editable install with serving + ml + otel + pipeline"
	@echo "    setup-all       Editable install with [all] (everything incl. feast/iceberg)"
	@echo ""
	@echo "  Data + Models"
	@echo "    features        Build features.parquet (5.7M rows)"
	@echo "    train-quick     XGBoost with 5 Optuna trials (~1m)"
	@echo "    train           XGBoost with 30 Optuna trials (~5m)"
	@echo "    conformal       Calibrate split conformal"
	@echo "    cqr             Calibrate Conformalized Quantile Regression"
	@echo "    ml-phase        Train ML phase classifier (silver-label)"
	@echo "    per-phase-if    Train 7 per-phase Isolation Forests"
	@echo "    chromadb        Rebuild ChromaDB from data/icao/corpus/"
	@echo ""
	@echo "  Feature Store + Schema (P6)"
	@echo "    feast-apply     Register Feast feature views + seed demo parquet"
	@echo "    feast-mat       Materialize offline → online (Redis)"
	@echo "    iceberg-init    Bootstrap Bronze/Silver/Gold tables"
	@echo "    schema-list     List Avro schemas"
	@echo "    schema-register Register all schemas to Confluent SR"
	@echo ""
	@echo "  Test + Lint"
	@echo "    smoke           FastAPI in-process smoke test"
	@echo "    lint            ruff check"
	@echo "    fmt             ruff format"
	@echo ""
	@echo "  Docker / k8s"
	@echo "    up              docker compose up -d (dev: kafka+redis+ui)"
	@echo "    up-prod         docker compose -f docker-compose.prod.yml up -d"
	@echo "    obs             +observability profile (Jaeger/Prom/Grafana)"
	@echo "    schema-up       +schema profile (Confluent Schema Registry)"
	@echo "    down            Stop everything"
	@echo "    k8s-smoke       kubectl apply local Redis smoke test"
	@echo ""
	@echo "  Streaming producers"
	@echo "    opensky         OpenSky ADS-B producer (한반도)"
	@echo "    metar           NOAA/KMA METAR producer"
	@echo "    swim-trust      Bootstrap c_rehash trust store for FAA SWIM"
	@echo "    swim            Run swim_subscriber (real FAA NOTAM)"
	@echo "    notam-mock      NOTAM mock producer"
	@echo "    atfm-mock       ATFM mock producer"
	@echo ""
	@echo "  Active Learning"
	@echo "    al-report       Analyze feedback.jsonl"
	@echo "    al-retrain      Run retrain loop (use --dry-run to test)"
	@echo ""
	@echo "  Eval"
	@echo "    ragas-bench     RAGAs benchmark (proxy mode)"
	@echo ""
	@echo "  Cleanup"
	@echo "    clean           Remove .pyc, __pycache__, .pytest_cache"
	@echo "    clean-models    Remove all .pkl files in data/models/ (dangerous)"

# ── Setup ────────────────────────────────────────────────────────────
.PHONY: setup setup-all
setup:
	$(PIP) install -e ".[serving,otel,pipeline,ml,rag,eval,dev]"

setup-all:
	$(PIP) install -e ".[all,dev]"

# ── Data + Models ────────────────────────────────────────────────────
.PHONY: features train-quick train conformal cqr ml-phase per-phase-if chromadb
features:
	$(PYTHON) analysis/feature_engineering.py
	$(PYTHON) analysis/prepare_dataset.py

train-quick:
	$(PYTHON) analysis/xgboost_model.py --trials 5

train:
	$(PYTHON) analysis/xgboost_model.py --trials 30

conformal:
	$(PYTHON) analysis/conformal_calibration.py --mode split

cqr:
	$(PYTHON) analysis/quantile_regression.py --alpha 0.1
	$(PYTHON) analysis/conformal_calibration.py --mode cqr

ml-phase:
	$(PYTHON) analysis/ml_phase_classifier.py --n-samples 200000

per-phase-if:
	$(PYTHON) analysis/per_phase_isolation_forest.py --n-samples 30000

chromadb:
	$(PYTHON) serving/04_build_vectordb.py --reset --show-stats

# ── P6 · Feature Store + Schema + Iceberg ────────────────────────────
.PHONY: feast-apply feast-mat iceberg-init schema-list schema-register
feast-apply:
	$(PYTHON) -m feature_store.apply

feast-mat:
	$(PYTHON) -m feature_store.materialize --lookback-days 7

iceberg-init:
	$(PYTHON) -m feature_store.iceberg_bootstrap

schema-list:
	$(PYTHON) -m pipeline.schema_registry list

schema-register:
	$(PYTHON) -m pipeline.schema_registry register-all \
		--registry-url $${SCHEMA_REGISTRY_URL:-http://localhost:8081}

# ── Test + Lint ──────────────────────────────────────────────────────
.PHONY: smoke lint fmt
smoke:
	OTEL_ENABLED=0 $(PYTHON) -c "\
import sys, importlib.util; \
sys.path.insert(0, 'serving'); \
spec = importlib.util.spec_from_file_location('api', 'serving/api.py'); \
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); \
from fastapi.testclient import TestClient; \
c = TestClient(mod.app); \
print('  /health:', c.get('/health').json()); \
print('  /notam/recent:', len(c.get('/notam/recent').json()), 'items'); \
print('  /active-learning/next:', c.get('/active-learning/next?top_k=3').json()); \
print('  /aircraft/live:', len(c.get('/aircraft/live').json()), 'aircraft')"

lint:
	ruff check .

fmt:
	ruff format .

# ── Docker / k8s ─────────────────────────────────────────────────────
.PHONY: up up-prod obs schema-up down k8s-smoke
up:
	$(DOCKER_COMPOSE) up -d
	@echo "Kafka UI: http://localhost:8080"

up-prod:
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml up -d
	@echo "API:       http://localhost:8000  (Swagger /docs)"
	@echo "Dashboard: http://localhost:3000"

obs:
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml $(PROFILE_OBS) up -d
	@echo "Jaeger:     http://localhost:16686"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana:    http://localhost:3001  (admin / skyops)"

schema-up:
	$(DOCKER_COMPOSE) $(PROFILE_SCHEMA) up -d schema-registry
	@echo "Schema Registry: http://localhost:8081"
	@sleep 5
	@$(PYTHON) -m pipeline.schema_registry register-all || true

down:
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml down 2>/dev/null || true

k8s-smoke:
	kubectl apply -f k8s/local/redis-only.yaml
	kubectl wait --for=condition=ready pod -n skyops-local -l app=redis --timeout=120s
	kubectl run smoke-test --image=redis:7.2-alpine -n skyops-local \
		--restart=Never --rm -i --tty=false --command -- redis-cli -h redis ping

# ── Streaming ────────────────────────────────────────────────────────
.PHONY: opensky metar swim-trust swim notam-mock atfm-mock
opensky:
	$(PYTHON) pipeline/opensky_producer.py

metar:
	$(PYTHON) pipeline/metar_producer.py

# Bootstrap c_rehash trust store (one-shot, idempotent)
swim-trust:
	mkdir -p data/secrets/swim_trust
	echo | openssl s_client -connect ems2.swim.faa.gov:55443 \
		-servername ems2.swim.faa.gov -showcerts 2>/dev/null \
		> data/secrets/swim_trust/full_chain.pem
	csplit -z -f data/secrets/swim_trust/cert_ -b '%02d.pem' \
		data/secrets/swim_trust/full_chain.pem '/-----BEGIN CERTIFICATE-----/' '{*}'
	curl -fsSL -o data/secrets/swim_trust/digicert_g2_root.pem \
		https://cacerts.digicert.com/DigiCertGlobalRootG2.crt.pem
	@for pem in data/secrets/swim_trust/*.pem; do \
		hash=$$(openssl x509 -in "$$pem" -noout -hash 2>/dev/null); \
		[ -n "$$hash" ] && cp "$$pem" "data/secrets/swim_trust/$${hash}.0"; \
	done
	@ls -la data/secrets/swim_trust/*.0

swim:
	SWIM_TRUSTSTORE_PATH=./data/secrets/swim_trust $(PYTHON) pipeline/swim_subscriber.py

notam-mock:
	NOTAM_MODE=mock $(PYTHON) pipeline/notam_producer.py

atfm-mock:
	ATFM_MODE=mock $(PYTHON) pipeline/atfm_producer.py

# ── Active Learning ──────────────────────────────────────────────────
.PHONY: al-report al-retrain al-retrain-dry
al-report:
	$(PYTHON) analysis/active_learning.py

al-retrain:
	$(PYTHON) -m analysis.active_learning_retrain

al-retrain-dry:
	$(PYTHON) -m analysis.active_learning_retrain --dry-run

# ── Eval ─────────────────────────────────────────────────────────────
.PHONY: ragas-bench
ragas-bench:
	$(PYTHON) -m evaluation.ragas_bench --n 30 --judge proxy

# ── Cleanup ──────────────────────────────────────────────────────────
.PHONY: clean clean-models
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

clean-models:
	@echo "DANGEROUS — removing all .pkl in data/models/ in 5s. Ctrl-C to abort."
	@sleep 5
	rm -f data/models/*.pkl
