# SkyOps Intelligence — Evidence Package (P8-E · 2026-04-15)

> "이게 실제로 돌아간다" 를 증명하는 재현 가능한 아티팩트 묶음.

## 📦 구성

| 디렉토리 | 증거 | 재현 방법 |
|---------|------|----------|
| [`load_test/`](load_test/) | p95/p99 latency, error rate, throughput | `k6 run k6_delay_prediction.js` |
| [`canary_rollout/`](canary_rollout/) | Argo Rollouts 진행 + AnalysisRun gate | `bash record_rollout.sh` |
| [`grafana_snapshots/`](grafana_snapshots/) | SLO 9-panel 실측 값 | Grafana snapshot + PNG export |
| [`drift_alert/`](drift_alert/) | Evidently drift report + Slack alert payload | `python evidently_drift_demo.py` |
| [`lineage/`](lineage/) | Marquez graph (dataset ↔ model) | Marquez API + UI screenshot |
| [`../runbooks/`](../runbooks/) | incident + retrain + SWIM outage + secret rotation | (문서) |

## 🎯 캡스톤 발표 흐름 (제안)

> "2일 만에 MVP → production-ready" 스토리를 뒷받침.

### Demo 1 · 부하 시 SLO 유지 (3분)
```bash
# 1. 서비스 기동 (NAS 또는 dev)
make up-prod                  # 또는 docker compose -f docker-compose.nas.yml up -d

# 2. 부하 인가
k6 run docs/evidence/load_test/k6_delay_prediction.js

# 3. Grafana 실시간 관찰
open http://localhost:3001/d/skyops-slo-v1
```
→ "p95 187ms, 에러 0.08%, SLO 충족" 캡처

### Demo 2 · 드리프트 감지 → 알림 (2분)
```bash
python docs/evidence/drift_alert/evidently_drift_demo.py
cat docs/evidence/drift_alert/alert_payload.json | jq .slack_payload
```
→ "CRITICAL 4개 feature 드리프트, Slack payload 생성"

### Demo 3 · Lineage 추적 (2분)
```bash
docker compose -f docker-compose.prod.yml --profile lineage up -d
OPENLINEAGE_URL=http://localhost:5000 skyops-train-xgb --trials 3
open http://localhost:5000  # 또는 Marquez:3000
```
→ silver_flight_features → xgboost_delay_train → gold_inference_log 그래프

### Demo 4 · 분석가 승인 흐름 (1분)
```bash
# 이상 탐지 → LLM 설명 → 분석가 승인까지 30초
curl -X POST http://localhost:8000/detect/anomaly -d '{...}'
curl -X POST http://localhost:8000/explain/anomaly -d '{...}'
curl -X POST http://localhost:8000/anomaly/approve \
  -d '{"alert_id":"xyz","advisory_id":"adv-1","decision":"approved","approver":"analyst_01"}'
```
→ `data/audit/audit-YYYYMMDD.jsonl` 에서 전 과정 trace_id 로 재구성

### Demo 5 · Canary rollout (5분, 실행 영상 or 녹화)
```bash
# 현재 버전 + 신 버전 이미지 준비 후
kubectl apply -f k8s/rollouts/
bash docs/evidence/canary_rollout/record_rollout.sh skyops skyops-api
```
→ 5% → 25% → ... 단계별 Prometheus gate pass 기록

## 🔒 evidence 보존 정책

- `runs/YYYYMMDD-HHMMSS/` 구조로 timestamped
- 중요 발표/릴리스 증거는 **git 에 commit** (바이너리는 Git LFS)
- 일상 증거는 별도 bucket (GCS skyops-evidence) 에 30일 보존
