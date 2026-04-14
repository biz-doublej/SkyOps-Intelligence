# ADR-002: API Gateway Selection — Traefik for ADR-001 Phase 3

**Status**: Proposed (Phase 3 배포 직전 재검토)
**Date**: 2026-04-14
**Deciders**: DoubleJ팀 (정재원), 지도교수 조상구
**Technical Story**: [ADR-001 Service Decomposition](ADR-001-service-decomposition.md) — Phase 3 containerization 직전 단일 진입점 선택 필요.

---

## Context and Problem Statement

ADR-001 Phase 1 (2026-04-14 P3)이 완료되어 `serving/api.py` 가 **1120 → 107 라인**으로 축소되고 6개 router 모듈로 분리됐다. Phase 3에서는 이것이 6개 독립 **컨테이너/서비스** 로 분리된다:
- `api-gateway`, `delay-inference`, `anomaly`, `rag`, `notification`, `ws-broadcast`

이 시점에서 클라이언트(Next.js 대시보드, 외부 API 소비자)는 **단일 URL**만 알아야 하고, 뒤에서 서비스 분산이 이뤄져야 한다. 이를 위한 **API Gateway** 선택이 필요하다.

### 필수 요구사항
1. **HTTP + WebSocket** 동시 지원 (SkyOps는 `/ws/aircraft`, `/ws/anomalies` 사용)
2. **Kubernetes 네이티브** — Ingress 또는 IngressRoute CRD
3. **동적 서비스 발견** — 서비스 추가/제거 시 config reload 없이 반영
4. **TLS 자동화** — Let's Encrypt 자동 발급/갱신
5. **OIDC / JWT 지원** — 향후 RBAC 진입점
6. **Rate limiting + Circuit Breaker** — 운영 기본 안전장치
7. **Observability** — OpenTelemetry 통합 (ADR-001 Phase 1 P3 에서 이미 도입한 OTel과 연속성)
8. **OSS + 커뮤니티** — 한국 개발팀 유지보수 용이성

---

## Decision Drivers

- **Learning curve**: 캡스톤 팀 1인 운영 가능한 수준
- **Kubernetes-first**: Cloud Run으로도 호환되지만 k8s가 주요 타겟
- **Middleware ecosystem**: 향후 RAGAs evaluation gateway, audit log, request filtering 추가 가능
- **한국 CDN 호환**: CloudFlare / GCP 글로벌 LB 와 같이 쓸 수 있는 유연성
- **Cost**: OSS, 운영 과금 없음

---

## Considered Options

### Option 1 · NGINX
전통의 강자. C 기반, 가장 빠름.

### Option 2 · Traefik (★ Chosen)
Go 기반. Kubernetes IngressRoute CRD, 자동 discovery, Let's Encrypt 내장.

### Option 3 · 자체 FastAPI api-gateway
Python FastAPI로 직접 gateway 역할 수행. ADR-001에서 원래 제안한 방식.

### Option 4 · Cloud 매니지드 (AWS ALB, GCP Cloud Run built-in, Azure APIM)
클라우드 벤더 lock-in.

---

## Decision Outcome

**Chosen option**: **Option 2 — Traefik v3**

### 선정 이유
1. **Kubernetes IngressRoute CRD** — Helm 1-command 설치 + 서비스 annotation 기반 자동 routing
2. **WebSocket first-class support** — SkyOps의 `/ws/*` 엔드포인트 원래 어노테이션 없이 동작
3. **Let's Encrypt 자동화** — `certResolver: letsencrypt` annotation 한 줄로 TLS
4. **OpenTelemetry native** — Traefik 3.0부터 OTLP 내장, P3에서 구축한 trace와 연속성 확보
5. **Middleware chain** — ratelimit, basicauth, forwardauth(OIDC), retry, circuitbreaker 모두 CRD로 정의
6. **Dashboard UI** — `/dashboard` 에서 실시간 서비스 health 확인
7. **Migration 간단** — 기존 `serving/api.py` 그대로 두고 Traefik IngressRoute만 추가하면 됨

