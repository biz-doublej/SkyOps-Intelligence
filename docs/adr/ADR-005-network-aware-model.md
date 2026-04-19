# ADR-005 — 운항 네트워크를 아는 모델 (Rotation + Graph Topology + CQR)

- **Status**: Accepted (D1, D3, D4) · **Proposed** (D2-GNN)
- **Date**: 2026-04-19
- **Sprint**: Stage 2 (Strategic Review 로드맵)
- **Authors**: SkyOps team
- **Supersedes**: —
- **Related**: ADR-004 (Foundation 정직성), ADR-003 (Multi-region)

## Context

Stage 1 (ADR-004) 이 "숫자를 믿을 수 있다" 를 확보했다면, Stage 2 의 게이트는
다음이다:

> **"이 모델이 운항 네트워크를 알고 있는가?"**

항공편 한 건 (leg) 은 고립된 이벤트가 아니다. **같은 기체의 직전 leg**, **출발
공항의 실시간 혼잡 상태**, **route 가 hub↔hub 인지 spoke↔spoke 인지** 가
지연에 직접 영향을 준다. 기존 feature set 은 시간·거리·기상·항공사 기본
통계까지는 포함했지만, 다음 세 축이 없었다:

1. **Rotation-aware** — 같은 tail 의 이전 leg 정보 (연쇄 지연 = EUROCONTROL 연구상
   지연 원인의 45%)
2. **Network topology** — 공항/route 가 네트워크에서 어느 위치에 있는가
3. **Probabilistic** — 점 추정이 아니라 **비대칭 신뢰구간** (지연 분포는
   오른쪽 꼬리가 긴 현실에 맞는 CQR)

본 ADR 은 세 축에 대한 구체 설계 결정을 기록한다. GNN (D2 하위) 은 full
실험을 Stage 2 안에 끝낼 수 없으므로 **Proposed** 로 남겨 follow-up.

## Decision Drivers

| Driver | Weight |
|---|---|
| 운항 연쇄 지연 반영 | 🔴 매우 높음 |
| 서빙 SLA 유지 (p95 < 50ms) | 🔴 매우 높음 |
| Training-serving skew 방지 | 🔴 매우 높음 |
| 모델 재학습 비용 | 🟡 중간 |
| GNN framework 도입 부담 | 🟡 중간 |

## Decisions

### D1 · Rotation-aware feature set (Accepted)

**결정**: 5 개의 rotation feature 를 `NUMERIC_FEATURES` 에 포함시킨다 (P1 에서 이미 landing).

- `rotation_depth` — 같은 tail 의 당일 leg index (0=첫 leg)
- `prev_leg_arr_delay_min` — 직전 leg 실제 도착 지연 (분)
- `scheduled_turnaround_min` — 예정 turnaround
- `actual_turnaround_min` — 실 turnaround (EDA 시점에 관측)
- `is_first_leg_of_day` — 첫 leg 이면 1 (rotation chain 없음)

**근거**:
- 단일 변경으로 Test R² **0.0996 → 0.4328 (+335%)** 달성 (P1, 2026-04-14).
- 도메인 관점: aircraft rotation 은 항공사 내부 문제가 아니라 **공항·관제
  시스템 레벨에서 관찰 가능한 물리량** (gate 점유, taxi 순서). 데이터 확보 가능.
- 서빙 관점: 5 개 모두 DelayRequest Pydantic schema 로 노출, 대시보드 폼에 입력 필드.

**위치 증거**:
- Training: `analysis/feature_engineering.py:372-393`, `analysis/xgboost_model.py:75-77`
- Serving: `serving/common/constants.py:43-45`, `serving/common/models.py:39-43`
- Feature Store: `feature_store/feature_views.py` `flight_rotation_fv`
- UI: `dashboard/src/app/predict/page.tsx:30-34`, `:153-188`

### D2 · Graph / Network Topology (D2-Static Accepted · D2-GNN Proposed)

#### D2-Static (Accepted, v2.1.9)

**결정**: **정적 airport network topology feature** 를 pre-compute 해서 학습·서빙에서
O(1) lookup 으로만 쓴다. 네트워크는 월 단위로만 변하므로 on-the-fly 계산 금지.

구성 feature:
- Airport-level (from `analysis/graph_features.py`):
  - `degree_in`, `degree_out`, `degree_total`
  - `pagerank` (weighted, edge weight = 역사적 flight count)
  - `betweenness` (k=500 sample)
  - `airport_hub_score = log1p(degree_total) × (1 + pagerank)` — topology 가 주, flow 가 보조
