"""
SkyOps Intelligence — 7주차 Step 1: LiveATC 공개 녹취 다운로드
==============================================================
LiveATC.net 에서 ATC 교신 공개 오디오를 수집합니다.

실행:
  python llm_data/download_liveatc.py
  python llm_data/download_liveatc.py --hours 10 --airports KJFK KLAX KORD

출력:
  data/liveatc/audio/     — 원본 mp3 파일
  data/liveatc/index.csv  — 다운로드 목록 (공항, URL, 파일명, 길이)

NOTE: LiveATC.net Terms of Service
  - 개인 학습·연구 목적 사용 허용
  - 상업적 재배포 금지
  - 과도한 요청 자제 (rate limiting 적용)
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
AUDIO_DIR    = PROJECT_ROOT / "data" / "liveatc" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
INDEX_CSV    = PROJECT_ROOT / "data" / "liveatc" / "index.csv"

# ── 대상 공항 (ICAO 코드) ──────────────────────────────────────────────
DEFAULT_AIRPORTS = [
    "KJFK",  # 뉴욕 존에프케네디
    "KLAX",  # 로스앤젤레스
    "KORD",  # 시카고 오헤어
    "KATL",  # 애틀랜타
    "KDEN",  # 덴버
]

# ── LiveATC 아카이브 URL 패턴 ──────────────────────────────────────────
LIVEATC_ARCHIVE_URL = "https://www.liveatc.net/recordings.php?icao={icao}"
LIVEATC_BASE        = "https://www.liveatc.net"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_archive_links(icao: str) -> list[dict]:
    """LiveATC 아카이브 페이지에서 mp3 링크 목록을 수집합니다."""
    url = LIVEATC_ARCHIVE_URL.format(icao=icao)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"   ⚠️  {icao} 아카이브 접근 실패: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".mp3") or "rec" in href.lower():
            full_url = href if href.startswith("http") else LIVEATC_BASE + href
            links.append({
                "icao": icao,
                "url":  full_url,
                "text": a.get_text(strip=True),
            })

    print(f"   🔍 {icao}: {len(links)}개 링크 발견")
    return links


def estimate_duration_sec(filepath: Path) -> float:
    """ffprobe로 오디오 길이(초)를 측정합니다."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(filepath),
            ],
            capture_output=True, text=True, timeout=10,
        )
        import json
        info = json.loads(result.stdout)
        return float(info.get("format", {}).get("duration", 0))
    except Exception:
        return 0.0


def download_audio(url: str, out_path: Path) -> bool:
    """yt-dlp 또는 requests로 오디오 파일을 다운로드합니다."""
    if out_path.exists() and out_path.stat().st_size > 10_000:
        print(f"      ⏭️  이미 존재: {out_path.name}")
        return True

    # yt-dlp 우선 시도 (스트리밍 URL 지원)
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--quiet",
                "--extract-audio",
                "--audio-format", "mp3",
                "--output", str(out_path.with_suffix("")) + ".%(ext)s",
                url,
            ],
            timeout=120, capture_output=True,
        )
        if result.returncode == 0 and out_path.exists():
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # requests 직접 다운로드 (직링크 mp3)
    try:
        resp = requests.get(url, headers=HEADERS, stream=True, timeout=30)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except requests.RequestException as e:
        print(f"      ❌ 다운로드 실패: {e}")
        return False


def main(args: argparse.Namespace) -> None:
    print("=" * 65)
    print("  SkyOps Intelligence — LiveATC 녹취 다운로드")
    print("=" * 65)
    print(f"  목표: {args.hours}시간 / 공항: {', '.join(args.airports)}")

    total_sec   = 0.0
    target_sec  = args.hours * 3600
    records     = []

    for icao in args.airports:
        if total_sec >= target_sec:
            break

        print(f"\n▶ {icao} 아카이브 스캔")
        links = fetch_archive_links(icao)
        time.sleep(args.delay)

        for link in links:
            if total_sec >= target_sec:
                break

            fname    = f"{icao}_{Path(link['url']).name}"
            out_path = AUDIO_DIR / fname

            print(f"   ⬇️  {fname[:60]}")
            ok = download_audio(link["url"], out_path)

            if ok and out_path.exists():
                dur = estimate_duration_sec(out_path)
                total_sec += dur
                records.append({
                    "icao":     icao,
                    "filename": fname,
                    "url":      link["url"],
                    "duration_sec": round(dur, 1),
                    "downloaded_at": datetime.now().isoformat(),
                })
                print(
                    f"      ✅ {dur/60:.1f}분 | "
                    f"누적 {total_sec/3600:.2f}h / {args.hours}h"
                )
            time.sleep(args.delay)

    # index.csv 저장
    with open(INDEX_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["icao", "filename", "url", "duration_sec", "downloaded_at"]
        )
        writer.writeheader()
        writer.writerows(records)

    print("\n" + "=" * 65)
    print(f"✅ 다운로드 완료")
    print(f"   총 오디오: {total_sec/3600:.2f}시간 / {len(records)}파일")
    print(f"   저장 위치: {AUDIO_DIR}")
    print(f"   인덱스:    {INDEX_CSV}")
    print("\n다음 단계:")
    print('  python -m pip install "setuptools<81" wheel')
    print("  python -m pip install --no-build-isolation -r llm_data/requirements_stt.txt")
    print("  python llm_data/transcribe_whisper.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LiveATC 녹취 다운로드")
    parser.add_argument("--hours",    type=float, default=10.0,
                        help="목표 수집 시간 (기본 10시간)")
    parser.add_argument("--airports", nargs="+", default=DEFAULT_AIRPORTS,
                        help="ICAO 공항 코드 목록")
    parser.add_argument("--delay",   type=float, default=2.0,
                        help="요청 간 대기 시간(초) — rate limiting 준수")
    main(parser.parse_args())
