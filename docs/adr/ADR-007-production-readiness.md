# ADR-007 — 운영 제품 승격 (RAGAs + Phase 3 분해 + Full-stack OTel + RBAC/SLO/Shadow)

- **Status**: Accepted (D1, D2, D3, D4a, D4b, D4c, D4d)
- **Date**: 2026-04-19
- **Sprint**: Stage 4 (Strategic Review 로드맵 — 최종)
- **Authors**: SkyOps team
- **Supersedes**: —
- **Related**: ADR-001 (service decomposition · Phase 3 여기서 진전),
  ADR-002 (API gateway · 여전히 Proposed), ADR-003 (multi-region),
  ADR-004 (Foundation 정직성), ADR-005 (Network-aware), ADR-006 (Operable anomaly)

## Context

Stage 4 는 Strategic Review 로드맵의 마지막 단계다. 이 단계의 게이트는 하나다:

> **"캡스톤 MVP 에서 **운영 제품**으로 넘어갔는가."**

Stage 1–3 까지 모델 품질·네트워크 반영·알람 discipline 은 갖춰졌다. 그런데
**운영** 이라는 말을 쓸 수 있으려면 기술적으로 네 축이 추가로 성립해야 한다:

1. **품질 회귀를 지속적으로 감시** — RAGAs 가 코드 한 번이 아니라 매주·PR 마다 돈다.
2. **관심사 분리가 배포 단위까지 내려옴** — 한 파일 730 줄 monolith 는 운영 제품 아님.
3. **시스템 가시성이 서비스 경계를 관통** — FastAPI 만 tracing 해선 부족. Kafka·Redis·outbound HTTP 까지.
4. **거버넌스** — RBAC·SLO·Canary·Shadow 네 가지가 있어야 "바꿀 수 있는" 제품이 된다.

본 ADR 은 네 축의 설계 결정을 기록한다.

## Decision Drivers

| Driver | Weight |
|---|---|
| 운영 중 품질 회귀 가시성 | 🔴 매우 높음 |
| 배포 단위의 독립성 | 🔴 매우 높음 |
| 사고 발생 시 분석 가능성 (tracing) | 🔴 매우 높음 |
| 변경 안전성 (canary + shadow + RBAC) | 🔴 매우 높음 |
| 운영 복잡도 증가 (trade-off) | 🟡 중간 |

## Decisions

### D1 · RAGAs CI pipeline (Accepted)

**결정**: RAGAs 평가를 수동 스크립트 (`skyops-ragas-bench`) 에서 **GitHub Actions
job** 으로 승격. 주간 cron + RAG 관련 PR 자동 실행 + 품질 gate.

**구현** (`.github/workflows/ragas_eval.yml`):
- 주간 cron: 월요일 09:00 UTC
- `workflow_dispatch` 수동 실행 (judge_mode / sample_size 입력)
- `pull_request` paths: `serving/05_rag_chain.py`, `serving/04_build_vectordb.py`,
  `serving/routers/rag.py`, `evaluation/ragas_bench.py`, `data/vectordb/**`
- 결과는 artifact 로 업로드 (90 일 보존)
- 품질 gate: `faithfulness ≥ 0.7` AND `answer_relevancy ≥ 0.7` 미달 시 CI 실패.
  proxy mode (judge 없음) 인 경우 gate skip (지표가 heuristic 이므로).
- PR 에는 자동 comment 로 4 지표 요약 게시.

**근거**:
- 운영 중인 모델의 품질은 한 번 잰 숫자가 아니라 **trend** 가 중요. 주간 cron 은
  그 trend 를 데이터로 쌓는다.
- PR 자동 실행은 RAG corpus / retrieval chain 변경의 회귀를 **코드리뷰 시점에** 잡음.
- Proxy judge mode 는 GitHub runner 에서 GPU 없이도 heuristic 으로 돌릴 수 있게
  해 cost 와 신뢰성을 trade-off — 실제 LLM judge 는 GPU 장비에서 수동.

### D2 · Service Decomposition · Phase 3 진전 (Accepted)

**결정**: ADR-001 Phase 1/2 는 이미 accepted (router 분리 + thin entry). Stage 4 에서
**Phase 3 의 첫 단계** 로 `serving/routers/anomaly.py` (754 줄) 의 관심사를 분리한다.

