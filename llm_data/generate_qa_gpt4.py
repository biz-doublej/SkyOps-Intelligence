"""
SkyOps Intelligence — 7주차 Step 5: GPT-4 API로 QA 쌍 자동 생성 (~60K건)
=========================================================================
ICAO 청크 + ATC 코퍼스를 소스로 GPT-4에게 질문/답변 쌍을 생성시킵니다.

생성 유형 (총 ~60K):
  A. 규정 QA        (~25K) — FAR/ICAO 규정 조항 기반
  B. ATC 절차 QA    (~20K) — 관제 절차·교신 기반
  C. 이상 상황 QA   (~10K) — 비상 절차·비정상 운항 기반
  D. 용어 정의 QA   (~5K)  — 항공 용어 해설

실행:
  python llm_data/generate_qa_gpt4.py
  python llm_data/generate_qa_gpt4.py --target 5000   # 빠른 테스트
  python llm_data/generate_qa_gpt4.py --resume        # 이어서 생성

환경 변수:
  OPENAI_API_KEY=sk-...   (.env 파일 또는 시스템 환경 변수)

출력:
  data/qa/regulation_qa.jsonl
  data/qa/procedure_qa.jsonl
  data/qa/emergency_qa.jsonl
  data/qa/terminology_qa.jsonl
  data/qa/all_qa.jsonl    — 통합본 (~60K)
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
    )
except ImportError:
    def retry(*a, **kw):
        def decorator(fn): return fn
        return decorator
    def stop_after_attempt(n): return None
    def wait_exponential(**kw): return None
    def retry_if_exception_type(e): return None

# ── 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
ICAO_CHUNKS  = PROJECT_ROOT / "data" / "icao" / "chunks.jsonl"
ATC_CORPUS   = PROJECT_ROOT / "data" / "liveatc" / "atc_corpus.jsonl"
QA_DIR       = PROJECT_ROOT / "data" / "qa"
QA_DIR.mkdir(parents=True, exist_ok=True)
ALL_QA_PATH  = QA_DIR / "all_qa.jsonl"

# ── 생성 목표 ─────────────────────────────────────────────────────────
QA_TARGETS = {
    "regulation_qa":   {"file": "regulation_qa.jsonl",  "target": 25000, "domain": "regulation"},
    "procedure_qa":    {"file": "procedure_qa.jsonl",   "target": 20000, "domain": "atc_procedure"},
    "emergency_qa":    {"file": "emergency_qa.jsonl",   "target": 10000, "domain": "emergency"},
    "terminology_qa":  {"file": "terminology_qa.jsonl", "target": 5000,  "domain": "terminology"},
}

MODEL = "gpt-4o"  # gpt-4-turbo 도 가능

# ── QA 생성 프롬프트 ──────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert aviation knowledge assistant specializing in ATC procedures,
FAA regulations, ICAO standards, and aviation safety. Your task is to generate high-quality
question-answer pairs for fine-tuning a domain-specific language model (AviationLLM).

Rules:
1. Generate exactly {n_pairs} Q&A pairs as a JSON array.
2. Each item: {{"question": "...", "answer": "...", "category": "..."}}
3. Questions should be varied: factual, procedural, scenario-based, why/how.
4. Answers must be accurate, concise (2-5 sentences), and cite relevant regulations when applicable.
5. Use proper aviation terminology. Expand abbreviations in answers.
6. Cover different complexity levels: basic (30%), intermediate (50%), advanced (20%).
7. Categories: regulation / procedure / emergency / terminology / scenario."""

USER_PROMPT_TEMPLATE = """Source text from {doc_title} (domain: {domain}):

---
{context}
---

Generate {n_pairs} diverse aviation Q&A pairs based on this content.
Focus on: {focus_area}
Return ONLY a valid JSON array, no markdown."""

EMERGENCY_PROMPTS = [
    "engine failure procedures and crew resource management",
    "TCAS resolution advisories and pilot response",
    "emergency squawk codes 7700/7600/7500 and procedures",
    "go-around decision making and missed approach procedures",
    "wind shear escape maneuver and microburst recognition",
    "runway incursion prevention and hotspot procedures",
    "pressurization failures and emergency descent",
    "bird strike procedures and NOTAM reporting",
]