- Route-level: `route_volume`, `route_rank`, `route_degree_product`, `route_hub_to_hub`
- 저장: `data/models/graph_features_airports.csv`, `..._routes.csv`
- 서빙 lookup: `GraphFeatureLookup` 싱글턴 클래스 (dict O(1)), networkx 의존 없음
- Feature Store: `airport_graph_fv` (TTL 30 일)

**근거**:
- 한국/미국 공항 네트워크는 월 단위로 거의 불변 — 정적 캐시로 충분.
- XGBoost 는 topology feature 를 tabular 로 받을 수 있어 GNN 없이도 이득.
- 서빙 p95 예산 내 — lookup 시간 < 1 µs.
- PageRank 는 **directed graph 에서 sink 쪽으로 편향** 되는 걸 실험으로 확인
  (self-test: CDG/NRT 가 sink 로 높게 나옴) → `airport_hub_score` 공식에서
  degree 를 주 신호, PageRank 를 부 보정으로 설계.

**위치 증거**:
- `analysis/graph_features.py` 전체 (260 + 라인, self-test 포함)
- `feature_store/feature_views.py` `airport_graph_fv`
- `serving/common/constants.py` `GRAPH_FEATURES_AIRPORT`, `GRAPH_FEATURES_ROUTE`

#### D2-Upstream Delay State (Accepted, v2.1.9)

**결정**: airport 의 **최근 60 분 지연 상태** 를 학습 시 leak-free 롤링으로 계산하고,
서빙 시에는 Redis 에서 읽는다.

- `origin_recent_delay_avg_60m`, `..._p95_60m`, `..._volume_60m`
- `dest_recent_delay_avg_60m`, `..._volume_60m`
- `origin_hub_congestion_ratio = recent_volume / avg_hourly_volume`

**Leak-free 구현** (`analysis/upstream_delay.py::_rolling_by_group`):
- `pandas DatetimeIndex + groupby(airport).rolling('60min', closed='left')` — 좌폐구간
- self-test: 10:30 flight 가 09:45 flight 만 window 에 포함 (09:00 은 1.5 h 전이라 제외) 확인

**서빙 구현** (추후 P8 에서 wire):
- Redis hash `skyops:upstream:{airport}` 에 `{count, delay_sum, delay_sq, p95}` 저장
- Flink processor 가 departure/arrival 이벤트를 받을 때마다 hash 갱신
- API 는 READ only → O(1)

**근거**:
- 지연은 **전염** 되는 성질. "지금 ICN 이 계속 밀려 있으면 KE 다음 편도 밀린다" 는
  관제사 직관을 정량화.
- 학습 시 random shuffle 로 계산하면 **미래 지연을 현재 feature 에 새어넣어** 평가가
  인위적으로 좋아짐 → ADR-004 의 temporal leakage 원칙과 직결.

**위치 증거**:
- `analysis/upstream_delay.py` 전체
- `feature_store/feature_views.py` `upstream_delay_fv`

#### D2-GNN (Proposed, Stage 3 후보)

**현 단계에서 배제**. 이유:

1. **실험 비용** — GNN framework (torch-geometric / DGL) 도입은 새 런타임 의존성
   (~500 MB) + 학습 파이프라인 재설계.
2. **효과 불확실** — airport graph 는 상대적으로 작고 (V≈400, E≈5000) dense.
   Message passing 의 구조적 이득이 XGBoost + 정적 topology feature 대비 얼마나
   큰지 확증된 선행연구가 없다.
3. **운영 부담** — GNN 서빙은 TorchServe / Triton 이 필요, cosign 서명·SBOM
   파이프라인 확장 필요.

**Follow-up 조건**: Stage 3 이후 (a) 데이터 볼륨이 10 × 증가, (b) 정적 topology
feature 로도 설명되지 않는 패턴이 drift detector 에서 잡히는 경우.

Proposed 실험 branch: `experiments/gnn-sandbox`, target: Test R² +5pp 이상이면 Accepted 로 승격.

### D3 · Quantile Regression + Conformal (Accepted)

**결정**: 점 추정 + 대칭 구간에 더해 **Conformalized Quantile Regression (CQR)**
calibrator 를 production 에 투입한다.

구성:
- 학습 (`analysis/quantile_regression.py`) — `GradientBoostingRegressor(loss='quantile', alpha=[0.05, 0.95])`
  로 하한·상한 분리 학습. 저장: `data/models/quantile_lower.pkl`, `quantile_upper.pkl`
- 보정 (`analysis/conformal_calibration.py`) — MAPIE `SplitConformalRegressor` 위에 CQR
  residual 로 추가 보정. 저장: `data/models/conformal_calibrator_cqr.pkl`
