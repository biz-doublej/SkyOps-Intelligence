# Runbook — Incident Response Playbook (P8-H · 2026-04-15)

> P5+ RAG corpus 의 `incident_response_p1.md` 를 실전 진단 명령어로 확장.
> 각 단계는 복사-붙여넣기 바로 실행 가능.

## 🚨 Severity 등급

| 등급 | 정의 | 응답시간 |
|------|------|---------|
| **P1** (CRITICAL) | API 전체 다운, SWIM/SLO 둘 다 breach | 5분 |
| **P2** (HIGH) | 특정 endpoint 장애, p95 > 500ms 10min | 15분 |
| **P3** (MEDIUM) | 드리프트 감지, 배치 실패 | 1시간 |
| **P4** (LOW) | 로깅 이슈, 단일 pod restart 루프 | 다음 영업일 |

## 🎯 P1 — CRITICAL (사이트 다운)

### Step 0 · 알람 수신 (0~1min)
- PagerDuty / Slack `#skyops-oncall` 알람 확인
- `alertname` 확인 → 해당 섹션으로 이동

### Step 1 · 기본 진단 (1~5min)
```bash
# Grafana 대시보드 확인
open http://skyops-grafana:3001/d/skyops-slo-v1

# 영향 범위
kubectl get pods -n skyops -o wide
kubectl get events -n skyops --sort-by='.lastTimestamp' | head -20

# Health 체크
curl -m 5 https://api.skyops.io/health | jq
# 실패 → step 2a
# 200 이지만 models/feast/iceberg 중 false → step 2b
```

### Step 2a · API 다운 (health timeout)
```bash
# Pod 상태
kubectl describe pods -n skyops -l app=skyops-api | head -40

# 리소스 부족?
kubectl top pods -n skyops
kubectl top nodes

# OOM?
kubectl logs -n skyops -l app=skyops-api --tail=100 --previous | grep -i "killed\|oom"

# 이미지 pull 실패?
kubectl get events -n skyops --field-selector reason=Failed

# 복구 액션:
# (a) 최근 배포가 원인 → 롤백
kubectl rollout undo deployment/skyops-api -n skyops
# 또는 Argo Rollouts:
kubectl argo rollouts abort skyops-api -n skyops

# (b) 노드 장애 → 다른 노드로 재스케줄
kubectl cordon <bad-node>
kubectl drain <bad-node> --ignore-daemonsets --delete-emptydir-data

# (c) HPA 부족 → 수동 스케일
kubectl scale deployment/skyops-api -n skyops --replicas=8
```

### Step 2b · 부분 장애 (models 중 하나 false)
```bash
# 어느 모델? /health 응답 보고 target:
HEALTH=$(curl -s https://api.skyops.io/health)
echo "$HEALTH" | jq '.models'

# xgboost: false → 모델 파일 누락 또는 PVC 언마운트
kubectl exec -n skyops deploy/skyops-api -- ls -la /app/data/models/
# 복구: PVC remount + rollout restart
kubectl rollout restart deployment/skyops-api -n skyops

# iceberg: loaded=false → catalog 접근 불가
kubectl logs -n skyops deploy/skyops-api | grep -i iceberg
# SQLite catalog 파일? Glue endpoint? → 복구 후 재시작

# feast: loaded=false → Redis db=1 접근 불가
kubectl exec -n skyops deploy/skyops-api -- redis-cli -h skyops-redis -n 1 ping
# PONG 안 오면 Redis 재시작
```

### Step 3 · 롤백 vs 복구 결정 (5~10min)
```bash
# 최근 5 릴리스 히스토리
kubectl rollout history deployment/skyops-api -n skyops

# 직전 2 릴리스와 차이
kubectl rollout history deployment/skyops-api -n skyops --revision=<N>
kubectl rollout history deployment/skyops-api -n skyops --revision=<N-1>

# → 최근 배포가 원인일 가능성 높으면 (< 15분 전 배포 + 알람 시작 시간 일치)
#   즉시 롤백:
kubectl rollout undo deployment/skyops-api -n skyops

# → 아니면 (외부 요인: FAA SWIM outage, DB 장애 등)
#   외부 대응 (step 4)
```

### Step 4 · 외부 의존성 확인
```bash
# FAA SWIM
kubectl logs -n skyops -l app=skyops-swim-subscriber --tail=100 | grep -E "error|failed|untrust"
# SOLCLIENT_SUBCODE_* → docs/runbooks/swim_outage.md 참조

# Redis
kubectl exec -n skyops deploy/skyops-redis -- redis-cli info stats | head -10

# vLLM (옵션)
curl -m 5 http://vllm:8001/v1/models
# 404 → LLM_MODE=fallback 활성화:
kubectl set env deployment/skyops-api -n skyops LLM_MODE=fallback
```