TERMINOLOGY_QA_SEED = [
    ("What is a Standard Instrument Departure (SID)?",
     "A SID (Standard Instrument Departure) is a published IFR departure procedure that provides "
     "obstacle clearance and separation from other traffic. It establishes a standard route from "
     "the runway to the en-route structure, reducing controller and pilot workload by combining "
     "complex ATC clearances into a single procedure name."),
    ("What does CAVOK mean in a METAR report?",
     "CAVOK stands for Ceiling and Visibility OK. It indicates that visibility is 10 km or more, "
     "no cloud below 5,000 feet or minimum sector altitude (whichever is greater), no cumulonimbus, "
     "and no significant weather phenomena. CAVOK simplifies weather reporting by replacing "
     "individual visibility, cloud, and weather fields when conditions are ideal."),
    ("Explain the difference between IFR and VFR flight rules.",
     "IFR (Instrument Flight Rules) govern flight primarily by reference to instruments, "
     "used when weather conditions fall below VFR minimums or when flying in controlled airspace "
     "requiring ATC separation. VFR (Visual Flight Rules) allow pilots to navigate by visual "
     "reference to terrain and maintain their own separation using 'see-and-avoid.' "
     "IFR requires an ATC clearance; VFR typically does not in uncontrolled airspace."),
    ("What is the purpose of a SIGMET?",
     "A SIGMET (Significant Meteorological Information) is an unscheduled weather advisory "
     "issued by a meteorological watch office to warn pilots of severe en-route weather hazards "
     "such as thunderstorms, tropical cyclones, severe turbulence, severe icing, volcanic ash, "
     "or radioactive cloud. SIGMETs are mandatory for flight planning on IFR and certain VFR flights."),
    ("What does 'Cleared for the ILS approach' mean?",
     "When a controller issues 'Cleared for the ILS approach,' the pilot is authorized to fly "
     "the published Instrument Landing System approach procedure. This includes intercepting the "
     "localizer course, following the glide slope down to the decision altitude (DA), and either "
     "landing if the runway environment is in sight or executing the published missed approach "
     "procedure if visual contact is not established."),
]