- 서빙 (v2.1.9):
  - `ModelStore.conformal()` 이 CQR artifact 를 우선 load (있으면), 없으면
    symmetric split conformal 로 fallback
  - 응답의 `PredictionInterval.method` 필드가 `"cqr_mapie_v1.3.0"` 으로 변경
  - 배치 경로 `/predict/delay/batch` 도 동일

**근거**:
- 지연 분포는 오른쪽 꼬리가 긴 실제 운영 관찰 사실. 대칭 구간은 "지연 20 분,
  ± 18 분" 같은 말이 안 되는 하한 (음의 지연) 을 만든다.
- CQR 은 quantile regression 의 **coverage guarantee 없는 문제** 를 conformal
  residual 로 보정 → 분포 가정 없이 target coverage 보장.
- MAPIE 구현체 이미 존재, 추가 의존성 0 건.

**위치 증거**:
- `analysis/quantile_regression.py:37` (GradientBoostingRegressor quantile)
- `analysis/conformal_calibration.py:45-55` (MAPIE SplitConformalRegressor for CQR)
- `serving/common/constants.py:25` `CONFORMAL_PATH_CQR`
- `serving/common/model_store.py:81-115` CQR 우선순위 loader (v2.1.9)
- `serving/routers/delay.py:45-47` method 문자열 분기 (v2.1.9)

## Consequences

### 긍정적 (Expected)

- **운항 네트워크 반영** — rotation + topology + upstream 세 축이 모두 feature
  set 에 들어가 "공항이 지금 어떤 상태인지" 를 모델이 인식.
- **CQR 의 현실적 구간** — 관제사가 "최대 지연 X 분" 을 정량적으로 안내 가능.
  대칭 구간의 거짓 안정감 (falsely-symmetric band) 문제 해결.
- **F/S bundle 버전 관리** — `delay_prediction_v3_network` feature service 로 다음
  retrain 의 input 이 정의됨. 재학습 시 training-serving skew 원천 차단.
- **GNN 으로 성급히 가지 않음** — 비용 대비 효과를 확신하기 전까지 간접비 0.

### 부정적 (Trade-offs)

- **graph_features CSV 생성 필요** — 풀 `flights.csv` (5.7 M 행) 에서 월 1 회
  batch 작업. 60 s 이내 완료 (self-test 완료).
  → 완화: Airflow DAG 로 스케줄. 실패 시 이전 CSV 유지 (stale-safe).
- **현 production 모델은 graph feature 를 받지 않음** — xgboost_best.pkl 은
  rotation 까지만. graph feature 는 다음 retrain 에 입력.
  → 완화: `NUMERIC_FEATURES` 에 추가하지 않고 별도 리스트 (`NETWORK_FEATURES`)
  로 유지하여 serving 이 깨지지 않도록. 재학습 시 `ALL_FEATURES =
  NUMERIC_FEATURES + CATEGORICAL_FEATURES + NETWORK_FEATURES` 로 합치기.
- **CQR artifact 가 training pipeline 의 실패 지점을 추가** — quantile 모델 2 개
  + calibrator 1 개가 모두 생성되어야 함.
  → 완화: `ModelStore.conformal()` 가 fallback 경로 (CQR → split → None) 를 지원.

## Alternatives Considered

| 대안 | 채택하지 않은 이유 |
|---|---|
| **정적 graph feature 생략하고 GNN 바로 도입** | 위 D2-GNN 참조. 비용 대비 효과 불확실 |
| **on-the-fly graph 계산 (networkx 서빙 시 호출)** | 서빙 p95 예산 초과 — networkx pagerank O(V+E) 수 ms |
| **rolling 을 `closed='right'` 또는 기본값** | temporal leakage 발생 (ADR-004 위반) |
| **Symmetric conformal 만 유지** | 지연 분포의 오른쪽 꼬리를 과소평가 |
| **Bayesian Neural Network** for 불확실성 | 학습 비용 × 10, ROI 불명확. Stage 3 이후 |

## Follow-up Actions

- [ ] `airflow/dags/skyops_graph_refresh_dag.py` 신설 — 월 1 회 `graph_features.py` 실행.
- [ ] `analysis/xgboost_model.py` 에 `--network-features` flag — True 시
      `ALL_FEATURES + NETWORK_FEATURES` 로 학습.
- [ ] CQR retrain 가이드 `docs/runbooks/cqr-calibration.md` 추가.
- [ ] `experiments/gnn-sandbox` branch 생성 — torch-geometric 실험 (D2-GNN Proposed).
- [ ] Stage 3 로 이동 — Phase-aware Anomaly Stack + Analyst Feedback + Alert Fatigue.

## Change Log

- 2026-04-19 · D1 + D2-Static + D2-Upstream + D3 **Accepted** (v2.1.9). D2-GNN **Proposed**.