**이번 사이클 범위**:
- `serving/routers/alert_triage.py` 신설 — `/alerts/triage` 이관.
- `serving/common/anomaly_feedback_io.py` 신설 — 두 라우터가 공유하던
  `load_labeled_alert_ids`, `uncertainty_score`, `parse_ts_to_age`, `SEVERITY_WEIGHT`.
- `anomaly.py` 라인 수 754 → 〜640 (17% 감소, 단일 관심사: detection / feedback / approve).
- `serving/api.py` 에 `alert_triage.router` 등록.

**이번 사이클 밖 (follow-up)**:
- Phase 3 의 최종 목표인 "별도 컨테이너 배포" 는 배포 복잡도 증가가 ROI 대비 크므로
  **proposed** 로 남기고, 대신 router 분리 + 공유 헬퍼 추출로 **decomposability
  준비** 만 끝낸다. GHCR 이미지 분리, Helm sub-chart, Traefik gateway (ADR-002) 는
  실제 멀티-팀 운영이 시작될 때 시점으로 연기.

**근거**:
- Audit 에서 "anomaly.py 730 줄 = Phase 3 가 사실상 후퇴" 지적을 받음. 라인 수는
  기술 부채 proxy 이지만 실제로 테스트·리뷰 속도에 직결.
- 공유 헬퍼 파일은 나중에 라우터를 별도 프로세스로 쪼갤 때 import 경로 바꾸기만
  하면 되는 자연스러운 단계.

### D3 · Full-stack OpenTelemetry (Accepted)

**결정**: FastAPI + Logging 에 더해 Kafka / Redis / httpx / urllib3 / requests
instrumentor 를 자동 설치. 각 instrumentor 는 opt-in import (실패 시 조용히 skip).

**구현** (`serving/common/telemetry.py::_install_optional_instrumentors`):
- `OTEL_INSTRUMENT_KAFKA=1` — `KafkaInstrumentor` (producer/consumer span)
- `OTEL_INSTRUMENT_REDIS=1` — `RedisInstrumentor` (get/hgetall/xadd span)
- `OTEL_INSTRUMENT_HTTPX=1` — `HTTPXClientInstrumentor` (vLLM outbound)
- `OTEL_INSTRUMENT_URLLIB3=1` — stdlib HTTP (OpenLineage)
- `OTEL_INSTRUMENT_REQUESTS=1` — fallback 라이브러리
- pyproject.toml `otel` extras 에 5 개 패키지 추가.

**W3C traceparent propagation**:
- FastAPIInstrumentor + HTTPXClientInstrumentor 조합이 incoming/outgoing 모두
  `traceparent` 를 자동 주입. 별도 코드 수정 없음.
- Kafka 의 경우 Confluent Kafka 헤더에 자동 주입되어 downstream consumer 가
  parent span 을 복원 가능 (flink 까지 연결 준비).

**근거**:
- FastAPI 만 tracing 한 기존 상태에선 "API 는 20ms 인데 Redis 가 느린지 Kafka
  publish 가 막혔는지" 구분 불가능. 운영 사고 분석 시 가장 큰 시간 손실.
- 모든 instrumentor 가 opt-in 이라 **레거시 배포 환경** (패키지 없는 이미지) 에서도
  에러 없이 지나감 (fail-quiet 원칙).

### D4a · RBAC (Header-based, Accepted)

**결정**: FastAPI `Depends(require_roles(...))` 으로 write 엔드포인트 authorization.
Upstream Ingress / API Gateway 가 OIDC 를 해석해 `X-SkyOps-User` /
`X-SkyOps-Roles` 헤더로 전달하는 offload 모델.

**구현** (`serving/common/auth.py`):
- Principal dataclass: `user`, `roles`, `authenticated`.
- `get_principal()` dependency — 두 헤더 읽어 Principal 구성.
- `require_roles(*required)` — 역할 하나라도 있으면 통과. admin 은 모든 역할 포함.
- `require_analyst` / `require_admin` shortcut.
- env `SKYOPS_AUTH_ENFORCE=1` 일 때만 403 반환. 기본값 0 (WARN 로그 + 통과) — dev grace.

**보호된 엔드포인트** (이번 사이클):
- `POST /anomaly/feedback` — analyst or admin 필요. `req.labeled_by` 는 principal 로 강제 overwrite (spoof 방지).
- `POST /anomaly/approve` — analyst or admin 필요.

