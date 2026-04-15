# ADR-003 — Multi-Region Deployment Strategy

- **Status**: Proposed
- **Date**: 2026-04-15
- **Sprint**: P7-G
- **Authors**: SkyOps team (Gabriel review)
- **Supersedes**: —
- **Related**: ADR-001 (service decomposition), ADR-002 (API gateway)

## Context

SkyOps Intelligence는 현재 단일 region (Docker Desktop / 추후 GCP asia-northeast3 Seoul)에 배포될 예정이다. 캡스톤 단계에서는 충분하지만, 실 운영 SaaS 가정 시 다음 요구사항이 발생한다:

1. **Latency**: 항공 운항 의사결정은 sub-100ms p95 latency가 critical. 글로벌 분산 사용자(한국 항공사 + 미국 ATC 파트너 + 유럽 EUROCONTROL)에게 단일 region 만으로는 RTT 가 한계.
2. **Data residency**:
   - 한국: 개인정보보호법 + 국토부 항공보안법 — flight crew PII는 한국 region에 보관
   - EU: GDPR Article 44 — EU 시민 PII는 EU 내 processing
   - US: CCPA, ITAR-controlled aviation data
3. **Disaster recovery**: 단일 region 장애 시 RTO < 1h, RPO < 5min 목표
4. **Regulatory sovereignty**: FAA SWIM과 EUROCONTROL NM B2B는 각각 미국·EU 인증을 요구하므로 client는 해당 region에 위치해야 함

## Decision Drivers

| Driver | Weight |
|--------|--------|
| Latency p95 < 100ms | 🔴 매우 높음 |
| GDPR / 한국 PIPA 준수 | 🔴 매우 높음 |
| 운영 복잡도 (관리 부담) | 🟡 중간 |
| 비용 (CSP 비용) | 🟡 중간 |
| Vendor lock-in 회피 | 🟢 낮음 |

## Considered Options

### Option 1 — Active-Passive Single Region with DR

- Primary: GCP `asia-northeast3` (Seoul)
- DR: GCP `us-west1` (Oregon)
- Cold standby, async replication (Iceberg snapshot ship + Redis RDB snapshot)
- DR drill 분기당 1회

| 장점 | 단점 |
|------|------|
| 단순한 운영 | EU/US 사용자 latency 200ms+ |
| 비용 ~50% 절감 | RPO 5~15min |
| GCP 단일 vendor 관리 | data residency 미준수 |

### Option 2 — Active-Active Multi-Region (per-region full stack)

- 3 regions: `asia-northeast3` (KR), `europe-west4` (NL), `us-east1` (SC)
- 각 region 에 API + Redis + Iceberg warehouse 독립 운영
- Cross-region: Iceberg gold tier만 한 방향 (KR primary → 다른 region read-only)
- Routing: GCP Global Load Balancer geo-routing

| 장점 | 단점 |
|------|------|
| 사용자 latency 50ms 이하 | 운영 복잡 (3× IaC) |
| Data residency 준수 (region-local PII) | 비용 2.5~3× |
| Region 1 fail → 나머지 2 region 자동 routing | active-active write conflict 가능 (CRDT/last-write-wins 필요) |

### Option 3 — Hybrid: Active-Active for read, Single-master for write

- Read: 3 regions (cached delay predictions, NOTAM, anomaly stream)
- Write: KR primary (모델 학습, feedback ingest, MLflow tracking server)
- ML 모델은 KR 에서 학습 → S3-compatible cross-region replication → 각 region 에서 deploy
- Iceberg snapshot ID로 model version ↔ training data lineage 보존

| 장점 | 단점 |
|------|------|
| Read latency 좋음 + write 단순 (no conflict) | 모델 학습 latency는 region별 차이 |
| 비용 Option 2 대비 30% 절감 | KR primary 단점 — 한국 region 장애 시 학습 정지 |
| Iceberg + MLflow로 model lineage 자연스러움 | EU PII 처리 시 KR 으로 보내면 GDPR 위반 가능 |

### Option 4 — Cloud-agnostic with Multi-cloud (deferred)

- Primary: GCP, Secondary: AWS, Tertiary: Naver Cloud (Korea-specific)
- Anti-vendor-lock-in
- 너무 복잡 → 캡스톤 + 초기 SaaS 단계에서는 over-engineering

## Decision

**Option 3 (Hybrid: Active-Active read + Single-master write)** 채택.

이유:
1. 캡스톤 → 초기 SaaS 전환 단계에서 Option 2 의 운영 복잡도/비용을 감당하기 어려움
2. SkyOps의 핵심 가치는 LLM advisory (read-heavy workload) — read latency 가 가장 critical
3. 모델 학습 (write-heavy) 은 batch 작업이라 region 단일화로 충분
4. PII (GDPR/PIPA) 는 region-local Redis + Iceberg silver/bronze 에 머무르고, gold tier (학습용 aggregate) 만 cross-region

