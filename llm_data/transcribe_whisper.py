"""
SkyOps Intelligence — 7주차 Step 2: Whisper large-v3 STT 변환
==============================================================
LiveATC mp3 파일을 OpenAI Whisper large-v3로 텍스트 변환합니다.

실행:
  python llm_data/transcribe_whisper.py
  python llm_data/transcribe_whisper.py --model large-v3
  python llm_data/transcribe_whisper.py --device cpu    # GPU 없을 때

사전 조건:
  python llm_data/download_liveatc.py
  python -m pip install "setuptools<81" wheel
  python -m pip install --no-build-isolation -r llm_data/requirements_stt.txt
  ffmpeg / ffprobe 가 PATH 에 있어야 함

출력:
  data/liveatc/transcripts/  — JSON + txt 텍스트 파일
  data/liveatc/transcripts_index.csv — 변환 결과 요약
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

# ── 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(__file__).parent.parent
AUDIO_DIR      = PROJECT_ROOT / "data" / "liveatc" / "audio"
TRANSCRIPT_DIR = PROJECT_ROOT / "data" / "liveatc" / "transcripts"
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
INDEX_CSV      = PROJECT_ROOT / "data" / "liveatc" / "transcripts_index.csv"


def load_whisper(model_name: str, device: str):
    """Whisper 모델 로드 (최초 실행 시 자동 다운로드)."""
    try:
        import whisper
    except ImportError:
        print("❌ whisper 미설치.")
        print('   python -m pip install "setuptools<81" wheel')
        print("   python -m pip install --no-build-isolation -r llm_data/requirements_stt.txt")
        sys.exit(1)

    print(f"▶ Whisper {model_name} 로드 중 (device={device})...")
    model = whisper.load_model(model_name, device=device)
    print(f"   ✅ 모델 로드 완료")
    return model


def transcribe_file(model, audio_path: Path, language: str = "en") -> dict:
    """단일 mp3 파일 STT 변환. 결과 딕셔너리 반환."""
    t0 = time.time()
    result = model.transcribe(
        str(audio_path),
        language=language,
        task="transcribe",
        fp16=False,         # CPU 호환
        verbose=False,
        condition_on_previous_text=True,
        initial_prompt=(
            "ATC communication. "
            "Tower, Ground, Approach, Departure, Center. "
            "ATIS, squawk, heading, altitude, cleared, roger, wilco."
        ),
    )
    elapsed = time.time() - t0
    return {
        "audio_file":  audio_path.name,
        "language":    result.get("language", language),
        "text":        result["text"].strip(),
        "segments":    result.get("segments", []),
        "elapsed_sec": round(elapsed, 1),
    }


def save_transcript(result: dict, out_dir: Path, stem: str) -> None:
    """JSON (세그먼트 포함) + txt (전체 텍스트) 저장."""
    json_path = out_dir / f"{stem}.json"
    txt_path  = out_dir / f"{stem}.txt"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])


def main(args: argparse.Namespace) -> None:
    print("=" * 65)
    print("  SkyOps Intelligence — Whisper STT 변환")
    print("=" * 65)

    # 오디오 파일 목록
    audio_files = sorted(AUDIO_DIR.glob("*.mp3"))
    if not audio_files:
        print(f"❌ {AUDIO_DIR} 에 mp3 파일 없음.")
        print("   python llm_data/download_liveatc.py 먼저 실행")
        sys.exit(1)

    print(f"  오디오 파일: {len(audio_files)}개")
    print(f"  모델: {args.model} | 디바이스: {args.device}")

    model   = load_whisper(args.model, args.device)
    records = []

    for i, audio_path in enumerate(audio_files, 1):
        stem     = audio_path.stem
        out_json = TRANSCRIPT_DIR / f"{stem}.json"

        if out_json.exists() and not args.force:
            print(f"  [{i:03d}/{len(audio_files)}] ⏭️  스킵 (이미 존재): {stem}")
            continue

        print(f"  [{i:03d}/{len(audio_files)}] 🎙️  {audio_path.name}")
        try:
            result = transcribe_file(model, audio_path, language=args.language)
            save_transcript(result, TRANSCRIPT_DIR, stem)

            word_count = len(result["text"].split())
            print(
                f"         ✅ {word_count:,}단어 | "
                f"{result['elapsed_sec']}초 소요"
            )
            records.append({
                "audio_file":   audio_path.name,
                "transcript":   f"{stem}.json",
                "word_count":   word_count,
                "elapsed_sec":  result["elapsed_sec"],
                "language":     result["language"],
            })
        except Exception as e:
            print(f"         ❌ 변환 실패: {e}")

    # 인덱스 저장
    with open(INDEX_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["audio_file", "transcript", "word_count",
                           "elapsed_sec", "language"]
        )
        writer.writeheader()
        writer.writerows(records)

    total_words = sum(r["word_count"] for r in records)
    print("\n" + "=" * 65)
    print(f"✅ STT 변환 완료")
    print(f"   변환 파일: {len(records)}개")
    print(f"   총 단어 수: {total_words:,}")
    print(f"   저장 위치: {TRANSCRIPT_DIR}")
    print("\n다음 단계: python llm_data/clean_atc_text.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisper large-v3 STT 변환")
    parser.add_argument("--model",    default="large-v3",
                        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
                        help="Whisper 모델 크기 (기본: large-v3)")
    parser.add_argument("--device",   default="cuda",
                        choices=["cuda", "cpu", "mps"],
                        help="연산 장치 (기본: cuda)")
    parser.add_argument("--language", default="en",
                        help="오디오 언어 코드 (기본: en)")
    parser.add_argument("--force",    action="store_true",
                        help="이미 변환된 파일도 재처리")
    main(parser.parse_args())
