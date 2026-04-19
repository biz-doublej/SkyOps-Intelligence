"""
SkyOps — Airport network graph features (Stage 2 / ADR-005, v2.1.9 · 2026-04-19).

항공 운항은 airport-pair 네트워크 위에서 일어난다. 출발 공항의 **위상**
(hub 인가 spoke 인가) 과 route 의 **인기도** 는 지연 발생 패턴에 영향을 주지만
기존 feature set (시간·거리·기상·rotation) 에는 네트워크 topology 가 없다.

본 모듈은 한번만 계산되는 **정적 그래프 feature** 를 만든다 (공항별·route 별
topology 지표). 이 값들은 training 때 join 되고, serving 때는 pre-computed
lookup 으로만 쓰인다 (추론 경로에서 networkx 호출 금지 — SLA 유지).

**출력 파일**:
    data/models/graph_features_airports.csv
        icao | degree_in | degree_out | degree_total | pagerank
        | betweenness | airport_hub_score

    data/models/graph_features_routes.csv
        origin | dest | route_volume | route_rank
        | route_degree_product | route_hub_to_hub

**왜 GNN 아닌 정적 feature 로 시작했는가**: ADR-005 D2 참고. 요약하자면
 (1) GNN 은 inference 비용이 순간 + 캐싱 어렵고,
 (2) 항공 네트워크 topology 는 월 단위로 거의 변하지 않아 static 캐시가 충분하며,
 (3) XGBoost + topology feature 조합이 우리 data volume 에 부합.
GNN 실험은 ADR-005 D2-proposed 로 남겨 두고 follow-up.

실행:
    python -m analysis.graph_features                # 5.7M 행 전체
    python -m analysis.graph_features --sample 500000

테스트:
    python -m analysis.graph_features --self-test    # 합성 toy graph
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_CSV = DATA_DIR / "raw" / "flights.csv"
MODELS_DIR = DATA_DIR / "models"
AIRPORTS_OUT = MODELS_DIR / "graph_features_airports.csv"
ROUTES_OUT = MODELS_DIR / "graph_features_routes.csv"

ORIGIN_COL = "ORIGIN"
DEST_COL = "DEST"


# ──────────────────────────────────────────────────────────────────────
# Core graph construction
# ──────────────────────────────────────────────────────────────────────
def build_graph(df: pd.DataFrame):
    """Directed weighted graph (origin → dest, weight=flight count)."""
    import networkx as nx

    cnt = (
        df[[ORIGIN_COL, DEST_COL]]
        .dropna()
        .groupby([ORIGIN_COL, DEST_COL], observed=True)
        .size()
        .reset_index(name="flight_count")
    )

    G = nx.DiGraph()
    for _, r in cnt.iterrows():
        G.add_edge(r[ORIGIN_COL], r[DEST_COL], weight=int(r["flight_count"]))
    return G, cnt


# ──────────────────────────────────────────────────────────────────────
# Airport-level features
# ──────────────────────────────────────────────────────────────────────
def airport_features(G, betweenness_k: Optional[int] = 500) -> pd.DataFrame:
    """Per-airport topology features.

    Parameters
    ----------
    G : nx.DiGraph
    betweenness_k : int | None
        k-sample estimator size.  None 이면 exact (느림).
        Betweenness 는 O(V*E); V=400 공항일 때 n_s=500 은 실측 1-3 초.
    """
    import networkx as nx

    if G.number_of_nodes() == 0:
        return pd.DataFrame(columns=[
            "icao", "degree_in", "degree_out", "degree_total",
            "pagerank", "betweenness", "airport_hub_score",
        ])

    d_in = dict(G.in_degree())
    d_out = dict(G.out_degree())
    pagerank = nx.pagerank(G, weight="weight")

    # NetworkX 의 approximate betweenness — airport graph (V~400) 에서 k=V 면 exact.
    k = None if betweenness_k is None else min(betweenness_k, G.number_of_nodes())
    try:
        betw = nx.betweenness_centrality(G, k=k, weight=None, seed=42)
    except Exception as e:  # noqa: BLE001
        # 작은 / 비연결 그래프에서 실패할 수 있음 → 0 fallback.
        logger.warning("betweenness 계산 실패 → 0 fallback: %s", e)
        betw = {n: 0.0 for n in G.nodes}

    import math
    rows = []
    for n in G.nodes:
        din = d_in.get(n, 0)
        dout = d_out.get(n, 0)
        total = din + dout
        # Hub score: **topology 중심** (total degree) 에 flow 보정 (pagerank) 을 곱한 값.
        # Directed PageRank 는 sink (in-degree 높음) 쪽으로 쏠리므로 degree 를 주, pagerank 를 부로 사용.
        # log1p(degree_total) 이 주 신호, (1 + pagerank) 는 10% 이내 보정.
        hub = math.log1p(total) * (1.0 + float(pagerank.get(n, 0.0)))
        rows.append({
            "icao": n,
            "degree_in": din,
            "degree_out": dout,
            "degree_total": total,
            "pagerank": round(float(pagerank.get(n, 0.0)), 8),
            "betweenness": round(float(betw.get(n, 0.0)), 8),
            "airport_hub_score": round(float(hub), 8),
        })
    return pd.DataFrame(rows).sort_values("airport_hub_score", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────
# Route-level features
# ──────────────────────────────────────────────────────────────────────
def route_features(G, airports: pd.DataFrame, edge_counts: pd.DataFrame) -> pd.DataFrame:
    """Per-(origin,dest) route features."""
    hub_lookup = dict(zip(airports["icao"], airports["airport_hub_score"]))
    deg_lookup = dict(zip(airports["icao"], airports["degree_total"]))

    rc = edge_counts.rename(columns={
        ORIGIN_COL: "origin", DEST_COL: "dest", "flight_count": "route_volume",
    })
    rc["route_rank"] = rc["route_volume"].rank(ascending=False, method="min").astype(int)
    rc["route_degree_product"] = rc.apply(
        lambda r: deg_lookup.get(r["origin"], 0) * deg_lookup.get(r["dest"], 0), axis=1,
    )
    rc["route_hub_to_hub"] = rc.apply(
        lambda r: float(hub_lookup.get(r["origin"], 0.0) * hub_lookup.get(r["dest"], 0.0)), axis=1,
    )
    return rc


# ──────────────────────────────────────────────────────────────────────
# Top-level pipeline
# ──────────────────────────────────────────────────────────────────────
def compute_and_save(df: pd.DataFrame, betweenness_k: Optional[int] = 500) -> tuple[Path, Path]:
    print("🔧 building graph...")
    G, edge_counts = build_graph(df)
    print(f"   nodes={G.number_of_nodes()}  edges={G.number_of_edges()}")

    print("🔧 computing airport-level features...")
    airports = airport_features(G, betweenness_k=betweenness_k)
    print(f"   top-5 hubs: {airports['icao'].head(5).tolist()}")

    print("🔧 computing route-level features...")
    routes = route_features(G, airports, edge_counts)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    airports.to_csv(AIRPORTS_OUT, index=False)
    routes.to_csv(ROUTES_OUT, index=False)
    print(f"💾 airports  → {AIRPORTS_OUT}  ({len(airports)} rows)")
    print(f"💾 routes    → {ROUTES_OUT}  ({len(routes)} rows)")
    return AIRPORTS_OUT, ROUTES_OUT


# ──────────────────────────────────────────────────────────────────────
# Serving-side lookup (fast, no networkx dep)
# ──────────────────────────────────────────────────────────────────────
class GraphFeatureLookup:
    """Pre-computed graph feature lookup used by /predict/delay at serving time.

    O(1) dict access — no networkx import on the hot path. Load once at
    ModelStore init, then call `.airport(icao)` / `.route(origin, dest)`.
    """

    def __init__(self, airports_csv: Path = AIRPORTS_OUT, routes_csv: Path = ROUTES_OUT):
        self._airport_fallback = {
            "degree_in": 0, "degree_out": 0, "degree_total": 0,
            "pagerank": 0.0, "betweenness": 0.0, "airport_hub_score": 0.0,
        }
        self._route_fallback = {
            "route_volume": 0, "route_rank": 9999,
            "route_degree_product": 0.0, "route_hub_to_hub": 0.0,
        }
        self._airports: dict[str, dict] = {}
        self._routes: dict[tuple[str, str], dict] = {}
        if airports_csv.exists():
            a = pd.read_csv(airports_csv)
            self._airports = {row["icao"]: row.to_dict() for _, row in a.iterrows()}
        if routes_csv.exists():
            r = pd.read_csv(routes_csv)
            self._routes = {
                (row["origin"], row["dest"]): row.to_dict() for _, row in r.iterrows()
            }

    def airport(self, icao: str) -> dict:
        return self._airports.get(icao, self._airport_fallback.copy())

    def route(self, origin: str, dest: str) -> dict:
        return self._routes.get((origin, dest), self._route_fallback.copy())

    @property
    def is_loaded(self) -> bool:
        return bool(self._airports) and bool(self._routes)


# ──────────────────────────────────────────────────────────────────────
# Self-test — toy 6-airport graph
# ──────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    """Run on a 6-airport toy graph to confirm numerics are sensible."""
    import networkx as nx
    print("── self-test: toy 6-airport graph ──")
    # ICN is hub (connects to 5 others); ATL is mini-hub; rest are spokes.
    edges = [
        ("ICN", "ATL", 100), ("ICN", "LAX", 80), ("ICN", "JFK", 70),
        ("ICN", "NRT", 60), ("ICN", "CDG", 40),
        ("ATL", "LAX", 50), ("ATL", "JFK", 45),
        ("LAX", "NRT", 20), ("NRT", "CDG", 10),
    ]
    df = pd.DataFrame(
        [(o, d) for (o, d, c) in edges for _ in range(c)],
        columns=[ORIGIN_COL, DEST_COL],
    )
    G, cnt = build_graph(df)
    a = airport_features(G, betweenness_k=None)
    print(a.to_string(index=False))
    # assertion: ICN should be top hub
    top = a.iloc[0]["icao"]
    assert top == "ICN", f"expected ICN as top hub, got {top}"
    r = route_features(G, a, cnt)
    icn_atl = r[(r["origin"] == "ICN") & (r["dest"] == "ATL")].iloc[0]
    assert icn_atl["route_rank"] == 1, "ICN->ATL should be the #1 route"
    print("[OK] self-test passed")
    return 0


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="SkyOps airport graph features")
    parser.add_argument("--sample", type=int, default=None,
                        help="only read N rows of flights.csv (dev)")
    parser.add_argument("--betweenness-k", type=int, default=500,
                        help="k-sample for betweenness (None for exact)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    if args.self_test:
        return _self_test()

    if not RAW_CSV.exists():
        print(f"❌ {RAW_CSV} 없음. 먼저 prepare_dataset 을 돌려 flights.csv 를 받아두세요.")
        return 2

    print(f"📂 load {RAW_CSV}  (sample={args.sample})")
    df = pd.read_csv(
        RAW_CSV, usecols=[ORIGIN_COL, DEST_COL],
        nrows=args.sample, low_memory=False,
    )
    compute_and_save(df, betweenness_k=args.betweenness_k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
