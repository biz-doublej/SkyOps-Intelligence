"""
10주차 Step 4 — ChromaDB 벡터 DB 구축

FAA AIM / ICAO SOP / NOTAM 샘플 문서를 ChromaDB에 임베딩합니다.
임베딩 모델: sentence-transformers (BAAI/bge-m3 or 다국어 소형 모델)

요구사항:
    pip install chromadb sentence-transformers

사용법:
    python serving/04_build_vectordb.py                        # 기본 설정
    python serving/04_build_vectordb.py --reset                # DB 초기화 후 재구축
    python serving/04_build_vectordb.py --show-stats           # DB 통계 출력

출력:
    data/vectordb/   ← ChromaDB 영구 저장소
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
CHUNKS_JSONL = PROJECT_ROOT / "data/icao/chunks.jsonl"
CORPUS_DIR   = PROJECT_ROOT / "data/icao/corpus"   # P4+ · 2026-04-14 · folder-based corpus
VECTORDB_DIR = PROJECT_ROOT / "data/vectordb"
COLLECTION   = "aviation_rag"

# 임베딩 모델: 영어 + 한국어 지원, 로컬 실행 가능
EMBED_MODEL = "BAAI/bge-m3"          # 고성능 다국어 모델 (1.9GB)
# EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # 경량 대안


# ── 추가 항공 도메인 문서 ─────────────────────────────────────────────
# data/icao/chunks.jsonl 외에 아래 인라인 문서를 함께 임베딩합니다.
EXTRA_DOCS: list[dict[str, Any]] = [
    # FAA AIM — 관제탑 절차
    {
        "chunk_id": "faa_aim_4_3_1",
        "source": "FAA_AIM",
        "section": "4-3-1. Airport Traffic Control Tower",
        "text": "Airport Traffic Control Tower (ATCT) personnel provide air traffic control service to aircraft operating on the movement area and in the airspace around the airport. Controllers issue clearances and instructions to aircraft to maintain safe separation and orderly traffic flow.",
        "domain": "atc_procedure",
        "doc_title": "FAA AIM Chapter 4",
    },
    {
        "chunk_id": "faa_aim_4_3_2",
        "source": "FAA_AIM",
        "section": "4-3-2. Ground Control",
        "text": "Ground control is responsible for airport surface traffic. All aircraft and vehicles operating on the movement area must have clearance from ground control. Pilots must obtain ground control clearance before taxiing.",
        "domain": "atc_procedure",
        "doc_title": "FAA AIM Chapter 4",
    },
    {
        "chunk_id": "faa_aim_5_5_1",
        "source": "FAA_AIM",
        "section": "5-5-1. Pilot Responsibility upon Clearance Issuance",
        "text": "When a clearance has been issued, the pilot is responsible for adhering to that clearance. If the clearance cannot be complied with, the pilot must notify ATC immediately. Emergency authority of the pilot in command takes precedence over ATC instructions in emergency situations.",
        "domain": "atc_procedure",
        "doc_title": "FAA AIM Chapter 5",
    },
    # NOTAM 샘플
    {
        "chunk_id": "notam_example_1",
        "source": "NOTAM",
        "section": "RKSI NOTAM",
        "text": "NOTAM: RKSI/INCHEON INTL - RWY 15L/33R CLSD DUE TO MAINTENANCE. EFF 2503210600-2503211800 UTC. ILS CAT II/III RWY 15R UNSERVICEABLE DUE TO MAINTENANCE WORK. EXPECT ILS CAT I APPROACHES ONLY. CONTACT INCHEON APP ON 124.5 FOR AMENDED CLEARANCES.",
        "domain": "notam",
        "doc_title": "RKSI NOTAMs",
    },
    {
        "chunk_id": "notam_example_2",
        "source": "NOTAM",
        "section": "EGLL NOTAM",
        "text": "NOTAM: EGLL/HEATHROW - ATIS VOICE BROADCAST UNAVAILABLE. PILOTS SHOULD USE D-ATIS VIA ACARS OR CONTACT INFORMATION SERVICE ON 121.750. TAXIWAY CHARLIE CLOSED BETWEEN TWY BRAVO AND TWY DELTA. USE ALTERNATE TAXI ROUTING VIA TAXIWAY ECHO.",
        "domain": "notam",
        "doc_title": "EGLL NOTAMs",
    },
    # 이상 탐지 대응 절차
    {
        "chunk_id": "sop_anomaly_1",
        "source": "SOP",
        "section": "Anomaly Response Procedure",
        "text": "When an anomaly is detected in flight parameters: (1) Identify the affected aircraft immediately. (2) Issue traffic alert to nearby aircraft. (3) Coordinate with adjacent sectors for rerouting. (4) Notify airport operations if diversion may be required. (5) Document all communications and actions taken.",
        "domain": "sop",
        "doc_title": "ATC SOP Manual",
    },
    {
        "chunk_id": "sop_anomaly_2",
        "source": "SOP",
        "section": "Unusual Fuel Consumption Protocol",
        "text": "For aircraft reporting unusual fuel consumption: Immediately query the pilot for current fuel state and destination fuel requirements. Calculate diversion fuel requirements to nearest suitable alternate. If fuel emergency declared, issue priority handling and coordinate with fire and rescue services. Advise airport operations of potential emergency landing.",
        "domain": "sop",
        "doc_title": "ATC SOP Manual",
    },
    # 지연 원인 및 분류
    {
        "chunk_id": "delay_classification_1",
        "source": "FAA",
        "section": "Delay Classification",
        "text": "Air carrier delays are classified as: (1) Air carrier caused - mechanical, crew, cleaning, fueling; (2) NAS (National Airspace System) - volume, weather, runway closures; (3) Late arriving aircraft - previous leg delay propagated; (4) Security delays; (5) Weather - both local and en-route. Delays exceeding 15 minutes at departure are reportable.",
        "domain": "operations",
        "doc_title": "FAA Delay Classification Guide",
    },
    {
        "chunk_id": "delay_classification_2",
        "source": "FAA",
        "section": "Ground Delay Programs",
        "text": "Ground Delay Programs (GDP) are traffic management initiatives that delay flights at their departure airports to manage demand at destination airports. When GDP is in effect, expect arrival delay programs, miles-in-trail restrictions, and altitude restrictions. Airlines receive controlled departure times (CDTs) and are responsible for conformance.",
        "domain": "operations",
        "doc_title": "FAA ATCSCC Operations",
    },
    # 한국 항공 관제 절차 (Korean ATC)
    {
        "chunk_id": "korean_atc_1",
        "source": "MOLIT_ATC",
        "section": "항공교통관제 절차",
        "text": "항공기 이상 상황 발생 시 관제사는 즉각적으로 해당 항공기와 교신을 시도하고, 인근 항공기에 교통 경보를 발령해야 합니다. 비상 선언 항공기에는 최우선 처리(Priority Handling)를 부여하고, 공항 소방구조대에 즉시 통보합니다. 모든 교신 내용은 자동 녹음되며 사고 조사에 활용됩니다.",
        "domain": "korean_atc",
        "doc_title": "항공교통관제 업무 매뉴얼",
    },
    {
        "chunk_id": "korean_atc_2",
        "source": "MOLIT_ATC",
        "section": "지연 대응 절차",
        "text": "15분 이상 지연이 예상되는 항공기에 대해: (1) 관련 항공사 운항관리사에 즉시 통보, (2) 슬롯 조정 요청, (3) 연결 항공편 파악 및 영향 분석, (4) 여객 안내 방송 조율. 지연 원인이 기상인 경우 기상청 항공기상서비스와 연계하여 지속 모니터링합니다.",
        "domain": "korean_atc",
        "doc_title": "항공교통관제 업무 매뉴얼",
    },
]


def scan_corpus_folder(base: Path) -> list[dict[str, Any]]:
    """Scan data/icao/corpus/**/*.md and yield chunks (P4+ · 2026-04-14).

    각 Markdown 파일은 frontmatter (optional) + content 구조.
    Content는 `## heading` 기반으로 chunk 분리한다.

    메타데이터:
      - source: frontmatter source 또는 파일 경로
      - domain: frontmatter domain 또는 parent folder name
      - section: heading text
      - doc_title: 파일명 또는 첫 # heading

    각 chunk는 chunk_id = f"{folder}_{filename}_{section_slug}" 형식.
    """
    import re
    chunks: list[dict[str, Any]] = []
    if not base.exists():
        print(f"     (corpus folder 없음: {base})")
        return chunks

    for md_file in sorted(base.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        domain = md_file.parent.name

        # Frontmatter parse (optional YAML between --- lines)
        frontmatter: dict[str, str] = {}
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                fm_block = parts[1]
                for line in fm_block.splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        frontmatter[k.strip()] = v.strip()
                text = parts[2].lstrip()

        source = frontmatter.get("source", f"{domain}/{md_file.stem}")
        fm_domain = frontmatter.get("domain", domain)
        doc_title = frontmatter.get("section", md_file.stem)

        # Split by ## headings
        sections = re.split(r"^## ", text, flags=re.MULTILINE)
        # sections[0] is preamble (before first ##); skip if empty/short
        for i, sec in enumerate(sections):
            sec = sec.strip()
            if not sec or len(sec) < 80:
                continue
            # First line is heading (unless first section which has no ##)
            if i == 0:
                heading = doc_title
                body = sec
            else:
                head_line, _, body = sec.partition("\n")
                heading = head_line.strip()
                body = body.strip()

            if not body or len(body) < 50:
                continue

            slug = re.sub(r"[^a-z0-9]+", "_", heading.lower())[:50].strip("_")
            # P6-F: append index to guarantee uniqueness even when slugs collide
            chunk_id = f"corpus_{domain}_{md_file.stem}_{slug or 'sec'}_{i}"

            chunks.append({
                "chunk_id": chunk_id,
                "text": body,
                "source": source,
                "section": heading[:200],
                "domain": fm_domain,
                "doc_title": doc_title,
            })
    return chunks


def build_vectordb(reset: bool = False, show_stats: bool = False) -> None:
    print("=" * 60)
    print("  SkyOps Intelligence — ChromaDB 벡터 DB 구축")
    print("=" * 60)

    try:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    except ImportError as e:
        print(f"[ERROR] 패키지 누락: {e}")
        print("  pip install chromadb sentence-transformers")
        raise

    t0 = time.time()

    # ── 1. ChromaDB 클라이언트 초기화 ────────────────────────────────
    VECTORDB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTORDB_DIR))

    if reset and COLLECTION in [c.name for c in client.list_collections()]:
        print(f"[!] 기존 컬렉션 삭제: {COLLECTION}")
        client.delete_collection(COLLECTION)

    # ── 2. 임베딩 함수 설정 ──────────────────────────────────────────
    print(f"[1/4] 임베딩 모델 로드: {EMBED_MODEL}")
    embed_fn = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)

    collection = client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    # ── 3. 문서 수집 ─────────────────────────────────────────────────
    print("[2/4] 문서 수집...")
    docs: list[dict] = []

    # ICAO chunks.jsonl 로드
    if CHUNKS_JSONL.exists():
        with CHUNKS_JSONL.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    docs.append(json.loads(line))
        print(f"     ICAO chunks.jsonl: {len(docs)}건")

    # P4+ · 2026-04-14 · Corpus folder scanner
    corpus_chunks = scan_corpus_folder(CORPUS_DIR)
    docs.extend(corpus_chunks)
    print(f"     Corpus folder chunks: {len(corpus_chunks)}건  ({CORPUS_DIR.relative_to(PROJECT_ROOT)})")

    # 인라인 추가 문서 (legacy)
    docs.extend(EXTRA_DOCS)
    print(f"     추가 항공 도메인 문서 (legacy EXTRA_DOCS): {len(EXTRA_DOCS)}건")
    print(f"     총 문서: {len(docs)}건")

    # ── 4. 이미 임베딩된 항목 제외 ──────────────────────────────────
    existing_ids: set[str] = set(collection.get(include=[])["ids"])
    new_docs = [d for d in docs if d["chunk_id"] not in existing_ids]
    print(f"     신규 임베딩 대상: {len(new_docs)}건 (이미 처리됨: {len(existing_ids)}건)")

    if not new_docs:
        print("[INFO] 모든 문서가 이미 임베딩되어 있습니다.")
    else:
        print("[3/4] 임베딩 및 저장...")
        BATCH = 32
        for i in range(0, len(new_docs), BATCH):
            batch = new_docs[i:i + BATCH]
            collection.add(
                ids=[d["chunk_id"] for d in batch],
                documents=[d["text"] for d in batch],
                metadatas=[
                    {
                        "source":    d.get("source", ""),
                        "section":   d.get("section", ""),
                        "domain":    d.get("domain", ""),
                        "doc_title": d.get("doc_title", ""),
                    }
                    for d in batch
                ],
            )
            print(f"     batch {i // BATCH + 1}: {len(batch)}건 저장")

    # ── 5. 검색 테스트 ───────────────────────────────────────────────
    print("[4/4] 검색 테스트 (이상 탐지 시나리오)...")
    results = collection.query(
        query_texts=["항공기 이상 연료 소비 감지 시 대응 절차"],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )
    for j, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        print(f"     [{j+1}] score={1-dist:.3f} | {meta['source']} — {meta['section'][:50]}")
        print(f"          {doc[:80]}...")

    elapsed = time.time() - t0
    total   = collection.count()
    print()
    print(f"✅ ChromaDB 구축 완료  ({elapsed:.1f}s)")
    print(f"   경로      : {VECTORDB_DIR}")
    print(f"   컬렉션    : {COLLECTION}")
    print(f"   총 문서 수: {total}건")

    if show_stats:
        all_meta = collection.get(include=["metadatas"])["metadatas"]
        domains: dict[str, int] = {}
        for m in all_meta:
            domains[m.get("domain", "?")] = domains.get(m.get("domain", "?"), 0) + 1
        print("\n   도메인 분포:")
        for domain, cnt in sorted(domains.items()):
            print(f"     {domain:20s}: {cnt}건")


def main() -> None:
    parser = argparse.ArgumentParser(description="ChromaDB 벡터 DB 구축")
    parser.add_argument("--reset",      action="store_true", help="기존 DB 초기화 후 재구축")
    parser.add_argument("--show-stats", action="store_true", help="도메인별 통계 출력")
    args = parser.parse_args()
    build_vectordb(reset=args.reset, show_stats=args.show_stats)


if __name__ == "__main__":
    main()
