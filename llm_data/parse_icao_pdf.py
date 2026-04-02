"""
SkyOps Intelligence — 7주차 Step 4: ICAO 문서 PDF 파싱
=======================================================
ICAO AIM, FAR Part 91/121 PDF를 파싱하여
학습용 텍스트 청크와 규정 QA 소스로 변환합니다.

지원 문서:
  - ICAO Doc 8168 (PANS-OPS) — 계기 비행 절차
  - ICAO Doc 4444 (PANS-ATM) — 관제 절차
  - FAA AIM (Aeronautical Information Manual)
  - FAR Part 91 — General Operating and Flight Rules
  - FAR Part 121 — Air Carrier Operations

실행:
  python llm_data/parse_icao_pdf.py
  python llm_data/parse_icao_pdf.py --pdf-dir data/pdfs/

출력:
  data/icao/chunks.jsonl   — 청크 단위 텍스트
  data/icao/toc.csv        — 목차 구조

PDF 입수 방법:
  - FAA AIM: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/
  - FAR: https://www.ecfr.gov/current/title-14
  - ICAO 문서: https://www.icao.int/publications (계정 필요)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# ── 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
PDF_DIR      = PROJECT_ROOT / "data" / "pdfs"
ICAO_DIR     = PROJECT_ROOT / "data" / "icao"
ICAO_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_JSONL = ICAO_DIR / "chunks.jsonl"
TOC_CSV      = ICAO_DIR / "toc.csv"

# ── 문서 메타데이터 매핑 ──────────────────────────────────────────────
DOC_META: dict[str, dict] = {
    "aim":      {"title": "FAA Aeronautical Information Manual",  "domain": "atc_procedure"},
    "far91":    {"title": "FAR Part 91 — General Operating",      "domain": "regulation"},
    "far121":   {"title": "FAR Part 121 — Air Carrier Operations","domain": "regulation"},
    "pans_atm": {"title": "ICAO Doc 4444 PANS-ATM",              "domain": "atc_procedure"},
    "pans_ops": {"title": "ICAO Doc 8168 PANS-OPS",              "domain": "atc_procedure"},
}

# ── 청크 설정 ─────────────────────────────────────────────────────────
CHUNK_SIZE_WORDS   = 300   # 청크당 최대 단어 수
CHUNK_OVERLAP_WORDS = 50   # 청크 간 겹침


def extract_text_fitz(pdf_path: Path) -> list[dict]:
    """PyMuPDF(fitz)로 페이지별 텍스트 추출."""
    try:
        import fitz  # type: ignore
    except ImportError:
        print("❌ pymupdf 미설치. pip install pymupdf")
        sys.exit(1)

    pages = []
    with fitz.open(str(pdf_path)) as doc:
        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text")
            pages.append({"page": page_num, "text": text.strip()})
    return pages


def extract_text_pdfplumber(pdf_path: Path) -> list[dict]:
    """pdfplumber 백업 파서 (표 포함 PDF에 유리)."""
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        print("❌ pdfplumber 미설치. pip install pdfplumber")
        sys.exit(1)

    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            pages.append({"page": i, "text": text.strip()})
    return pages


def clean_pdf_text(text: str) -> str:
    """PDF 추출 텍스트 정제."""
    # 헤더/푸터 패턴 제거 (페이지 번호 등)
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^Page\s+\d+\s+of\s+\d+\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)
    # 하이픈 연결어 복원
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # 줄바꿈 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_section_header(text: str) -> str | None:
    """섹션 헤더 패턴 추출. (예: '7-1-2. ATC Clearances...')"""
    patterns = [
        r"^(\d+[-\.]\d+[-\.]\d+[\.\s]+[A-Z].{5,60})$",
        r"^(SECTION\s+\d+[.\-\s]+[A-Z].{5,60})$",
        r"^(CHAPTER\s+\d+[.\-\s]+[A-Z].{5,60})$",
        r"^(PART\s+\d+[.\-\s]+[A-Z].{5,60})$",
        r"^(§\s*\d+\.\d+\s+[A-Z].{5,60})$",
    ]
    for line in text.split("\n")[:5]:
        line = line.strip()
        for pattern in patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return line
    return None


def chunk_text(
    text: str,
    source: str,
    page: int,
    section: str | None,
    doc_meta: dict,
    chunk_size: int = CHUNK_SIZE_WORDS,
    overlap: int = CHUNK_OVERLAP_WORDS,
) -> list[dict]:
    """텍스트를 슬라이딩 윈도우 방식으로 청크 분할."""
    words  = text.split()
    chunks = []
    start  = 0
    idx    = 0
    while start < len(words):
        end  = min(start + chunk_size, len(words))
        chunk_text_str = " ".join(words[start:end])
        if len(chunk_text_str.strip()) < 50:
            break
        chunks.append({
            "chunk_id":  f"{source}_p{page}_c{idx}",
            "source":    source,
            "page":      page,
            "section":   section or "",
            "text":      chunk_text_str,
            "word_count": end - start,
            "domain":    doc_meta.get("domain", "general"),
            "doc_title": doc_meta.get("title", source),
        })
        start += chunk_size - overlap
        idx   += 1
    return chunks


def parse_pdf(pdf_path: Path, doc_key: str | None = None) -> list[dict]:
    """PDF 파일 파싱 → 청크 리스트 반환."""
    print(f"   📄 {pdf_path.name}")

    # 문서 메타데이터
    key      = doc_key or pdf_path.stem.lower()
    doc_meta = next(
        (v for k, v in DOC_META.items() if k in key),
        {"title": pdf_path.stem, "domain": "aviation"},
    )

    # 텍스트 추출 (fitz 우선, 실패 시 pdfplumber)
    try:
        pages = extract_text_fitz(pdf_path)
    except Exception:
        pages = extract_text_pdfplumber(pdf_path)

    all_chunks = []
    for page_data in pages:
        raw_text = page_data["text"]
        if not raw_text or len(raw_text) < 100:
            continue
        cleaned   = clean_pdf_text(raw_text)
        section   = extract_section_header(cleaned)
        chunks    = chunk_text(
            cleaned,
            source   = pdf_path.stem,
            page     = page_data["page"],
            section  = section,
            doc_meta = doc_meta,
        )
        all_chunks.extend(chunks)

    print(f"      ✅ {len(pages)}페이지 → {len(all_chunks)}청크")
    return all_chunks


def main(args: argparse.Namespace) -> None:
    print("=" * 65)
    print("  SkyOps Intelligence — ICAO/FAR PDF 파싱")
    print("=" * 65)

    pdf_dir  = Path(args.pdf_dir)
    pdf_files = sorted(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []

    if not pdf_files:
        print(f"⚠️  {pdf_dir} 에 PDF 파일 없음.")
        print("\n📥 PDF 입수 방법:")
        print("  FAA AIM:  https://www.faa.gov/air_traffic/publications/atpubs/aim_html/")
        print("  FAR:      https://www.ecfr.gov/current/title-14")
        print("  파일을 data/pdfs/ 폴더에 저장 후 재실행하세요.\n")
        print("⚙️  샘플 텍스트로 청크 구조를 시연합니다...")

        # 샘플 데이터로 구조 시연
        sample_chunks = [
            {
                "chunk_id":  "sample_atc_p1_c0",
                "source":    "sample_atc",
                "page":      1,
                "section":   "4-2-1. Clearance Items",
                "text":      (
                    "ATC clearances normally contain the following information in the order listed: "
                    "Aircraft identification, Clearance limit, Departure procedure, Route of flight, "
                    "Altitude data in the order flown, Holding instructions, Any special information, "
                    "Frequency and transponder information. "
                    "After receiving a clearance, pilots should read back those parts containing "
                    "altitude assignments or vectors and any part requiring verification."
                ),
                "word_count": 72,
                "domain":    "atc_procedure",
                "doc_title": "FAA AIM (Sample)",
            },
            {
                "chunk_id":  "sample_far91_p1_c0",
                "source":    "sample_far91",
                "page":      1,
                "section":   "§ 91.123 Compliance with ATC Clearances",
                "text":      (
                    "When an ATC clearance has been obtained, no pilot in command may deviate from "
                    "that clearance unless an amended clearance is obtained, an emergency exists, "
                    "or the deviation is in response to a TCAS resolution advisory. "
                    "Each pilot in command who deviates from an ATC clearance shall notify ATC "
                    "as soon as possible and obtain an amended clearance."
                ),
                "word_count": 61,
                "domain":    "regulation",
                "doc_title": "FAR Part 91 (Sample)",
            },
        ]
        pdf_files = []
        all_chunks = sample_chunks
    else:
        all_chunks = []
        for pdf_path in pdf_files:
            chunks = parse_pdf(pdf_path)
            all_chunks.extend(chunks)

    # JSONL 저장
    with open(CHUNKS_JSONL, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    # TOC CSV 저장
    sections = [c for c in all_chunks if c.get("section")]
    with open(TOC_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["chunk_id", "source", "page", "section", "word_count"])
        writer.writeheader()
        writer.writerows([
            {k: c[k] for k in ["chunk_id", "source", "page", "section", "word_count"]}
            for c in sections
        ])

    total_words = sum(c["word_count"] for c in all_chunks)
    print(f"\n✅ PDF 파싱 완료")
    print(f"   파일: {len(pdf_files)}개 PDF → {len(all_chunks):,}청크")
    print(f"   총 단어: {total_words:,}")
    print(f"   저장: {CHUNKS_JSONL}")
    print("\n다음 단계: python llm_data/generate_qa_gpt4.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ICAO/FAR PDF 파싱")
    parser.add_argument("--pdf-dir", default="data/pdfs",
                        help="PDF 파일 디렉터리 (기본: data/pdfs/)")
    main(parser.parse_args())
