"""
SkyOps Intelligence — OpenSky Network API 테스트 스크립트
.env 파일에 OPENSKY_USERNAME, OPENSKY_PASSWORD 를 입력한 후 실행하세요.

실행 방법:
    pip install requests python-dotenv
    python test_opensky_api.py
"""

import os
import json
import time
import requests
from datetime import datetime, timezone

# .env 파일 로드 (python-dotenv 설치 시 자동 로드)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[INFO] .env 파일 로드 완료")
except ImportError:
    print("[WARN] python-dotenv 미설치 — 환경 변수를 직접 설정하거나 pip install python-dotenv 실행")

# ── 설정 ──────────────────────────────────────────────────
USERNAME = os.getenv("OPENSKY_USERNAME", "")
PASSWORD = os.getenv("OPENSKY_PASSWORD", "")

# 한반도 + 주변 바운딩 박스
LAT_MIN = float(os.getenv("OPENSKY_LAT_MIN", "33.0"))
LAT_MAX = float(os.getenv("OPENSKY_LAT_MAX", "38.9"))
LON_MIN = float(os.getenv("OPENSKY_LON_MIN", "124.0"))
LON_MAX = float(os.getenv("OPENSKY_LON_MAX", "130.0"))

BASE_URL = "https://opensky-network.org/api"

# ── 컬럼 정의 (OpenSky states/all 응답 순서) ──────────────
STATE_FIELDS = [
    "icao24", "callsign", "origin_country", "time_position",
    "last_contact", "longitude", "latitude", "baro_altitude",
    "on_ground", "velocity", "true_track", "vertical_rate",
    "sensors", "geo_altitude", "squawk", "spi", "position_source"
]


def get_auth():
    """인증 정보 반환 (없으면 익명 요청)"""
    if USERNAME and PASSWORD:
        return (USERNAME, PASSWORD)
    return None


def test_states_all():
    """1. 항공기 상태 조회 (한반도 영역)"""
    print("\n" + "="*55)
    print("TEST 1 — 항공기 상태 조회 (states/all)")
    print("="*55)

    params = {
        "lamin": LAT_MIN, "lomin": LON_MIN,
        "lamax": LAT_MAX, "lomax": LON_MAX,
    }
    auth = get_auth()
    mode = "인증" if auth else "익명(제한적)"
    print(f"[INFO] 요청 모드: {mode}")
    print(f"[INFO] 바운딩 박스: lat({LAT_MIN}~{LAT_MAX}), lon({LON_MIN}~{LON_MAX})")

    try:
        resp = requests.get(f"{BASE_URL}/states/all", params=params, auth=auth, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        states = data.get("states") or []
        ts = data.get("time", 0)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        print(f"[OK] 응답 시각: {dt}")
        print(f"[OK] 탐지 항공기 수: {len(states)}대")

        if states:
            print("\n── 상위 5개 항공기 ──────────────────────────")
            for s in states[:5]:
                flight = dict(zip(STATE_FIELDS, s))
                callsign = (flight.get("callsign") or "N/A").strip()
                lat = flight.get("latitude")
                lon = flight.get("longitude")
                alt = flight.get("baro_altitude")
                vel = flight.get("velocity")
                print(
                    f"  ICAO: {flight['icao24']} | 콜사인: {callsign:8s} | "
                    f"위도: {lat} | 경도: {lon} | "
                    f"고도: {alt}m | 속도: {vel}m/s"
                )

            # 샘플 JSON 저장
            sample = [dict(zip(STATE_FIELDS, s)) for s in states[:10]]
            out_path = "sample_flight_position.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"time": ts, "states": sample}, f, ensure_ascii=False, indent=2)
            print(f"\n[SAVED] 샘플 10건 → {out_path}")
        else:
            print("[WARN] 현재 해당 구역에서 탐지된 항공기가 없습니다.")

        return True

    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] HTTP {resp.status_code} — {e}")
        if resp.status_code == 401:
            print("  → .env 파일의 OPENSKY_USERNAME / PASSWORD 를 확인하세요.")
        elif resp.status_code == 429:
            print("  → 요청 한도 초과. 잠시 후 재시도하세요.")
        return False
    except Exception as e:
        print(f"[ERROR] 요청 실패: {e}")
        return False


def test_flights_aircraft(icao24: str):
    """2. 특정 항공기 비행 이력 조회"""
    print("\n" + "="*55)
    print(f"TEST 2 — 특정 항공기 이력 조회 (icao24={icao24})")
    print("="*55)

    now = int(time.time())
    begin = now - 3600  # 1시간 전

    params = {"icao24": icao24, "begin": begin, "end": now}
    auth = get_auth()

    try:
        resp = requests.get(f"{BASE_URL}/flights/aircraft", params=params, auth=auth, timeout=15)
        resp.raise_for_status()
        flights = resp.json()

        print(f"[OK] 최근 1시간 비행 기록: {len(flights)}건")
        for f in flights[:3]:
            dep = f.get("estDepartureAirport") or "Unknown"
            arr = f.get("estArrivalAirport") or "Unknown"
            print(f"  출발: {dep} → 도착: {arr}")
        return True

    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            print(f"[INFO] 최근 1시간 내 기록 없음 (icao24={icao24})")
        else:
            print(f"[ERROR] HTTP {resp.status_code} — {e}")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║   SkyOps Intelligence — OpenSky API 연결 테스트     ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # TEST 1: 항공기 상태 조회
    ok = test_states_all()

    if ok:
        # TEST 2: 첫 번째 항공기의 이력 조회 (샘플)
        # 실제 ICAO24 코드를 states/all 결과에서 가져옴
        sample_icao = "71bf5c"  # Korean Air 샘플 코드 (실제 결과로 교체됨)
        try:
            with open("sample_flight_position.json", "r") as f:
                data = json.load(f)
            if data["states"]:
                sample_icao = data["states"][0]["icao24"]
        except Exception:
            pass
        test_flights_aircraft(sample_icao)

    print("\n" + "="*55)
    print("테스트 완료!")
    if not ok:
        print("[다음 단계] .env 파일에 OPENSKY_USERNAME / PASSWORD 를 입력 후 재실행하세요.")
    else:
        print("[다음 단계] Kafka Producer 구현으로 진행하세요. (2주차)")
    print("="*55)


if __name__ == "__main__":
    main()
