# ADR-006 — 운영 가능한 이상 탐지 스택 (Phase routing + Alert Discipline)

- **Status**: Accepted
- **Date**: 2026-04-19
- **Sprint**: Stage 3 (Strategic Review 로드맵)
- **Authors**: SkyOps team
- **Supersedes**: —
- **Related**: ADR-004 (Foundation 정직성), ADR-005 (Network-aware model)

## Context

Stage 2 (ADR-005) 가 "운항 네트워크를 아는 모델" 을 확보했다면, Stage 3 는
**운영 현장에서 그 모델이 살아남을 수 있는가** 를 묻는다. 게이트:

> **"False positive 가 급감하고 운영자가 신뢰하는가."**

P5+ 에서 per-phase Isolation Forest 7 개를 학습했고, P6 에서 analyst feedback
loop (Airflow 재학습 + hot-reload) 을 만들었다. **그런데 운영에 실제로 필요한
4 가지 discipline 이 빠져 있거나 서빙이 학습 자산을 제대로 쓰지 않고 있었다**:

1. **Per-phase routing** — 7 개 모델이 모두 디스크에 있는데 서빙은 base 모델 하나만 로드 (감사 결과: Item 1 PARTIAL).
2. **Hysteresis** — 단일 임계값 기반이라 score 가 threshold 주변에서 진동하면 alert 이 **같은 flight 에 대해 반복** 발화.
3. **Suppression** — 계획된 정비·기상 경보 동안에도 이상 알람이 계속 뜸 → 분석가가 "무시" 를 누르느라 진짜 alert 을 놓침.
4. **Triage** — Active Learning queue 는 "다음에 라벨링할 항목" 을 주지만, 실시간 운영자가 "지금 어떤 alert 부터 봐야 하는가" 에 답하지 않음.

본 ADR 은 네 축에 대한 구체 설계를 기록한다.

## Decision Drivers

| Driver | Weight |
|---|---|
| False positive 감소 | 🔴 매우 높음 |
| 운영자 alert fatigue 방지 | 🔴 매우 높음 |
| 감사 추적 (규제 요구) | 🔴 매우 높음 |
| 서빙 p95 latency (< 50 ms) | 🟡 중간 |
| 기존 모델 artifact 재사용 | 🟡 중간 |

## Decisions

### D1 · Per-phase Model Routing (Accepted, v2.1.10)

**결정**: 서빙이 요청의 `flight_phase` (또는 Redis `skyops:aircraft:phase:{id}`) 를
resolve 한 뒤, 해당 phase 의 Isolation Forest 를 로드한다.

**구현**:
- `serving/common/model_store.py` — `ModelStore.isolation_forest_for_phase(phase)`
  메서드. in-process `_if_by_phase` 캐시 사전, reload signal 에 따라 invalidate.
  모델 파일이 없으면 base 로 **조용히 fallback** (운영 안정성 원칙).
- `serving/common/constants.py` — `if_model_path_for_phase(phase)` 헬퍼와
  `IF_PHASES = [TAXI, TAKEOFF, CLIMB, CRUISE, DESCENT, APPROACH, LANDING]` 상수.
- `serving/routers/anomaly.py::_resolve_phase` — 요청 우선, 그 다음 Redis, 그 다음 None.
- `AnomalyRequest` 에 `flight_phase`, `origin`, `dest`, `icao24` optional 필드 추가.
- `AnomalyResponse` 에 `model_source = "phase_model" | "base_fallback"` 필드 추가 —
  운영자가 "지금 phase 모델이 실제로 쓰였는지" 확인 가능.

**근거**:
- P5+ 학습 자산 (`isolation_forest_{PHASE}.pkl` × 7) 이 이미 disk 에 있었으나
  서빙이 한 번도 활용하지 않음. 기존 alert fatigue −67% 주장이 프로덕션에서
  실제로 달성되지 않은 상태였음.
- 각 phase 의 contamination 이 0.02 (TAXI) ~ 0.06 (APPROACH) 로 3 배 차이 —
  단일 모델로는 phase 별 타당한 임계값을 만들 수 없음.