### 6 서비스 라우팅 예시
```yaml
# k8s/ingress.yaml (발췌)
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: skyops-api
spec:
  entryPoints: [websecure]
  routes:
    - match: Host(`api.skyops.example.com`) && PathPrefix(`/predict`)
      kind: Rule
      services:
        - name: delay-inference-service
          port: 8010
      middlewares:
        - name: ratelimit-100rpm
    - match: Host(`api.skyops.example.com`) && PathPrefix(`/detect`) || PathPrefix(`/anomaly`)
      kind: Rule
      services:
        - name: anomaly-service
          port: 8020
    - match: Host(`api.skyops.example.com`) && PathPrefix(`/chat`)
      kind: Rule
      services:
        - name: rag-service
          port: 8030
    - match: Host(`api.skyops.example.com`) && PathPrefix(`/ws`)
      kind: Rule
      services:
        - name: ws-broadcast-service
          port: 8050
  tls:
    certResolver: letsencrypt
```

### Consequences

#### Good
- ✅ **Zero-downtime service 추가**: annotation만 붙이면 routing 자동 반영
- ✅ **TLS + HTTP/2** 자동 설정
- ✅ **OTel gateway-level span** 자동 생성 → P3에서 구축한 service-level span과 end-to-end trace
- ✅ **Middleware 재사용**: rate limit / OIDC / retry 를 서비스마다 반복 정의 안 해도 됨
- ✅ **Dashboard**: 운영자 단일 UI로 routing / middleware / health 확인
- ✅ **Local dev**: Docker Compose에도 동일 config 사용 가능

#### Bad
- ❌ **Kubernetes 의존성**: 순수 VM/Docker Swarm 에서는 NGINX 대비 매력 감소
- ❌ **Custom CRD**: IngressRoute / Middleware / TLSOption 등 Traefik 고유 리소스 배워야 함
- ❌ **Performance**: NGINX 대비 순수 RPS는 ~80%. SkyOps 트래픽 규모에선 무의미하지만 high-QPS 서비스라면 재검토.
- ❌ **커뮤니티 사이즈**: NGINX 대비 작음 (하지만 k8s 생태에선 충분히 활발)

---

## Pros and Cons of the Options

### Option 1 · NGINX

**Good**:
- 업계 표준, 최고 성능
- NGINX Plus로 기업 지원 가능
- OpenResty로 Lua 확장

**Bad**:
- Kubernetes annotation 기반 config 재로드 수동
- Let's Encrypt 는 cert-manager 별도 필요
- WebSocket은 동작하지만 `Upgrade` / `Connection` 헤더 명시 필요
- OTel은 모듈 별도 컴파일 (nginx-otel)
- Dashboard UI 없음

**평가**: 성능 우위는 명확하지만 **Kubernetes + WebSocket + OTel + Let's Encrypt** 조합에서 Traefik이 ops 비용이 낮음.

### Option 2 · Traefik (★ Chosen)

**Good / Bad**: 위 Consequences 참조

**평가**: SkyOps 요구사항 7개 중 7개 충족. 러닝커브는 있으나 1인 팀 감당 가능.

### Option 3 · 자체 FastAPI api-gateway

**Good**:
- Python 생태계 통일
- `_ModelStore` / OTel setup 재사용
- 완전한 제어

**Bad**:
- ❌ TLS / Let's Encrypt 직접 구현 (termination은 k8s ingress 앞단에서 어차피 해야 함)
- ❌ Rate limit / circuit breaker 직접 작성 (별도 라이브러리: slowapi, aiocircuitbreaker)
- ❌ Config hot-reload 직접 구현
- ❌ OIDC forward-auth 직접 구현
- ❌ **Engineering overhead 큼**: 검증된 gateway 쓰지 않고 재발명
- ❌ Python GIL 아래에서 대규모 요청 fan-out 병목

**평가**: "ADR-001 원안"이었지만, 실제로 gateway는 **solved problem**. Traefik/NGINX를 무시하고 Python으로 재발명하는 것은 팀 리소스 낭비. **거부**.

### Option 4 · Cloud 매니지드

**Good**:
- 관리형 — 운영 비용 최저
- AWS ALB / GCP Cloud Run built-in 사용 시 환상적으로 간편
- Scale 자동

