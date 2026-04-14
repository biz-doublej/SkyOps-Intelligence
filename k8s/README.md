# SkyOps Intelligence — Kubernetes Manifests

ADR-001 Phase 3 배포 템플릿 (2026-04-15 P4+).

## 디렉토리 구조

| 파일 | 용도 |
|------|------|
| `namespace.yaml` | `skyops` namespace |
| `configmap.yaml` | 공통 env vars (Redis, vLLM, OTel) |
| `api-deployment.yaml` | 3 replicas, HPA (3~10), resources, liveness/readiness |
| `api-service.yaml` | ClusterIP + PVC for models/vectordb |
| `dashboard-deployment.yaml` | Next.js 대시보드, 2 replicas + Service |
| `redis-deployment.yaml` | Redis 7.2-alpine, 1 replica + Service |
| `ingress.yaml` | Traefik IngressRoute (ADR-002) + rate limit + retry middleware |

## 사전 준비

1. **Kubernetes 클러스터** — GKE / EKS / Minikube 1.30+
2. **Traefik 설치**:
   ```bash
   helm repo add traefik https://helm.traefik.io/traefik
   helm install traefik traefik/traefik \
     --namespace traefik-system --create-namespace \
     --set certResolvers.letsencrypt.email=admin@skyops.example.com
   ```
3. **이미지 빌드 & 푸시**:
   ```bash
   docker build -f Dockerfile.api -t registry.example.com/skyops/api:2.1.0 .
   docker build -f Dockerfile.dashboard -t registry.example.com/skyops/dashboard:2.1.0 .
   docker push registry.example.com/skyops/api:2.1.0
   docker push registry.example.com/skyops/dashboard:2.1.0
   ```
4. **PV 준비** — `skyops-models-pvc`, `skyops-vectordb-pvc` 에 해당하는
   Persistent Volume (EFS, Filestore, 또는 NFS) 사전 prepare.
5. **DNS 설정** — `api.skyops.example.com`, `skyops.example.com` 이
   클러스터 Ingress LoadBalancer IP를 가리키도록 A record.

## 배포

```bash
# 1. 모든 manifest 적용
kubectl apply -f k8s/

# 2. Pod 상태 확인
kubectl get pods -n skyops

# 3. Logs
kubectl logs -n skyops -l app=skyops-api --tail=100

# 4. Rollout 상태
kubectl rollout status deployment/skyops-api -n skyops

# 5. HPA 동작 확인
kubectl get hpa -n skyops
```

## 검증

```bash
# Dry-run (실제 적용 없이 syntax 검증)
kubectl apply --dry-run=client -f k8s/

# Health check
curl https://api.skyops.example.com/health

# Predict delay smoke test
curl -X POST https://api.skyops.example.com/predict/delay \
  -H "Content-Type: application/json" \
  -d '{...}'
```

## 롤백

```bash
kubectl rollout undo deployment/skyops-api -n skyops
kubectl rollout history deployment/skyops-api -n skyops
```

## SLOs (ADR-001 Phase 3)

| 서비스 | p95 Latency | Error Budget | Deploy Frequency |
|--------|-------------|--------------|------------------|
| skyops-api | < 200 ms (non-LLM) / < 5s (LLM) | 99.95% | 주 1회 |
| skyops-dashboard | < 500 ms | 99.9% | 필요 시 |

## 향후 작업 (P5+)

- **ADR-001 Phase 3 Service Decomposition**: 단일 `skyops-api` Deployment를
  6개 독립 Deployment로 분리 (api-gateway, delay-inference, anomaly, rag,
  notification, ws-broadcast)
- **Secrets**: env vars 중 민감한 것(API keys) → Sealed Secrets 또는 ExternalSecrets
- **Observability**: OTel Collector + Tempo/Jaeger + Grafana
- **Canary deployment**: Flagger + Traefik weighted routing
- **Multi-region**: primary (ap-northeast-2) + DR (us-west-1)

## 참고 문서

- [../docs/adr/ADR-001-service-decomposition.md](../docs/adr/ADR-001-service-decomposition.md)
- [../docs/adr/ADR-002-api-gateway-selection.md](../docs/adr/ADR-002-api-gateway-selection.md)
- [Traefik Kubernetes CRD docs](https://doc.traefik.io/traefik/providers/kubernetes-crd/)