### D2 · Hysteresis State Machine (Accepted, v2.1.10)

**결정**: 단일 임계값을 **ENTER / EXIT 두 임계값** 으로 분리하고 per-flight Redis
state 로 flapping 을 방지한다.

**임계값** (env 로 override 가능):
- `IF_SCORE_ENTER = -0.15` (진입, 더 엄격) — 여기까지 내려가야 alert 발화.
- `IF_SCORE_EXIT = -0.05` (탈출, 더 관대) — 여기까지 올라가야 alert 종료.
- 두 값 사이 (hysteresis band) 에 있으면 **이전 상태를 유지** (플래핑 차단).

**상태 저장** (`serving/routers/anomaly.py::_apply_hysteresis`):
- Redis key `skyops:anomaly:hysteresis:{flight_id}`, value ∈ {`clear`, `alerting`}
- TTL `IF_HYSTERESIS_TTL_SEC = 900s` (15 min 무활동 시 자동 만료)
- state 변화 시 setex (TTL reset), 유지 시 expire 로 TTL 만 갱신.
- `AnomalyResponse.alert_state` 로 state 를 노출해 대시보드가 시각화 가능.

**근거**:
- 실제 IF decision_function 은 score 가 임계값 근처에서 미세 진동하는 경우가 흔함.
  단일 임계값 = 5 초 간격으로 alert on/off 반복. 운영자 경험상 최악.
- 산업 표준 (Prometheus alertmanager, PagerDuty) 도 모두 enter/exit 분리.

### D3 · Suppression Window (Accepted, v2.1.10)

**결정**: YAML 규칙 파일로 **정비·기상·공항 폐쇄** 기간을 선언하고, 모델 호출 전
short-circuit 한다. Suppression 은 alert 을 없애는 게 아니라 분석가 큐에서 제외 +
Redis Stream 에 감사 기록.

**구조**:
- `config/alert_suppression.yaml` — GitOps 리뷰 가능한 단일 파일.
  `maintenance`, `weather`, `airport_closure` 3 섹션.
- `serving/common/suppression.py::SuppressionEngine` — mtime 기반 hot-reload 싱글턴.
  파일 편집 → 저장 = 즉시 반영 (무재시작).
- `serving/routers/anomaly.py::_check_suppression` — origin / dest / icao24 중 하나
  매칭되면 suppress. `_detect_anomaly` 의 Step 2 (모델 호출 전).
- 감사 로그: Redis Stream `skyops:anomaly:suppress:audit` (maxlen ≈ 10000).

**매칭 규칙**:
- 정확 문자열 매칭만 허용. regex 금지 (`.*` 같은 실수로 전체 suppress 방지).
- 시간 범위는 tz-aware UTC. 현재 시각이 범위 내일 때만 활성.
- 셋 중 처음 매칭된 규칙의 `reason` + `kind` 기록.

**근거**:
- 실 운영에서 "정비 공지는 이미 NOTAM 에 있는데 IF 가 또 alert 낸다" 는 불만이 가장 흔함.
- regex 금지는 "운영자가 `*` 로 입력해 전체 공항 suppress" 같은 실수 방지.

### D4 · Top-K Triage Endpoint (Accepted, v2.1.10)

**결정**: Active Learning queue 와는 별개로 **실시간 분석가 triage 용** 엔드포인트
`GET /alerts/triage?limit=N` 을 추가한다.

**정렬 기준**: `composite_score = severity_weight × (1 + uncertainty)`
- `severity_weight`: CRITICAL=1.0, HIGH=0.7, MEDIUM=0.4, LOW=0.2
- `uncertainty`: `_uncertainty_score` (임계값 근접성 × severity 보정)
- **intuition**: CRITICAL 은 무조건 상위, 동순위에서는 불확실한 (= 모델이 헷갈리는)
  것부터 보여주기.

**구현**:
- `TriageItem` / `TriageResponse` Pydantic 모델 (`serving/common/models.py`)
- Redis stream `skyops:anomaly:stream` 최근 500 건 스캔 → composite 정렬 → top-K
- 기본적으로 이미 라벨된 alert 은 제외 (`include_labeled=True` 로 포함 가능)
- `alert_age_sec` 필드로 오래된 unaddressed alert 도 가시화.