**보호 대상 후보 (follow-up)**:
- `POST /generate/announcement`, `POST /predict/delay` (현재 read-only scope).
- `POST /admin/train`, `POST /models/rollback` (gateway router 에 있으면).

**근거**:
- JWT 자체 검증 대신 Ingress offload 를 택한 이유: 학부생 단독 프로젝트가 JWKS
  로테이션·IdP 연동을 감당할 시간·비용 대비 ROI 낮음. 업계 표준 패턴 (Envoy/Istio/nginx auth-subrequest) 과 동일.
- Enforce 기본 off + soft-deny WARN 은 운영 transition 의 현실.
  `SKYOPS_AUTH_ENFORCE=1` 는 staging/prod 의 Helm values 에서 명시적 on.

### D4b · SLO Burn-rate + Alertmanager (Accepted)

**결정**: 기존 Prometheus recording rules 에 **multi-window error-budget burn-rate**
alerts (Google SRE Workbook 방식) 을 추가. Alertmanager 로 severity 별 라우팅.

**구현** (`monitoring/prometheus/slo_burn_rate.yml`):
- Recording rules: `skyops:http_error_rate:{1m,5m,30m,1h,6h,3d}`
- SLO target: availability 99.5% → error budget 0.5%
- Alert 조합:
  - **Fast burn** (critical, page): 1h ≥ 14.4× AND 5m ≥ 14.4× → 예산 ~2h 안에 소진
  - **Slow burn** (warning, ticket): 6h ≥ 6× AND 30m ≥ 6×
  - **Very slow burn** (info, weekly review): 3d ≥ 1× AND 6h ≥ 1×
- Latency SLO: delay p95 < 500ms, anomaly p95 < 200ms (5분 창)

**Alertmanager** (`monitoring/alertmanager/alertmanager.yml`):
- `severity=critical` → PagerDuty + Slack `#skyops-incidents`
- `severity=warning` → Slack `#skyops-alerts`
- `severity=info` → email `skyops-slo-review@…`
- inhibit rule: critical 활성 시 same-instance warning 은 silent (noise 감소).

**근거**:
- 단일 threshold (5xx > 1%) 는 spike 에 과민하고 slow-burn 을 놓침. Multi-window 는
  업계 표준.
- PagerDuty / Slack / email 의 3단계 escalation 이 "새벽 2시에 깨울 사안 vs 근무시간
  에 볼 사안" 구분을 강제.

### D4c · Canary — 이미 DONE (ADR-001 Phase 2 에서 완료)

**현황**:
- `k8s/rollouts/api-rollout.yaml` — Argo Rollouts, 5→25→50→100 step.
- `k8s/rollouts/analysis-templates.yaml` — success-rate ≥99% + p95-latency ≤500ms.
- Helm toggle `features.canaryRollout` 로 활성화.

ADR-007 에서는 변경 없음, cross-reference 만.

### D4d · Shadow Traffic Mirror (Accepted)

**결정**: nginx-ingress `mirror-target` annotation 으로 production 트래픽 10% 를
shadow 환경에 복제. Shadow 응답은 버려지고 production client 는 origin 응답만 받음.

**구현** (`k8s/rollouts/shadow-traffic.yaml`):
- `skyops-api-shadow` Deployment (1 replica) + Service
- 별도 Ingress 에 `nginx.ingress.kubernetes.io/mirror-target` +
  `/mirror-host` + `/mirror-probability: 0.1`
- Shadow pod env:
  - `DEPLOY_ENV=shadow` → OTel resource 에 반영, Jaeger 에서 필터링 가능
  - `SKYOPS_SHADOW_MODE=1` → write 경로 (Redis stream, feedback file) no-op
  - `SKYOPS_AUTH_ENFORCE=0` → prod 헤더 없이 요청 들어올 수 있으므로 soft

**관찰 방식**:
- Jaeger 에서 `deployment.environment="shadow"` 로 필터 → prod 와 비교.
- Prometheus: `rate(http_requests_total{deploy_env="shadow", status_code=~"5.."})` 가
  prod 대비 유의미하게 높으면 rollout 중단.
- SLO burn-rate rules 은 `job="skyops-api"` 만 보므로 shadow 는 alert 안 냄 (의도).

