# OpenLineage / Marquez Evidence (P8-E · 2026-04-15)

## 🎯 목적

"dataset → model → deployment" 의 lineage 그래프가 실제로 연결되어 보임을 증명.

## 🚀 Marquez 실행

```bash
docker compose -f docker-compose.prod.yml --profile lineage up -d

# 30초 후 Postgres 초기화 확인
docker compose -f docker-compose.prod.yml logs marquez | grep "Started Marquez"

# UI: http://localhost:3000  (Next.js 대시보드 3000 이 먼저 잡혀있으면 down 시키거나 포트 변경)
```

## 🌱 이벤트 생성

```bash
# 1. XGBoost 학습 (OL START/COMPLETE 자동 emit)
OPENLINEAGE_URL=http://localhost:5000 \
  skyops-train-xgb --trials 5

# 2. Feature engineering (feature_engineering.py 실행 시 emit)
OPENLINEAGE_URL=http://localhost:5000 \
  python analysis/feature_engineering.py

# 3. 인퍼런스 로그 (serving)
OPENLINEAGE_URL=http://localhost:5000 \
  ICEBERG_ENABLED=1 \
  skyops-api --port 8000
# 몇 건 /predict/delay 요청 후 → Gold inference_log 에 lineage event 남김
```

## 📊 확인 — Marquez API

```bash
# Namespace
curl -s http://localhost:5000/api/v1/namespaces | jq '.namespaces[] | .name'
# → "skyops"

# Jobs
curl -s 'http://localhost:5000/api/v1/namespaces/skyops/jobs?limit=10' | jq '.jobs[] | {name,type,updatedAt}'
# → xgboost_delay_train · feature_engineering

# Datasets
curl -s 'http://localhost:5000/api/v1/namespaces/skyops/datasets' | jq '.datasets[] | .name'
# → silver_flight_features · bronze_flight_position_raw · gold_inference_log ...

# Runs for a specific job (inputs + outputs)
curl -s 'http://localhost:5000/api/v1/namespaces/skyops/jobs/xgboost_delay_train/runs' \
  | jq '.runs[0] | {state, facets: .runFacets, inputs: [.inputs[]?.name], outputs: [.outputs[]?.name]}'
```

## 🖼️ UI screenshot 체크리스트

1. **Jobs page** — `xgboost_delay_train` + `feature_engineering` 존재
2. **Datasets page** — Bronze/Silver/Gold tables 존재 (namespace: skyops)
3. **Graph view** — xgboost_delay_train 의 input → output 연결 보임:
   ```
   silver_flight_features ──► xgboost_delay_train ──► gold_inference_log
   ```
4. **Run facets** — `skyops_model` 커스텀 facet 에 model_version + metrics 들어있음

## 🧪 Evidence 저장

```bash
# Graph PNG export (Marquez UI → graph 우상단 📷)
# 저장 경로: docs/evidence/lineage/graph-YYYYMMDD.png

# API 응답도 archive
mkdir -p docs/evidence/lineage/api-snapshots
curl -s http://localhost:5000/api/v1/namespaces/skyops/jobs \
  > docs/evidence/lineage/api-snapshots/jobs-$(date +%Y%m%d).json
curl -s http://localhost:5000/api/v1/namespaces/skyops/datasets \
  > docs/evidence/lineage/api-snapshots/datasets-$(date +%Y%m%d).json
```