def load_chunks(domain_filter: str | None = None) -> list[dict]:
    """ICAO 청크 로드. 도메인 필터 옵션."""
    if not ICAO_CHUNKS.exists():
        return []
    chunks = []
    with open(ICAO_CHUNKS, encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            if domain_filter is None or c.get("domain") == domain_filter:
                chunks.append(c)
    return chunks


def load_atc_corpus() -> list[dict]:
    """ATC 코퍼스 로드."""
    if not ATC_CORPUS.exists():
        return []
    items = []
    with open(ATC_CORPUS, encoding="utf-8") as f:
        for line in f:
            items.append(json.loads(line))
    return items


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
)
def call_gpt4(client, context: str, doc_title: str, domain: str,
              focus: str, n_pairs: int = 10) -> list[dict]:
    """GPT-4 API 호출로 QA 쌍 생성."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(n_pairs=n_pairs)},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                doc_title=doc_title,
                domain=domain,
                context=context[:3000],
                n_pairs=n_pairs,
                focus_area=focus,
            )},
        ],
        temperature=0.7,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    parsed = json.loads(raw)
    # JSON 배열 또는 {"pairs": [...]} 형태 모두 처리
    if isinstance(parsed, list):
        return parsed
    for key in ("pairs", "qa_pairs", "questions", "data"):
        if key in parsed and isinstance(parsed[key], list):
            return parsed[key]
    return []


def count_existing(path: Path) -> int:
    """JSONL 파일의 기존 레코드 수."""
    if not path.exists():
        return 0
    count = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def generate_qa_set(
    client,
    qa_type: str,
    config: dict,
    chunks: list[dict],
    target_override: int | None,
    resume: bool,
) -> None:
    """단일 QA 유형 생성 루프."""
    out_path = QA_DIR / config["file"]
    target   = target_override or config["target"]
    existing = count_existing(out_path) if resume else 0

    if existing >= target:
        print(f"   ✅ {qa_type}: 이미 {existing:,}건 완료")
        return

    remaining = target - existing
    print(f"\n▶ {qa_type} 생성: {remaining:,}건 남음 ({existing:,}/{target:,})")

    domain      = config["domain"]
    focus_areas = {
        "regulation_qa":  [
            "compliance requirements and penalties",
            "pilot certification and currency requirements",
            "equipment requirements and MEL",
            "operational limits and restrictions",
        ],
        "procedure_qa":   [
            "departure and arrival procedures",
            "ATC communication phraseology",
            "instrument approach procedures",
            "en-route navigation and separation",
        ],
        "emergency_qa":   EMERGENCY_PROMPTS,
        "terminology_qa": ["aviation acronyms and definitions",
                           "weather terminology",
                           "navigation and instrument terms"],
    }[qa_type]

    # 소스 청크 필터
    src_chunks = [c for c in chunks if c.get("domain") in (domain, "general")]
    if not src_chunks:
        src_chunks = chunks  # 폴백: 전체 청크 사용

    generated = existing
    batch_size = 10  # 한 번 호출에 생성할 QA 수

    with open(out_path, "a", encoding="utf-8") as f:
        while generated < target:
            chunk = random.choice(src_chunks) if src_chunks else {"text": "", "doc_title": "Aviation Knowledge", "domain": domain}
            focus = random.choice(focus_areas)
            n     = min(batch_size, target - generated)

            try:
                pairs = call_gpt4(
                    client,
                    context   = chunk.get("text", ""),
                    doc_title = chunk.get("doc_title", "Aviation Manual"),
                    domain    = domain,
                    focus     = focus,
                    n_pairs   = n,
                )
                for pair in pairs:
                    if "question" in pair and "answer" in pair:
                        record = {
                            "type":     qa_type,
                            "question": pair["question"],
                            "answer":   pair["answer"],
                            "category": pair.get("category", domain),
                            "source":   chunk.get("chunk_id", "generated"),
                        }
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        generated += 1
                        if generated >= target:
                            break

                print(f"   [{generated:>6,}/{target:,}] +{len(pairs)}건")
                time.sleep(0.5)  # rate limiting

            except Exception as e:
                print(f"   ⚠️  API 오류: {e}")
                time.sleep(5)


def merge_all_qa() -> int:
    """모든 QA JSONL을 all_qa.jsonl로 통합."""
    total = 0
    with open(ALL_QA_PATH, "w", encoding="utf-8") as out_f:
        for config in QA_TARGETS.values():
            path = QA_DIR / config["file"]
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            out_f.write(line)
                            total += 1
    return total


def main(args: argparse.Namespace) -> None:
    print("=" * 65)
    print("  SkyOps Intelligence — GPT-4 QA 쌍 생성")
    print("=" * 65)

    # API 키 확인
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY 미설정.")
        print("   .env 파일에 OPENAI_API_KEY=sk-... 추가 또는 환경 변수 설정")
        sys.exit(1)

    try:
        from openai import OpenAI
    except ImportError:
        print("❌ openai 미설치. pip install openai")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # 소스 데이터 로드
    chunks = load_chunks()
    print(f"  ICAO 청크: {len(chunks):,}개")

    # 씨드 QA 먼저 저장 (용어 QA)
    term_path = QA_DIR / "terminology_qa.jsonl"
    if not args.resume or not term_path.exists():
        with open(term_path, "w", encoding="utf-8") as f:
            for q, a in TERMINOLOGY_QA_SEED:
                record = {"type": "terminology_qa", "question": q, "answer": a,
                          "category": "terminology", "source": "seed"}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 각 QA 유형 생성
    for qa_type, config in QA_TARGETS.items():
        generate_qa_set(
            client, qa_type, config, chunks,
            target_override=args.target,
            resume=args.resume,
        )

    # 통합
    total = merge_all_qa()
    print(f"\n✅ QA 생성 완료")
    print(f"   총 {total:,}건 → {ALL_QA_PATH}")
    print("\n다음 단계: python llm_data/generate_anomaly_nl.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GPT-4 QA 쌍 생성")
    parser.add_argument("--target", type=int, default=None,
                        help="유형별 생성 목표 수 오버라이드 (기본: 유형별 상이)")
    parser.add_argument("--resume", action="store_true",
                        help="이전 생성 이어서 진행")
    main(parser.parse_args())
