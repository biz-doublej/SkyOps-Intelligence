# ADR-004 — Foundation 정직성 (Walk-forward + Schema Contract + Iceberg + Lineage/Registry)

- **Status**: Accepted
- **Date**: 2026-04-19
- **Sprint**: Stage 1 (Strategic Review 로드맵)
- **Authors**: SkyOps team
- **Supersedes**: —
- **Related**: ADR-001 (service decomposition), ADR-002 (API gateway), ADR-003 (multi-region)

## Context

Strategic Review(2026-04-14) 는 SkyOps 를 "캡스톤 MVP" → "운영 제품" 으로 승격하려면 4 단계 로드맵을 거쳐야 한다고 결론지었다. 첫 단계(**Stage 1 · Foundation 정직성 확보**) 의 게이트는 단순하지만 강력하다:

> **"숫자를 믿을 수 있다."**

숫자를 믿으려면 다음 네 축이 모두 동시에 성립해야 한다:

1. **Temporal evaluation** — 시계열 데이터에 random shuffle CV 를 쓰면 미래 정보가 과거 학습에 새어나가 score 가 인위적으로 높아진다. 대회용 수치는 좋지만 운영에선 무용지물.
2. **Canonical event model + Schema Registry** — producer 와 consumer 가 서로 다른 필드를 가정하면 디버깅·회귀 테스트 비용이 기하급수적으로 늘어난다. 계약이 없으면 "운영 가능" 을 증명할 수 없다.
3. **Iceberg Bronze/Silver/Gold (공유 카탈로그)** — 학습 데이터와 서빙 데이터가 달라지면 training-serving skew 가 발생. ACID + schema evolution + time travel 이 없으면 재현성도, 롤백도 불가능.
4. **OpenLineage + MLflow Model Registry** — "어느 데이터로 학습한 어느 버전이 언제부터 어느 환경에서 서빙되었는가" 를 5 분 안에 답할 수 없으면 사고 대응이 불가능.

본 ADR 은 위 4 축을 v2.1.8 에서 구체적으로 어떻게 구현했는지 기록한다.

## Decision Drivers

| Driver | Weight |
|---|---|
| 평가 숫자의 통계적 정직성 | 🔴 매우 높음 |
| 사고 발생 시 lineage 추적 시간 | 🔴 매우 높음 |
| Training-serving skew 방지 | 🔴 매우 높음 |
| 로컬 dev 환경 부담 | 🟡 중간 (env flag 로 on/off) |
| 발표 시연 영향 | 🟡 중간 (NAS 경량 모드는 skip 가능) |

## Decisions

### D1 · Walk-forward validation 전면 도입

**원칙**: 타임스탬프를 가진 모든 학습 데이터는 (a) `sklearn.model_selection.TimeSeriesSplit` 또는 (b) `FL_DATE` / `event_timestamp` 기준 **chronological cutoff** 로만 분할한다. `shuffle=True` 는 금지.

**구체 구현**:
- `analysis/xgboost_model.py` — `TimeSeriesSplit(n_splits=5)` (P0 sprint 에서 완료, 유지).
- `analysis/ml_phase_classifier.py` — v2.1.8 에서 `train_test_split(shuffle=True, stratify=y)` → **FL_DATE 기준 80/20 chronological cutoff** 로 교체. 플라이트 행을 먼저 시간순 정렬·분할한 뒤 각 절반에서 phase sample 을 독립적으로 합성 (cross-split leakage 원천 차단).
- `analysis/conformal_calibration.py` — calibration set 은 항상 validation split 의 마지막 15% 를 사용 (이미 시간순 분리).
- `dpo/train_dpo.py` — 선호쌍(pair) 데이터는 시계열 이벤트가 아니므로 random split 허용(예외). 주석으로 명시.

**검증 방법**:
- CI 에서 `rg "shuffle=True" analysis/ training/` 가 0 건이면 pass (dpo 예외 제외). 추후 pre-commit hook 으로 승격.

### D2 · Canonical event model + Schema Registry

