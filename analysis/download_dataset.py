"""
SkyOps Intelligence — Kaggle Flight Delay Dataset 다운로드
===========================================================
대상 데이터셋: 2015 Flight Delays and Cancellations (usdot/flight-delays)
  - 크기: 약 5.8M 행 × 31 컬럼 (~580MB CSV)
  - 출처: U.S. DOT Bureau of Transportation Statistics

사전 준비:
  1. https://www.kaggle.com/settings → API → "Create New Token" → kaggle.json 다운로드
  2. Windows: kaggle.json → C:\\Users\\<본인>\\AppData\\Roaming\\kaggle\\kaggle.json
  3. pip install -r analysis/requirements.txt

실행:
  python analysis/download_dataset.py
"""

import os
import sys
import zipfile
from pathlib import Path

# ── 경로 설정 ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATASET_SLUG = "usdot/flight-delays"
TARGET_FILE = DATA_DIR / "flights.csv"


def check_kaggle_credentials() -> bool:
    """kaggle.json 자격 증명 존재 여부를 확인합니다."""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    win_kaggle = Path(os.environ.get("APPDATA", "")) / "kaggle" / "kaggle.json"

    if kaggle_json.exists() or win_kaggle.exists():
        return True

    print("❌ kaggle.json 파일을 찾을 수 없습니다.")
    print()
    print("설정 방법:")
    print("  1. https://www.kaggle.com/settings 접속")
    print("  2. API 섹션 → 'Create New Token' 클릭")
    print("  3. 다운로드된 kaggle.json 을 아래 경로에 저장:")
    print(f"     Windows: C:\\Users\\<본인>\\AppData\\Roaming\\kaggle\\kaggle.json")
    print(f"     Linux/Mac: ~/.kaggle/kaggle.json")
    return False


def download() -> None:
    if TARGET_FILE.exists():
        size_mb = TARGET_FILE.stat().st_size / 1024 / 1024
        print(f"✅ 이미 존재: {TARGET_FILE} ({size_mb:.0f} MB)")
        print("   재다운로드하려면 파일을 삭제 후 다시 실행하세요.")
        return

    if not check_kaggle_credentials():
        sys.exit(1)

    try:
        import kaggle
    except ImportError:
        print("❌ kaggle 패키지 미설치.")
        print("   pip install kaggle")
        sys.exit(1)

    print(f"📥 Kaggle 데이터셋 다운로드 중: {DATASET_SLUG}")
    print(f"   저장 위치: {DATA_DIR}")
    print("   (약 580MB, 시간이 걸릴 수 있습니다...)\n")

    kaggle.api.authenticate()
    kaggle.api.dataset_download_files(
        DATASET_SLUG,
        path=str(DATA_DIR),
        unzip=False,
        quiet=False,
    )

    # ZIP 압축 해제
    zip_files = list(DATA_DIR.glob("*.zip"))
    for zf in zip_files:
        print(f"\n📦 압축 해제: {zf.name}")
        with zipfile.ZipFile(zf, "r") as z:
            z.extractall(DATA_DIR)
        zf.unlink()
        print(f"   → {DATA_DIR}")

    # flights.csv 로 이름 표준화 (이미 존재하면 스킵)
    if not TARGET_FILE.exists():
        csv_files = [f for f in DATA_DIR.glob("*.csv") if f.name != "flights.csv"]
        if csv_files:
            main_csv = max(csv_files, key=lambda f: f.stat().st_size)
            main_csv.replace(TARGET_FILE)   # replace() = 덮어쓰기 허용
            print(f"\n✅ 저장 완료: {TARGET_FILE}")
    else:
        print(f"\n✅ flights.csv 이미 존재: {TARGET_FILE}")

    size_mb = TARGET_FILE.stat().st_size / 1024 / 1024 if TARGET_FILE.exists() else 0
    print(f"   크기: {size_mb:.0f} MB")
    print("\n다음 단계:")
    print("   python analysis/eda.py")


if __name__ == "__main__":
    download()
