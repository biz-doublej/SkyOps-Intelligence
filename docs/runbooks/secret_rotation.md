# Runbook — Secret Rotation (P8-D · 2026-04-15)

> 모든 SkyOps 비밀정보의 주기적 교체 절차. 유출/의심/정기 3가지 시나리오.

## 📋 Secret 인벤토리

| Key | 위치 | 교체 주기 | 소유자 |
|-----|------|----------|--------|
| `SWIM_PASSWORD` | `skyops-swim-secret` (ExternalSecrets → GCP SM) | 90일 (FAA 정책) | ops |
| `SWIM_USERNAME` | 동일 | 변경 없음 | ops |
| `KAC_API_KEY` | `skyops-kac-secret` | 180일 (정부 정책) | ops |
| `OPENAI_API_KEY` | `skyops-openai-secret` | 90일 | ml |
| `MLFLOW_TRACKING_USERNAME/PASSWORD` | `skyops-mlflow-secret` | 90일 | ml |
| `GRAFANA_ADMIN_PASSWORD` | `skyops-grafana-secret` | 60일 | sre |
| `POSTGRES_PASSWORD` (Marquez) | `skyops-marquez-db-secret` | 60일 | sre |
| TLS cert (api.skyops.io) | cert-manager 자동 | 60일 (Let's Encrypt) | 자동 |
| Redis auth (prod만) | `skyops-redis-secret` | 60일 | sre |

## 🔄 정기 교체 절차 (SWIM_PASSWORD 예시)

```bash
# 1. FAA SWIM portal 로 신규 비밀번호 발급 (manual step)
#    https://swim.aim.faa.gov/ → account → change password

# 2. GCP Secret Manager에 새 version 등록
NEW_PASSWORD='<새 비밀번호>'
echo -n "$NEW_PASSWORD" | gcloud secrets versions add swim-password \
  --project=skyops-prod \
  --data-file=-

# 3. ExternalSecrets이 15분 내 자동 sync → 확인
kubectl get externalsecret skyops-swim -n skyops -o yaml | grep lastSync

# 4. 신규 pod 만 새 비밀로 기동 (기존 pod 교체)
kubectl rollout restart deployment/skyops-api -n skyops
kubectl rollout status  deployment/skyops-api -n skyops --timeout=5m

# 5. 검증 — swim_subscriber 연결 확인
kubectl logs -n skyops -l app=skyops-swim-subscriber --tail=50 | grep "connected"

# 6. 구 version 은 grace period 후 비활성화
sleep 1h
gcloud secrets versions disable <OLD_VERSION> --secret=swim-password --project=skyops-prod
```

## 🚨 유출 의심 시 긴급 교체

```bash
# 즉시 실행 — 구 버전 destroy
gcloud secrets versions destroy <LEAKED_VERSION> --secret=swim-password \
  --project=skyops-prod

# 새 비밀 생성 + 전 파드 강제 재시작
echo -n "$NEW_PASSWORD" | gcloud secrets versions add swim-password \
  --project=skyops-prod --data-file=-

kubectl rollout restart deployment/skyops-api deployment/skyops-dashboard -n skyops
kubectl delete pod -n skyops -l app=skyops-api --grace-period=0 --force

# Audit log 에 기록
kubectl exec -n skyops deploy/skyops-api -- \
  python -c "from common.audit import audit_log; audit_log('secret_rotation_emergency','sre','SWIM_PASSWORD','completed', extra={'reason':'suspected_leak'})"

# FAA 통지 (사용자 수동)
# NDA 조건상 부정 사용 의심 시 24h 이내 FAA SWIM 운영팀 공지
```

## 📅 정기 rotation 스케줄

```yaml
# k8s/cronjobs/secret-rotation-reminder.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: secret-rotation-reminder
  namespace: skyops
spec:
  schedule: "0 9 1 */2 *"   # 매 2개월 1일 09:00
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: reminder
              image: curlimages/curl:latest
              command:
                - sh
                - -c
                - |
                  curl -X POST $SLACK_WEBHOOK \
                    -H "Content-Type: application/json" \
                    -d '{"text":"🔐 SkyOps secret rotation due: SWIM_PASSWORD, KAC_API_KEY"}'
          restartPolicy: OnFailure
```

## 🔑 ExternalSecrets Operator 설정

```yaml
# k8s/external-secrets.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: skyops-swim
  namespace: skyops
spec:
  refreshInterval: 15m
  secretStoreRef:
    name: gcp-secret-manager
    kind: ClusterSecretStore
  target:
    name: skyops-swim-secret
    creationPolicy: Owner
  data:
    - secretKey: SWIM_USERNAME
      remoteRef:
        key: swim-username
    - secretKey: SWIM_PASSWORD
      remoteRef:
        key: swim-password
```

## ✅ 검증 체크리스트

- [ ] 새 비밀 GCP SM 에 등록 확인
- [ ] ExternalSecrets lastSync 15분 이내
- [ ] 새 pod healthy
- [ ] SWIM subscriber connected
- [ ] 구 version destroy or disable
- [ ] audit log 기록 (actor, resource, outcome)
- [ ] 다음 rotation date 캘린더 등록