**원칙**: 모든 Kafka 토픽은 `pipeline/schemas/*.avsc` Avro 스키마로 계약된다. Schema Registry(Confluent) 가 BACKWARD 호환 정책을 강제한다. Producer 는 `SerializingProducer` + `AvroSerializer` 로만 publish.

**구체 구현** (이미 완료됨, ADR 에서 결정 기록만):
- 토픽 6 개: `flight-position` / `weather-event` / `notam` / `atfm-restriction` / `alert-decision` / `acdm-milestone`.
- 스키마 파일: `pipeline/schemas/*.avsc`.
- Registry 서비스: `docker-compose.yml` 의 `schema-registry` (port 8081, profile `schema`).
- Producer: `pipeline/avro_producer.py` + `pipeline/schema_registry.py`. 실행: `skyops-schema-registry` (pyproject entry point).
- 호환성 정책: **BACKWARD** (consumer 가 항상 구 스키마로 읽을 수 있음 — 장애 복구 용이).

**검증 방법**:
- 통합 테스트: 신규 필드 추가한 스키마로 publish → 구 consumer 가 기본값으로 읽히는지 확인.

### D3 · Iceberg Bronze/Silver/Gold — 공유 REST 카탈로그

**원칙**: 데이터는 Medallion 3 계층(Bronze/Silver/Gold) 으로만 저장된다. Bronze = 원본 JSON, Silver = 스키마 검증·피처 병합, Gold = 모델·대시보드 소비용 aggregate.

**구체 구현**:
- v2.1.8 에서 카탈로그 구성을 env flag 로 분기:
  - `ICEBERG_CATALOG=sql` (기본, 로컬 dev) — SQLite + 파일 warehouse, 서비스 의존 없음.
  - `ICEBERG_CATALOG=rest` (학습·실험·스테이징) — **Nessie** REST catalog + **MinIO** S3 warehouse.
- `docker-compose.yml` 에 profile `warehouse` 추가. `docker compose --profile warehouse up -d` 로 `nessie` / `minio` / `minio-init` 3 서비스 기동.
- `feature_store/iceberg_bootstrap.py` `_build_catalog_config()` 가 env 를 읽어 올바른 `load_catalog` kwargs 반환.
- Writer: `feature_store/iceberg_writer.py` — Silver/Gold 에 `write_silver_features`, `write_gold_inference_log`, `write_gold_anomaly_decision`.
- NAS 경량 배포 (`docker-compose.nas.yml`) 에서는 `ICEBERG_ENABLED=0` 유지 (메모리 제한).

**왜 Nessie 인가?**:
- Git-스타일 branching + commit history — 실험 branch 에서 학습·검증한 뒤 main 으로 merge 가능.
- REST 프로토콜 — pyiceberg · Spark · Trino 가 동일 catalog 공유.
- AWS Glue 대비 완전 오픈소스, 자체 호스팅 가능.

### D4 · OpenLineage + MLflow Model Registry

**원칙**: 학습 실행 = OpenLineage 이벤트 한 쌍(START + COMPLETE) 발행. 학습 산출물은 MLflow Model Registry 에 등록, 자동으로 Staging 으로 승격, Production 승격은 사람 승인(HITL).

**구체 구현**:
- **OpenLineage** (P7 에서 완료):
  - `monitoring/lineage.py` — `emit_train_run_start` / `emit_train_run_complete` (HTTP POST to Marquez).
  - `analysis/xgboost_model.py` — 학습 실행의 input = `skyops.silver_flight_features`, output = `skyops.gold_inference_log` 로 emit.
  - `analysis/feature_engineering.py` — Bronze → Silver 파이프라인도 emit.
  - Marquez 서버: `docker-compose.prod.yml` 서비스 (port 5000), 개발용은 생략.
