# ADR-001: Service Decomposition — Split `serving/api.py` Monolith into 6 Microservices

**Status**: Proposed
**Date**: 2026-04-14
**Deciders**: DoubleJ팀 (정재원), 지도교수 조상구
**Technical Story**: [2026-04-14 Strategic Review](../../../../Obsidian Vault/SkyOps Intelligence/2026-04-14 Strategic Review.md) — 8번 병목 (Monolith Smell)

---

## Context and Problem Statement

현재 SkyOps Intelligence의 백엔드는 `serving/api.py` **단일 파일 1004 라인** 에 모든 REST 엔드포인트(12종), WebSocket(2종), 그리고 4개의 모델 로더(XGBoost, Isolation Forest, Conformal Calibrator, RAG Chain)가 응축되어 있다. P1 업데이트로 Conformal Prediction과 Rotation feature가 추가되면서 파일 크기와 의존성 복잡도가 더 커졌다.

주요 문제:
1. **배포 단위 동일** — vLLM 종속 서비스(RAG)가 죽으면 delay prediction까지 503. GPU 장비 비용으로 스케일링도 한 덩어리.
2. **장애 격리 부재** — ChromaDB 로드 실패, vLLM timeout, Redis 연결 끊김 중 어느 하나가 전체 API를 흔든다.
3. **팀 분업 곤란** — ML 모델 쪽 작업과 WebSocket 인프라 작업이 같은 파일에서 충돌.
4. **관측성 통합 어려움** — OpenTelemetry traces를 엔드포인트별로 분리하려면 내부 router 태그에 의존.
5. **CORS 전면 개방(`*`)** — 운영 수준에서 교정 필요하지만 전체 API에 일괄 적용 중.

장기적으로 엔터프라이즈급 *"공항·항공사 운영의 Disruption Intelligence Copilot"* 로 체급이 바뀌려면, **각 기능 도메인이 독립된 운영 계약(SLO, deploy 주기, 팀 owner, 관측성)** 을 가져야 한다.

---

## Decision Drivers

- **독립 배포/스케일링**: GPU 필요 서비스(rag-service)와 CPU-only 서비스(delay-inference) 분리
- **장애 격리**: 하나의 hard dependency(vLLM, ChromaDB) 장애가 전체를 전파하지 않도록 bulkhead
- **팀 분업**: ML 엔지니어 / 인프라 / 프론트엔드가 독립 레포·CI 운영 가능하도록
- **Observability**: OpenTelemetry per-service tracing과 Prometheus metrics 분리
- **규제 대응**: Advisory Copilot 포지셔닝 ([[2026-04-14 Strategic Review]] 7번) 은 LLM 서비스에 강한 governance가 필요 → 별도 서비스로 분리 시 rate limit / audit 용이
- **점진적 마이그레이션**: Breaking change 없이 client는 gateway URL 그대로 유지

---

## Considered Options

1. **Status Quo + 내부 FastAPI Router 분리** — 하나의 app에서 router별로 파일 분리만 수행
2. **6-Service Full Decomposition** (★ 선택)
3. **3-Service Middle Ground** — (compute-heavy / stateless-api / edge-streaming)

---

## Decision Outcome

**Chosen option**: **Option 2 — 6 Microservices Full Decomposition**

### 서비스 매핑

| Service | Port | 담당 Endpoints | 모델/의존성 | Container Base |
|---------|------|----------------|-------------|----------------|
| `api-gateway` | 8000 | CORS, auth, rate limit, routing | — | Python-slim |
| `delay-inference-service` | 8010 | `POST /predict/delay`, `POST /predict/delay/batch` | `xgboost_best.pkl`, `conformal_calibrator.pkl` | Python-slim (CPU only) |
| `anomaly-service` | 8020 | `POST /detect/anomaly`, `POST /explain/anomaly`, `POST /anomaly/feedback` | `isolation_forest.pkl`, vLLM HTTP | Python-slim |
| `rag-service` | 8030 | `POST /chat` | ChromaDB, vLLM HTTP, `BAAI/bge-m3` | Python + GPU (optional) |
| `notification-service` | 8040 | `POST /generate/announcement`, Slack webhook | vLLM HTTP | Python-slim |
| `ws-broadcast-service` | 8050 | `WS /ws/aircraft`, `WS /ws/anomalies`, `GET /aircraft/live`, `GET /aircraft/h3`, `GET /anomaly/recent` | Redis (Pub/Sub 전환) | Python-slim |