**Bad**:
- ❌ **Vendor lock-in** — 멀티 클라우드 어려움
- ❌ 비용 (트래픽 증가 시 급상승)
- ❌ WebSocket 일부 제약 (예: AWS ALB idle timeout)
- ❌ 커스텀 middleware 제한
- ❌ 로컬 개발 환경에서는 동일 구성 불가

**평가**: **파일럿 단계에서는 고려 가치 있음** (Cloud Run built-in 으로 빠른 POC). 프로덕션 장기운영에서는 Traefik이 vendor-neutral.

---

## Migration Plan (3-step)

### Step 1 · Local Docker Compose Traefik 실험
```yaml
# docker-compose.prod.yml (발췌)
traefik:
  image: traefik:v3.2
  command:
    - --api.dashboard=true
    - --providers.docker=true
    - --entrypoints.web.address=:80
    - --entrypoints.websecure.address=:443
  ports:
    - "80:80"
    - "443:443"
    - "8080:8080"  # dashboard
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
```

서비스에 Traefik label 부착:
```yaml
api:
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.api.rule=Host(`localhost`) && PathPrefix(`/predict`, `/detect`, `/chat`)"
    - "traefik.http.services.api.loadbalancer.server.port=8000"
```

### Step 2 · Kubernetes Traefik Helm Chart 설치
```bash
helm repo add traefik https://helm.traefik.io/traefik
helm install traefik traefik/traefik \
  --namespace traefik-system --create-namespace \
  --set certResolvers.letsencrypt.email=admin@skyops.example.com \
  --set ingressRoute.dashboard.enabled=true
```

`k8s/ingress.yaml` 에 IngressRoute 정의 (위 예시 참조).

### Step 3 · Middleware 계층 구축
- **ratelimit**: 100 req/min per IP
- **basicauth / forwardauth**: OIDC (Keycloak or Google) → P5
- **retry**: 3x for 5xx
- **circuitbreaker**: 5xx rate 50%에 열림

---

## Verification / Metrics

### 선정 기준 충족 여부
| 요구 | 충족? | 근거 |
|------|-------|------|
| HTTP + WebSocket | ✅ | WebSocket 네이티브 지원, `Upgrade` 헤더 자동 |
| Kubernetes 네이티브 | ✅ | IngressRoute CRD, Helm Chart |
| 동적 서비스 발견 | ✅ | K8s Service discovery via CRD |
| Let's Encrypt TLS | ✅ | `certResolver: letsencrypt` 내장 |
| OIDC / JWT | ✅ | ForwardAuth middleware |
| Rate limit + Circuit Breaker | ✅ | `RateLimit`, `CircuitBreaker` middleware |
| OpenTelemetry | ✅ | OTLP exporter 내장 (Traefik 3.0+) |
| OSS + 커뮤니티 | ✅ | Apache 2.0, 40K+ GitHub stars |

### SLO (Phase 3 이후)
- Gateway p99 latency < **50ms** (routing only, excluding upstream)
- TLS handshake p95 < **300ms**
- Let's Encrypt 자동 갱신 성공률 > **99.9%**

### Rollback
Traefik 실패 시 NGINX로 전환 경로 명시. `k8s/ingress-nginx.yaml` template을 대기(v2 예정).

---

## Non-Goals

- **Service Mesh (Istio, Linkerd)**: 별도 ADR-003. Traefik은 "ingress" 역할만. East-west traffic은 k8s 기본 Service + ClusterIP 사용.
- **API Management Platform (Kong, Tyk)**: 과한 기능. SkyOps 규모에 맞지 않음.
- **CDN 선택 (CloudFlare vs GCP)**: 별도 논의.

---

## Links

- [ADR-001 Service Decomposition](ADR-001-service-decomposition.md)
- [Traefik v3 Docs](https://doc.traefik.io/traefik/)
- [Traefik Helm Chart](https://github.com/traefik/traefik-helm-chart)
- [MADR 3.0 spec](https://adr.github.io/madr/)

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-04-14 | Initial draft — Proposed | 정재원 + Claude (P4+ Sprint) |