- **MLflow Model Registry** (v2.1.8 신규):
  - `analysis/xgboost_model.py` 에서 `mlflow.register_model` + `MlflowClient().transition_model_version_stage(stage="Staging")` 추가.
  - Registry 모델 이름: `skyops-delay-xgb`.
  - 등록 gate: `test_r2 >= $REGISTER_R2_THRESHOLD` (default 0.40). 미달 시 skip — Staging 오염 방지.
  - Production 승격은 사람 승인(HITL) — ADR-003 의 Multi-region runbook 에 연결.
- OpenLineage `model_version` 필드를 Registry 버전 문자열(`skyops-delay-xgb/v7`) 로 맞춰 두 시스템 사이 JOIN 이 가능.

**검증 방법**:
- 학습 실행 후 `mlflow models list -r skyops-delay-xgb` 로 버전 확인.
- Marquez UI(http://marquez:5000) 에서 해당 run 이 input/output 데이터셋과 연결되는지 확인.

## Consequences

### 긍정적 (Expected)

- **숫자 신뢰도** — 학습 성능 지표가 temporal leakage 없이 산출됨. 발표·논문에 인용해도 defensible.
- **사고 대응 시간** — OpenLineage + Registry 조합으로 "어느 모델이 어느 데이터로 학습됐는가" 를 5 분 이내 답변 가능.
- **실험 속도** — Nessie branching 으로 `experiment/rotation-v3` 같은 branch 에서 안전하게 실험.
- **ADR-003 연결** — Multi-region 배포 시 Staging → Production 승격 게이트가 정확히 이 Registry 를 통과.

### 부정적 (Trade-offs)

- **로컬 dev 부담 증가** — `docker compose --profile warehouse up` 시 nessie(200MB) + minio(300MB) + pyiceberg 의존성 추가.
  → 완화: 기본 profile 은 SQL 카탈로그 유지. 명시적 opt-in.
- **학습 시간 증가** — OpenLineage POST + Registry API 호출로 초당 수 ms 오버헤드.
  → 완화: 학습 시간은 분 단위, 계측 오버헤드는 ms 단위 — 무시 가능.
- **Registry gating 의 거짓 양성** — R² 0.40 threshold 미달이면 새 버전이 Staging 으로 안 올라감 → 기존 모델이 stale 해질 수 있음.
  → 완화: threshold env 로 조정 가능, CI 에서 회귀 테스트 시 `REGISTER_R2_THRESHOLD=0` 으로 강제 등록 가능.

## Alternatives Considered

| 대안 | 채택하지 않은 이유 |
|---|---|
| **AWS Glue** catalog | Vendor lock-in, 학부생 자비 운영 비현실적, Nessie REST 가 동등 기능 오픈소스 |
| **Hive Metastore** | 운영 복잡도 높음, Thrift 프로토콜, Kubernetes 배포 부담 |
| **MLflow 만 쓰고 OpenLineage 없음** | 학습↔데이터 사이 lineage 가 끊김. 사고 대응 시 "어느 테이블 snapshot 썼나" 답변 불가 |
| **OpenLineage 만 쓰고 Registry 없음** | 모델 승격 게이트·롤백 정책을 UI 로 관리할 수 없어 프로덕션 배포 불가 |
| **`shuffle=True` 유지하고 "어차피 도메인 지식으로 보정"** | 정직하지 않음. Strategic Review 게이트 자체가 "숫자를 믿을 수 있음" — 비협상 항목 |

## Follow-up Actions

- [ ] CI workflow 에 `rg "shuffle=True" analysis/ training/ | wc -l` 게이트 추가 (< 2, dpo 예외).
- [ ] `mlflow models list -r skyops-delay-xgb` 를 Runbook `docs/runbooks/` 에 추가.
- [ ] Marquez UI 를 `docker-compose.yml` 기본 profile 로 이동 (dev 에서도 lineage UI 확인 가능하게).
- [ ] Stage 2 로 이동 — Rotation / Turnaround / ATFM / NOTAM feature + Probabilistic Delay Prediction.

## Change Log

- 2026-04-19 · Stage 1 게이트 통과를 위해 작성. v2.1.8 구현과 함께 **Accepted**.