### Communication

- **External**: api-gateway가 모든 요청의 단일 진입점 (client는 `http://api:8000/*` 그대로)
- **Internal**: gateway → downstream은 HTTP (httpx AsyncClient) + Correlation ID 헤더 전파
- **Async events**: anomaly-service 결과 → Redis Pub/Sub → ws-broadcast-service
- **Shared Redis**: cluster로 분리하지 않고 단일 Redis, namespace 규약만 유지 (`skyops:{domain}:{key}`)

### Consequences

#### Good
- ✅ 독립 배포: `delay-inference`는 매주, `rag-service`는 vLLM 업데이트 시에만 재배포
- ✅ 장애 격리: vLLM 장애 → `/chat`만 503, `/predict/delay`는 정상
- ✅ 리소스 효율: GPU는 `rag-service`만 할당. 다른 서비스는 cheap CPU
- ✅ OTel per-service: trace namespace 자연 분리
- ✅ RBAC 구현 용이: `rag-service`에만 강한 audit + content moderation
- ✅ Canary/Shadow deployment per service

#### Bad
- ❌ 운영 복잡도 증가: Docker Compose → Kubernetes로 격상 필요
- ❌ 서비스 간 호출 overhead (~5-10ms per hop)
- ❌ 분산 tracing 필수 (OpenTelemetry Collector 구성)
- ❌ 서비스 간 schema drift 위험 → Pydantic 모델을 `common/` 공유 패키지로 추출 필요
- ❌ Integration test 복잡도 (docker-compose.test.yml 필요)

---

## Pros and Cons of the Options

### Option 1 · Status Quo + Internal Router 분리

**Good**:
- 배포 단위 그대로 유지 (단일 FastAPI app)
- Pydantic 모델 자연 공유
- 개발 속도 빠름

**Bad**:
- 장애 격리 불가 (모든 하드 의존성이 같은 프로세스)
- GPU와 CPU 서비스 스케일링 불가능
- OTel per-service 분리 어려움
- 근본 문제 미해결 → 기술 부채 누적

**평가**: P3 품질 개선용으로는 유효. 엔터프라이즈 전환 방향과는 배치됨.

### Option 2 · 6-Service Full Decomposition (★ Chosen)

**Good**:
- 위 Consequences 참조

**Bad**:
- 위 Consequences 참조

**평가**: 초기 운영 부담은 크지만 엔터프라이즈급 운영 요구 충족. Migration Plan으로 점진적 이행 가능.

### Option 3 · 3-Service Middle Ground (compute / stateless / edge)

**구성**:
- `compute-service` — XGBoost + IF + Conformal + RAG + vLLM (GPU 필요)
- `stateless-api` — `/predict/delay`, `/detect/anomaly`, `/chat`, `/explain`, `/announce` 전부
- `edge-streaming` — WS + Redis + live aircraft

**Good**:
- Option 2보다 운영 단순
- 장애 격리는 부분적으로 가능

**Bad**:
- compute-service 여전히 monolith
- vLLM 장애 → delay prediction까지 영향
- 팀 분업 효과 반감

**평가**: Option 1과 2의 타협. 장기적으로 Option 2로 옮겨가야 하므로 중간 단계로도 매력적이지만, 최종 목표 아키텍처는 Option 2.

---

## Migration Plan (3-Phase · 점진적 이행)

### Phase 1 · Router Extraction (P3, ~1주)
**목표**: 단일 프로세스 내에서 코드 조직만 서비스 단위로 분리

