"""
KMA API 응답 구조 진단 스크립트 v3
실행: python debug_kma_response.py
"""
import os, requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
AUTH_KEY = os.getenv("KMA_AUTH_KEY", "")
KST = timezone(timedelta(hours=9))

print(f"[INFO] 인증키: {AUTH_KEY[:6]}...")

now_utc = datetime.now(timezone.utc)
now_kst = datetime.now(KST)
hour_utc = now_utc.replace(minute=0, second=0, microsecond=0)
hour_kst = now_kst.replace(minute=0, second=0, microsecond=0)

print(f"[INFO] UTC: {now_utc.strftime('%Y-%m-%d %H:%M')}  KST: {now_kst.strftime('%Y-%m-%d %H:%M')}")

# ── 테스트 1: air_metar_dec.php ───────────────────────────────
print("\n" + "="*60)
print("TEST 1 — air_metar_dec.php (UTC 현재 정시)")
print("="*60)
tm_utc = hour_utc.strftime("%Y%m%d%H%M")
print(f"tm={tm_utc}")
r = requests.get(
    "https://apihub.kma.go.kr/api/typ01/url/air_metar_dec.php",
    params={"tm": tm_utc, "org": "K", "help": 1, "authKey": AUTH_KEY},
    timeout=15
)
print(f"HTTP: {r.status_code}")
print(r.text[:3000])

# ── 테스트 2: air_metar_dec.php — 1시간 전 ────────────────────
print("\n" + "="*60)
print("TEST 2 — air_metar_dec.php (UTC 1시간 전)")
print("="*60)
tm_prev = (hour_utc - timedelta(hours=1)).strftime("%Y%m%d%H%M")
print(f"tm={tm_prev}")
r2 = requests.get(
    "https://apihub.kma.go.kr/api/typ01/url/air_metar_dec.php",
    params={"tm": tm_prev, "org": "K", "help": 1, "authKey": AUTH_KEY},
    timeout=15
)
print(f"HTTP: {r2.status_code}")
print(r2.text[:3000])

# ── 테스트 3: kma_air_tm.php — 과거 데이터 ────────────────────
print("\n" + "="*60)
print("TEST 3 — kma_air_tm.php (3시간 전 ~ 1시간 전 KST)")
print("="*60)
tm2_k = (hour_kst - timedelta(hours=1)).strftime("%Y%m%d%H%M")
tm1_k = (hour_kst - timedelta(hours=3)).strftime("%Y%m%d%H%M")
print(f"tm1={tm1_k}, tm2={tm2_k}")
r3 = requests.get(
    "https://apihub.kma.go.kr/api/typ01/url/kma_air_tm.php",
    params={"tm1": tm1_k, "tm2": tm2_k, "stn": "0", "help": 0, "authKey": AUTH_KEY},
    timeout=15
)
print(f"HTTP: {r3.status_code}")
print(r3.text[:3000])