**`/active-learning/next` 와의 구분**:

| 엔드포인트 | 목적 | 정렬 |
|---|---|---|
| `/active-learning/next` | "다음에 라벨링할 항목" (학습 효율) | uncertainty 최대 |
| `/alerts/triage` | "지금 대응해야 할 항목" (운영 효율) | severity × uncertainty |

## Consequences

### 긍정적 (Expected)

- **실질적 FP 감소** — per-phase routing 이 실제로 서빙에 적용. TAXI 중 정상 급가속
  을 CRUISE 의 이상치로 오인하던 사례 원천 차단.
- **Alert fatigue 현실 차단** — hysteresis 로 같은 flight 의 score flapping 이 알림
  폭주로 이어지지 않음.
- **감사 추적** — suppression 은 "숨기는" 게 아니라 Redis Stream 에 모두 기록 →
  사후 분석 가능.
- **운영자 경험** — `/alerts/triage` 가 대시보드의 "지금 집중할 K 개" 섹션을 채움.
- **기존 artifact 재사용** — P5+ 학습 모델 7 개를 그대로 활용, 재학습 필요 없음.

### 부정적 (Trade-offs)

- **API surface 확장** — AnomalyRequest 에 4 개 optional 필드 추가. 기존 client 는
  영향 없음 (optional 기본값).
- **Redis 의존 증가** — hysteresis state + suppression audit stream 이 Redis 에
  추가 load. 하지만 bytes 단위 overhead (key 하나 ≈ 64 B).
  → 완화: TTL 로 자동 만료. 최대 key 수 = 동시 alerting flight 수 ≈ 수천 개.
- **suppression 잘못 설정 시 진짜 alert 놓침** — 정비 창이 너무 넓거나 종료 시각
  누락 시 며칠간 조용해짐.
  → 완화: owner 필드 필수 (책임자 명시), Redis audit stream 이 "얼마나 많이
  suppress 되고 있는지" 가시화.
- **composite 공식이 임의적** — severity_weight 와 (1+unc) 가중치 조합은 heuristic.
  → 완화: env / config 로 추후 튜닝 가능하게 남겨둠. A/B 로 검증 예정.

## Alternatives Considered

| 대안 | 채택하지 않은 이유 |
|---|---|
| **Phase 별 모델 대신 하나 큰 모델 + phase feature** | 각 phase contamination 이 3× 차이 → 단일 모델로 균일 threshold 불가능 |
| **Hysteresis 대신 dead-band만** | dead-band = 더 낮은 표현력. 진입/탈출 분리가 실사용 경험상 더 직관적 |
| **Suppression 을 DB 에 저장** | YAML 파일 + GitOps 이 더 쉬운 리뷰·롤백 흐름. DB 는 Stage 5+ 에서 필요 시 |
| **Triage 를 그냥 /active-learning/next 로 통합** | 두 use case 가 정렬 기준이 다름 (uncertainty vs severity). 섞으면 둘 다 뭉개짐 |
| **GNN / sequence model 로 FP 감소** | Stage 3 에서는 ROI 불명확. Stage 4+ 이후 실험 |

## Follow-up Actions

- [ ] 대시보드 `/app/anomaly/page.tsx` — `alert_state` 뱃지 + `model_source` 표시.
- [ ] 대시보드 신규 `/app/triage/page.tsx` — `/alerts/triage` 를 polling (SWR 5 s).
- [ ] Grafana SLO 대시보드에 **"Alert suppression rate"** 패널 추가 —
      비정상적으로 높으면 rule misconfiguration 의심.
- [ ] Load test (`docs/evidence/load_test/`) 에 `/alerts/triage` 케이스 추가.
- [ ] Stage 4 로 이동 — RAGAs + OTel + RBAC/SLO/Canary.

## Change Log

- 2026-04-19 · D1 / D2 / D3 / D4 모두 **Accepted** (v2.1.10).