**근거**:
- Canary 5% 조차 signal 이 모호한 low-QPS 환경에서, shadow 는 실제 요청으로
  "신 버전이 같은 DB/Redis 호출 패턴을 재현하는가" 를 검증. 응답 수정 없음 → 안전.
- nginx annotation 방식이 Istio/Envoy 대비 운영 복잡도 훨씬 낮음.

## Consequences

### 긍정적 (Expected)

- **품질 회귀 가시성** — RAGAs 수치의 trend 가 artifact 로 누적. 1 주 단위로 모델
  성능 drift 을 눈으로 확인 가능.
- **분해 준비 완료** — alert_triage 분리 + 공유 헬퍼 추출로 Phase 3 최종 목표
  (별도 프로세스) 까지의 기술 부채 감소.
- **Trace 단절 제거** — Kafka/Redis/httpx 가 모두 span 으로 잡혀 사고 분석 시간 단축.
- **변경 안전망** — RBAC 으로 **누가** 바꿨는지, Canary 로 **조금씩** 바꾸고,
  Shadow 로 **똑같이** 테스트. 세 가지가 합쳐져 "운영 제품" 의 변경 안전성 확보.
- **SLO 정량화** — "SLA 같은 감" 이 아니라 "30-day 0.5% 예산을 이 속도로 쓰는 중" 이라는
  계측 가능한 기준.

### 부정적 (Trade-offs)

- **CI 비용** — GitHub Actions 주간 cron 이 ragas job 하나 추가. 10 분 이내로 끝나므로 무시 가능.
- **운영 복잡도 증가** — Alertmanager 3단계 라우팅 설정은 학습 곡선. 하지만 표준 패턴이라
  runbook 으로 내재화 가능.
- **OTel span 폭증** — Kafka/Redis 계측이 켜지면 span 수가 배로 증가 → Jaeger 저장
  비용 ↑.
  → 완화: `OTEL_INSTRUMENT_KAFKA=0` 로 서비스별 off 가능. Tail sampling
  은 ADR 따로 (follow-up).
- **Shadow pod 리소스** — 1 replica × 512Mi = 무시 가능. mirror-probability 10%
  이므로 실제 request 처리량도 적음.
- **RBAC 의 header 신뢰 가정** — Ingress 가 헤더를 upstream 에서 제거·재생성 해야
  안전. Helm 템플릿에 `nginx.ingress.kubernetes.io/configuration-snippet` 으로
  client 헤더 strip 명시 필요 (follow-up).

## Alternatives Considered

| 대안 | 채택하지 않은 이유 |
|---|---|
| **RAGAs 를 Airflow 로만** | Airflow 가 없는 환경 (개인 PC) 에서도 CI 로 돌 수 있어야 함 |
| **Phase 3 를 이번 사이클에 끝 — 서비스 분리 + Helm sub-charts** | 배포 복잡도 5배. 실제 멀티 팀 운영 전엔 ROI 부정적 |
| **OTel 대신 APM SaaS (Datadog)** | Vendor lock-in + 비용. OpenTelemetry 는 vendor-neutral |
| **자체 JWT 검증 (python-jose + JWKS)** | JWKS rotation·key rollover 운영 비용 매우 높음. Ingress offload 가 표준 |
| **Shadow 를 Istio mirror 로** | Istio 설치·sidecar 비용 크고 ingress-nginx 만으로 동일 기능 달성 가능 |

## Follow-up Actions

- [ ] ADR-002 (Traefik gateway) 를 실제 구현 — Phase 3 최종 단계 (별도 process).
- [ ] RBAC 을 모든 write 엔드포인트로 확장 (`/generate/announcement`, `/admin/*`).
- [ ] Helm 템플릿: client header strip (`X-SkyOps-User` 등).
- [ ] Tail sampling policy 도입 (OTel Collector `tail_sampling` processor).
- [ ] `docs/runbooks/slo-fast-burn.md` 작성 (SLO alert annotation 에 참조됨).
- [ ] Shadow pod 을 Argo Rollouts `experiment` step 으로도 실험 (대안 방식 검증).
- [ ] **Strategic Review 로드맵 Stage 1–4 전부 Accepted.** 추가 단계는 ADR-001 Phase 3
      최종 완성 + Multi-region ADR-003 실 구현으로 자연스럽게 이어짐.

## Change Log

- 2026-04-19 · D1 / D2 / D3 / D4a / D4b / D4c / D4d 모두 **Accepted** (v2.2.0).