### Region Layout

| Region | Role | Components |
|--------|------|-----------|
| `asia-northeast3` (Seoul) | **Primary write** | API, Dashboard, Redis, Iceberg (Bronze/Silver/Gold), MLflow, Marquez, Feast, vLLM, **모델 학습** |
| `europe-west4` (Netherlands) | Read replica + EUROCONTROL client | API, Redis, Iceberg Bronze (region-local), Feast online, vLLM, **EUROCONTROL NM B2B subscriber** |
| `us-east1` (South Carolina) | Read replica + FAA SWIM client | API, Redis, Iceberg Bronze (region-local), Feast online, vLLM, **FAA SWIM subscriber** |

### Replication Strategy

- **Bronze tier (raw events)**: region-local — 각 region 의 SWIM/EUROCONTROL/KAC subscriber 가 자기 region Bronze 에만 write
- **Silver tier (cleaned)**: region-local features는 region-local. Cross-region join 은 Gold tier 에서.
- **Gold tier (training datasets, inference logs)**: KR primary 가 Iceberg snapshot 을 다른 region 에 hourly snapshot ship (`pyiceberg` REST catalog → S3 cross-region replication)
- **Models (Feast registry, MLflow artifacts)**: KR 에서 학습 → S3 sync → 각 region 의 ModelStore가 startup 시 pull

### Routing

- GCP HTTP(S) Load Balancer with geo-DNS
- 사용자 IP 기준 가장 가까운 region 으로 routing
- 단일 region down 시 30s health check fail → traffic 자동 rerouting
- Read endpoints (`/predict/delay`, `/chat`, `/notam/recent`): any region
- Write endpoints (`/anomaly/feedback`, `/predict/delay/batch`): KR forced (or eventual consistency)

## Consequences

### Positive

- 사용자 latency p95 < 80ms 달성 가능 (region-local serving)
- GDPR/PIPA 데이터 residency 준수 (PII 가 region 경계 안에 머무름)
- KR primary 단순한 write path → 모델 학습 + lineage 명확
- Disaster recovery: KR 장애 시 read traffic 은 EU/US가 흡수 (RPO 0, RTO ~30s for reads)

### Negative

- 운영 복잡도 +200% (Terraform 모듈 region별, monitoring 통합 어려움)
- 비용 +120% (3 region full stack — 단일 대비)
- KR primary 장애 시 모델 학습 정지 (단, in-memory IF retrain 은 region별 가능)
- Cross-region Gold tier replication latency 1~5min (모델 학습 지연)

### Mitigation

- IaC: Terraform module per region, shared state in GCP Cloud Storage
- Monitoring: Grafana federation across 3 region Prometheus instances
- KR primary failover plan: in 24h, EU 가 secondary primary 로 승격 (Iceberg snapshot 기반 catch-up)
- Compliance: GDPR DPA + 한국 PIPA 신고 + ITAR review (사용자 직접 진행)

## Migration Plan (Phase로 분리)

| Phase | 범위 | 기간 |
|-------|------|------|
| **Phase A** | KR primary GCP GKE 배포 (P7 사용자 작업) | 1주 |
| **Phase B** | EU read replica (Bronze 만, EUROCONTROL subscriber) | 2주 |
| **Phase C** | US read replica (FAA SWIM subscriber) | 2주 |
| **Phase D** | Cross-region Iceberg replication + MLflow sync | 4주 |
| **Phase E** | Geo-DNS + automated failover drill | 2주 |

총 약 11주 — 이는 정식 SaaS 운영팀이 진행할 작업 (캡스톤 범위 외).

## SLOs per Region

| Endpoint | KR p95 | EU p95 | US p95 |
|----------|--------|--------|--------|
| `/predict/delay` | 50ms | 80ms | 80ms |
| `/chat` (RAG) | 2s | 3s | 3s |
| `/aircraft/live` | 30ms | 50ms | 50ms |
| `/anomaly/feedback` (write) | 100ms | 200ms (KR forced) | 200ms |

Error budget: 99.5% per region per month.

## References

- ICAO Doc 10101 - Manual on the Air Traffic Service Information Exchange Architecture
- AWS Well-Architected Framework — Reliability Pillar (multi-region patterns)
- GCP Architecture Framework — Multi-region resiliency
- GDPR Article 44 / 한국 개인정보보호법 제17조 (해외이전 기준)
- Iceberg Spec — REST Catalog (cross-region replication)

## Decision Date / Review

- Decided: 2026-04-15 (캡스톤 P7)
- Re-review: 사용자 SaaS 출시 직전 (Phase A 완료 후)
