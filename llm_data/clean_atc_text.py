"""
SkyOps Intelligence — 7주차 Step 3: ATC 교신 텍스트 정제
=========================================================
Whisper 전사 텍스트의 항공 약어를 표준 용어로 복원하고
학습 데이터에 적합한 형식으로 정제합니다.

약어 복원 예시:
  SQ / SQWK  → Squawk
  HDG        → Heading
  ALT        → Altitude
  SPD / KTS  → Speed / Knots
  CLR / CLRD → Cleared
  RWY        → Runway
  TWR        → Tower
  APP        → Approach
  DEP        → Departure
  GND        → Ground

실행:
  python llm_data/clean_atc_text.py
  python llm_data/clean_atc_text.py --min-words 10

출력:
  data/liveatc/cleaned/  — 정제된 txt 파일
  data/liveatc/atc_corpus.jsonl — 최종 ATC 코퍼스 (JSONL)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(__file__).parent.parent
TRANSCRIPT_DIR = PROJECT_ROOT / "data" / "liveatc" / "transcripts"
CLEANED_DIR    = PROJECT_ROOT / "data" / "liveatc" / "cleaned"
CLEANED_DIR.mkdir(parents=True, exist_ok=True)
CORPUS_JSONL   = PROJECT_ROOT / "data" / "liveatc" / "atc_corpus.jsonl"

# ── 약어 복원 사전 (우선순위: 긴 패턴 먼저) ──────────────────────────
# (패턴, 교체어, 플래그)
ATC_ABBREV_MAP: list[tuple[str, str]] = [
    # 관제 구분
    (r"\bTWR\b",          "Tower"),
    (r"\bAPP\b",          "Approach"),
    (r"\bDEP\b",          "Departure"),
    (r"\bGND\b",          "Ground"),
    (r"\bCTR\b",          "Center"),
    (r"\bATIS\b",         "ATIS"),
    (r"\bFSS\b",          "Flight Service Station"),
    (r"\bFIC\b",          "Flight Information Centre"),
    # 트랜스폰더
    (r"\bSQWK\b",         "Squawk"),
    (r"\bSQ\b",           "Squawk"),
    # 비행 파라미터
    (r"\bHDG\b",          "Heading"),
    (r"\bALT\b",          "Altitude"),
    (r"\bFL(\d{2,3})\b",  r"Flight Level \1"),
    (r"\bSPD\b",          "Speed"),
    (r"\bKTS\b",          "Knots"),
    (r"\bKNTS\b",         "Knots"),
    (r"\bMACH\b",         "Mach"),
    (r"\bIAS\b",          "Indicated Airspeed"),
    (r"\bTAS\b",          "True Airspeed"),
    (r"\bGS\b",           "Ground Speed"),
    # 허가·응답
    (r"\bCLRD\b",         "Cleared"),
    (r"\bCLR\b",          "Cleared"),
    (r"\bRGR\b",          "Roger"),
    (r"\bWLCO\b",         "Wilco"),
    (r"\bAFFRM\b",        "Affirm"),
    (r"\bNEGATIV\b",      "Negative"),
    (r"\bSTDBY\b",        "Standby"),
    (r"\bHLD\b",          "Hold"),
    (r"\bIMEDIATE\b",     "Immediate"),
    # 공항·활주로
    (r"\bRWY\b",          "Runway"),
    (r"\bTWY\b",          "Taxiway"),
    (r"\bRMP\b",          "Ramp"),
    (r"\bAPRON\b",        "Apron"),
    (r"\bTHLD\b",         "Threshold"),
    (r"\bTDZ\b",          "Touchdown Zone"),
    (r"\bDA\b",           "Decision Altitude"),
    (r"\bDH\b",           "Decision Height"),
    (r"\bMAP\b",          "Missed Approach Point"),
    # 항법·절차
    (r"\bIFR\b",          "Instrument Flight Rules"),
    (r"\bVFR\b",          "Visual Flight Rules"),
    (r"\bSID\b",          "Standard Instrument Departure"),
    (r"\bSTAR\b",         "Standard Terminal Arrival Route"),
    (r"\bILS\b",          "Instrument Landing System"),
    (r"\bVOR\b",          "VOR"),
    (r"\bNDB\b",          "NDB"),
    (r"\bGPS\b",          "GPS"),
    (r"\bRNAV\b",         "Area Navigation"),
    (r"\bLOC\b",          "Localizer"),
    (r"\bGS\b",           "Glide Slope"),
    (r"\bDME\b",          "Distance Measuring Equipment"),
    # 기상
    (r"\bWX\b",           "Weather"),
    (r"\bIMC\b",          "Instrument Meteorological Conditions"),
    (r"\bVMC\b",          "Visual Meteorological Conditions"),
    (r"\bMETAR\b",        "METAR"),
    (r"\bTAF\b",          "Terminal Aerodrome Forecast"),
    (r"\bSIGMET\b",       "SIGMET"),
    (r"\bPIREP\b",        "Pilot Report"),
    (r"\bCBs?\b",         "Cumulonimbus"),
    (r"\bTS\b",           "Thunderstorm"),
    (r"\bOVC\b",          "Overcast"),
    (r"\bBKN\b",          "Broken"),
    (r"\bSCT\b",          "Scattered"),
    (r"\bFEW\b",          "Few"),
    (r"\bCAVOK\b",        "Ceiling and Visibility OK"),
    # 비상
    (r"\bMYDAY\b",        "Mayday"),
    (r"\bPANPAN\b",       "Pan-Pan"),
    (r"\bEMRG\b",         "Emergency"),
    (r"\bSQUAWK\s*7700\b", "Squawk 7700 (Emergency)"),
    (r"\bSQUAWK\s*7600\b", "Squawk 7600 (Radio Failure)"),
    (r"\bSQUAWK\s*7500\b", "Squawk 7500 (Hijack)"),
    # 단위
    (r"\bFT\b",           "feet"),
    (r"\bNM\b",           "nautical miles"),
    (r"\bKM\b",           "kilometers"),
]

# 숫자 코드 → 발음 (NATO phonetic)
NATO_DIGITS = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "niner",
}


def expand_abbreviations(text: str) -> str:
    """약어를 표준 항공 용어로 복원합니다."""
    for pattern, replacement in ATC_ABBREV_MAP:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def normalize_callsign(text: str) -> str:
    """항공편 콜사인 표기를 정규화합니다. (예: N12AB → November One Two Alpha Bravo)"""
    # 간단한 콜사인 패턴: 알파벳 + 숫자 혼합 4~6자
    def replace_callsign(m: re.Match) -> str:
        cs = m.group(0)
        if len(cs) < 4 or len(cs) > 7:
            return cs
        return cs  # 현 단계에서는 원형 유지; 향후 phonetic 변환 가능
    return re.sub(r"\b[A-Z]{1,3}\d{1,4}[A-Z]{0,2}\b", replace_callsign, text)


def clean_text(raw: str) -> str:
    """전사 텍스트 정제 파이프라인."""
    text = raw.strip()

    # 1. 반복 문자 제거 (예: "ummm", "errr")
    text = re.sub(r"(.)\1{3,}", r"\1\1", text)

    # 2. 불필요한 필러 제거
    fillers = r"\b(uh+|um+|er+|ah+|hmm+)\b"
    text = re.sub(fillers, "", text, flags=re.IGNORECASE)

    # 3. 약어 복원
    text = expand_abbreviations(text)

    # 4. 콜사인 정규화
    text = normalize_callsign(text)

    # 5. 공백 정리
    text = re.sub(r"\s{2,}", " ", text).strip()

    # 6. 문장 첫 글자 대문자
    if text:
        text = text[0].upper() + text[1:]

    return text


def split_into_utterances(text: str, min_words: int = 5) -> list[str]:
    """
    긴 텍스트를 발화 단위로 분리합니다.
    마침표·느낌표·쉼표 기반으로 분리 후 최소 단어 수 필터.
    """
    # 문장 분리
    parts = re.split(r"(?<=[.!?])\s+|(?<=,)\s+", text)
    utterances = []
    buffer = ""
    for part in parts:
        buffer = (buffer + " " + part).strip()
        words  = buffer.split()
        if len(words) >= min_words:
            utterances.append(buffer)
            buffer = ""
    if buffer and len(buffer.split()) >= min_words:
        utterances.append(buffer)
    return utterances


def main(args: argparse.Namespace) -> None:
    print("=" * 65)
    print("  SkyOps Intelligence — ATC 텍스트 정제")
    print("=" * 65)

    txt_files = sorted(TRANSCRIPT_DIR.glob("*.txt"))
    if not txt_files:
        json_files = sorted(TRANSCRIPT_DIR.glob("*.json"))
        if not json_files:
            print(f"❌ {TRANSCRIPT_DIR} 에 텍스트 파일 없음.")
            sys.exit(1)
        # JSON에서 텍스트 추출
        for jf in json_files:
            with open(jf, encoding="utf-8") as f:
                data = json.load(f)
            txt_out = TRANSCRIPT_DIR / f"{jf.stem}.txt"
            txt_out.write_text(data.get("text", ""), encoding="utf-8")
        txt_files = sorted(TRANSCRIPT_DIR.glob("*.txt"))

    print(f"  입력 파일: {len(txt_files)}개")

    corpus_lines = 0
    with open(CORPUS_JSONL, "w", encoding="utf-8") as corpus_f:
        for txt_path in txt_files:
            raw = txt_path.read_text(encoding="utf-8")
            cleaned = clean_text(raw)

            # 정제 파일 저장
            out_path = CLEANED_DIR / txt_path.name
            out_path.write_text(cleaned, encoding="utf-8")

            # 발화 단위 분리 → JSONL 추가
            utterances = split_into_utterances(cleaned, min_words=args.min_words)
            for utt in utterances:
                record = {
                    "source":    txt_path.stem,
                    "text":      utt,
                    "type":      "atc_transcript",
                    "word_count": len(utt.split()),
                }
                corpus_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                corpus_lines += 1

    print(f"\n✅ 정제 완료")
    print(f"   정제 파일: {len(txt_files)}개 → {CLEANED_DIR}")
    print(f"   코퍼스:    {corpus_lines:,}개 발화 → {CORPUS_JSONL}")
    print("\n다음 단계: python llm_data/parse_icao_pdf.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ATC 교신 텍스트 정제")
    parser.add_argument("--min-words", type=int, default=8,
                        help="발화 최소 단어 수 필터 (기본 8)")
    main(parser.parse_args())