```
serving/
├── api.py                 # thin entry, mounts routers
├── routers/
│   ├── gateway.py         # health, CORS, auth placeholder
│   ├── delay.py           # /predict/delay*
│   ├── anomaly.py         # /detect/anomaly, /explain/anomaly, /anomaly/feedback
│   ├── rag.py             # /chat
│   ├── notification.py    # /generate/announcement
│   └── streaming.py       # /ws/*, /aircraft/*, /anomaly/recent
├── common/
│   ├── models.py          # 공유 Pydantic
│   ├── model_store.py     # _ModelStore
│   └── redis_client.py
```

- Breaking change 없음
- Git history 유지 (per-endpoint git log 가능)

### Phase 2 · Shared Infrastructure Extraction (~2주)
- `common/` → 독립 Python 패키지 (editable install)
- OpenTelemetry 계측 일괄 삽입
- Correlation ID middleware 공통화
- Prometheus custom metrics per endpoint

### Phase 3 · Service Separation + Containerization (~4주)
- 각 router → 독립 FastAPI 프로세스
- `docker-compose.yml` → `k8s/` manifests
- API Gateway (NGINX or Traefik or 자체 api-gateway FastAPI) 도입
- Service mesh (Linkerd/Istio) 선택적 도입
- CI/CD: 서비스별 독립 GitHub Actions workflow

### Rollback 전략
- Phase 1: revert commit 가능
- Phase 2: common 패키지 버전 pin
- Phase 3: Gateway가 routing만 하므로 특정 서비스를 monolith로 fallback 시 정상 동작

---

## Verification / Metrics

### Phase 1 완료 기준
- `serving/routers/` 디렉토리에 6개 파일 존재
- `serving/api.py`가 100라인 이하로 축소
- 기존 클라이언트(대시보드 `/predict`, `/chat`) 변경 없이 동작
- pytest 커버리지 유지

### Phase 2 완료 기준
- `pip install -e common/` 성공
- OpenTelemetry trace가 Jaeger/Tempo에 per-endpoint로 기록
- Correlation-ID가 로그에서 end-to-end 추적 가능

### Phase 3 완료 기준 (SLO)
| 서비스 | p95 Latency | Error Budget | Deploy Frequency |
|--------|-------------|--------------|------------------|
| api-gateway | < 50 ms | 99.9% | 매일 가능 |
| delay-inference-service | < 200 ms | 99.95% | 주 1회 |
| anomaly-service | < 150 ms | 99.9% | 주 1회 |
| rag-service | < 5 s (p95), < 8 s (p99) | 99% | vLLM 버전 동기화 |
| notification-service | < 5 s | 99% | 주 1회 |
| ws-broadcast-service | < 100 ms push 간격 | 99.9% | 월 1회 |

### 실패 지표 (rollback trigger)
- 서비스 분리 후 전체 지연(p95) 현재 대비 2배 이상 증가
- 2주 연속 SLO 미달
- Gateway가 bottleneck이 되어 throughput 감소

---

## Non-Goals

- **Kubernetes 도입 결정은 Phase 3에서 별도 ADR-002로 분리**. 초기에는 docker-compose로 유지 가능.
- **Service mesh (Istio/Linkerd) 도입 여부는 별도 ADR**. Phase 3 완료 후 결정.
- **Database (Postgres/DynamoDB) 도입**: 현재 모든 persistent state는 Redis + file. 이 ADR 범위 밖.
- **Schema Registry (Avro)**: Canonical Event Model ([[event_model.md]]) 연동은 별도 작업.

---

## Links

- [[event_model.md]] — Canonical Event Model (Kafka 스트리밍 계약)
- [[performance_benchmark.md]] — 현재 성능 벤치마크
- [[limitations_and_improvements.md]] — Strategic Review 8번 병목
- [MADR 3.0 spec](https://adr.github.io/madr/)
- [FastAPI APIRouter documentation](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Kubernetes microservices patterns](https://kubernetes.io/docs/concepts/services-networking/)

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-04-14 | Initial draft — Proposed | Gabriel (Strategic Review) + 정재원 |