### Step 5 · 상황 전파 (5min 이내, parallel)
- Slack `#skyops-incidents` — 상황 + ETA
- Status page (있으면) — "investigating"
- 관제사/파트너에게 공지 (실 서비스만)
- **HITL 승인 대기 중인 advisory 는 manual hold** (broadcast 중단)

### Step 6 · 복구 확인 + Postmortem (1h 내)
```bash
# 복구 확인
curl https://api.skyops.io/health | jq '.status'
kubectl get pods -n skyops
# Grafana 에서 error rate < 0.1% 확인
```

**Postmortem 템플릿** (blameless):
```markdown
# Postmortem — 2026-04-15 API Outage

## Summary (1줄)
- 2026-04-15 14:23~14:41 UTC — /predict/delay 503 응답, p95 무제한.

## Impact
- 18분 서비스 장애, ~1200 request 실패

## Timeline
- 14:23 — 알람
- 14:25 — on-call engineer 수신, 초기 진단
- 14:28 — 롤백 결정
- 14:31 — 롤백 완료
- 14:41 — 완전 복구 확인

## Root cause
- (blameless) 신 릴리스가 XGBoost 2.1.0 wheel 요구, runtime 은 2.0 설치
- pyproject requirements 업데이트 누락

## Lessons
- integration test 에서 모델 로드 smoke test 추가 → PR #XYZ
- Canary 단계에서 /health.models.xgboost=false 시 auto-abort

## Action items
- [ ] ML team — requirements.txt lock 강화 (pip-tools)
- [ ] SRE — AnalysisTemplate 에 /health sub-check 추가
```

## ⚠️ P2 — HIGH (SLO breach)

### p95 latency > 500ms / 10min
```bash
# 1. 어느 handler가 느린가?
kubectl exec -n skyops deploy/skyops-prometheus -- \
  curl -s 'http://localhost:9090/api/v1/query?query=skyops:http_request_latency_seconds:p95_5m' \
  | jq '.data.result[] | {handler: .metric.handler, p95: .value[1]}'

# 2. Jaeger 에서 slowest trace
open http://skyops-jaeger:16686
# service=skyops-api, operation=/predict/delay, duration > 500ms

# 3. 흔한 원인:
# (a) Conformal calibrator 무거움 → 캐시 리로드
# (b) XGBoost 모델 재로드 반복 → ModelStore singleton 확인
# (c) Redis slow command → kubectl exec -n skyops deploy/skyops-redis -- redis-cli slowlog get 10
# (d) GC pause → kubectl logs | grep "GC took"

# 4. 단기 mitigation — 트래픽 제한
kubectl annotate ingress/skyops-ingress -n skyops \
  traefik.ingress.kubernetes.io/router.middlewares=skyops-ratelimit@kubernetescrd
```

## 📉 P3 — MEDIUM (Drift alert)

```bash
# Evidently 최신 report 확인
python -c "
import json, pathlib
r = json.loads(pathlib.Path('data/results/drift_report.json').read_text())
print(json.dumps({k: r[k] for k in ('dataset_drift','drift_share','method')}, indent=2))
"

# 조치 판단:
# drift_share > 0.5 → 긴급 재학습
make train && make conformal
# drift_share < 0.5 → 모니터링 강화, 주말 재학습

# Active Learning 상태 확인
skyops-active-learning   # feedback 분석 리포트 생성
cat data/results/active_learning_report.md | head -30
```

## 🧪 DR drill (반기 1회)

`docs/runbooks/dr_drill.sh` 자동화. 시나리오:
1. KR region 전체 down 시뮬레이션 (kubectl cordon all)
2. EU read replica 승격 (failover)
3. 15분 내 read traffic 회복 확인
4. KR 복구 후 catchup replication 검증

## 📚 참조

- `docs/runbooks/model_retrain.md` — XGBoost 재학습 체크리스트
- `docs/runbooks/swim_outage.md` — FAA SWIM 장애 대응
- `docs/runbooks/secret_rotation.md` — 비밀 교체 playbook
- `docs/runbooks/supply_chain.md` — 이미지 서명 + SBOM
- `data/icao/corpus/runbook/incident_response_p1.md` — RAG용 원본
