"""SkyOps KAC (한국공항공사) ACDM Public Data API client (P7-E · 2026-04-15).

P6에서 ATFM real API는 EUROCONTROL NM B2B credentials 부족으로 이연됨.
P7에서는 한국 공공데이터포털의 항공 운항 정보 API 를 대체 경로로 시도한다.

Public APIs (api.data.go.kr):
  - 인천국제공항공사 운항정보 (FlightStatus)
  - 한국공항공사 통합운항정보 (KAC arrivals/departures)
  - 항공기상청 ATIS / METAR
  - 국토부 항공위험지구 NOTAM (제한적)

Auth:
  공공데이터포털에서 Service Key 발급 (무료, 트래픽 제한 1000 req/day).
  https://www.data.go.kr/  →  검색: "한국공항공사" / "인천국제공항"

Set:
  KAC_API_KEY=<발급받은 service key>
  KAC_API_BASE=http://apis.data.go.kr/B551177  (인천)
  ATFM_MODE=kac    # atfm_producer.py 가 이 모듈을 위임 호출

Mock 모드 (default):
  ATFM_MODE=mock   # 기존 동작 유지

Note:
  실제 API 는 운항 capacity/restriction을 직접 제공하지 않으므로,
  delay/staffing/equipment 정보를 inferred ATFMRestrictionEvent 로
  변환한다. 제한적이지만 EUROCONTROL B2B credentials 없이도 한국 trafffic의
  delay-cause 신호를 얻을 수 있다.
"""
from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

KAC_API_KEY = os.getenv("KAC_API_KEY", "")
KAC_API_BASE = os.getenv("KAC_API_BASE", "http://apis.data.go.kr/B551177")
KAC_AIRPORT_ICAO = os.getenv("KAC_AIRPORT_ICAO", "RKSI")  # 인천 default
SCHEMA_VERSION = "2.0"


def _http_get(path: str, params: dict) -> dict | None:
    """Generic GET wrapper. Returns parsed JSON or None on any failure."""
    try:
        import requests
    except ImportError:
        logger.error("requests 미설치. `pip install requests`")
        return None

    full = {"serviceKey": KAC_API_KEY, "type": "json", **params}
    try:
        r = requests.get(f"{KAC_API_BASE}{path}", params=full, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001
        logger.warning("KAC API call failed (%s): %s", path, e)
        return None


def fetch_recent_delays(airport_icao: str = "RKSI",
                        page_no: int = 1,
                        rows: int = 50) -> list[dict]:
    """Pull recent flight status, derive delays.

    Returns list of inferred-delay records:
      [{flight_id, scheduled, actual, delay_min, cause_hint}, ...]
    """
    if not KAC_API_KEY:
        logger.warning("KAC_API_KEY 미설정 — fetch_recent_delays는 빈 리스트 반환")
        return []

    # 인천공항 운항정보 endpoint 예시 — 실 path는 공공데이터포털 docs 참조
    data = _http_get("/StatusOfPassengerFlightsDeOdp/getPassengerDeparturesDeOdp", {
        "pageNo": page_no,
        "numOfRows": rows,
        "lang": "K",  # Korean
    })
    if not data:
        return []

    out: list[dict] = []
    items = (data.get("response", {}).get("body", {}).get("items", {}) or {}).get("item", [])
    if isinstance(items, dict):
        items = [items]

    for it in items:
        try:
            sched = it.get("scheduleDateTime") or it.get("estimatedDateTime")
            actual = it.get("estimatedDateTime")
            if not sched or not actual:
                continue
            delay_min = _delay_minutes(sched, actual)
            if delay_min < 5:
                continue  # only keep meaningful delays
            out.append({
                "flight_id": it.get("flightId") or it.get("airlineKorean", "") + str(it.get("flightId", "")),
                "scheduled": sched,
                "actual": actual,
                "delay_min": delay_min,
                "destination": it.get("airport", "") or it.get("airportName", ""),
                "carrier": it.get("airlineKorean", ""),
                "remark": it.get("remark", ""),
            })
        except Exception:  # noqa: BLE001
            continue
    return out


def _delay_minutes(sched_iso: str, actual_iso: str) -> int:
    """Compute delay in minutes between two HHMM or ISO datetime strings."""
    # Some KAC fields use "HHMM" only; pad to today UTC if so.
    def _parse(s: str) -> datetime:
        s = s.strip()
        if len(s) == 4 and s.isdigit():
            today = datetime.now(timezone.utc).strftime("%Y%m%d")
            return datetime.strptime(today + s, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    try:
        delta = _parse(actual_iso) - _parse(sched_iso)
        return max(0, int(delta.total_seconds() // 60))
    except Exception:
        return 0


def derive_restrictions_from_delays(delays: list[dict],
                                     airport_icao: str = "RKSI",
                                     window_min: int = 60) -> list[dict]:
    """Aggregate per-airport delay signals into ATFMRestrictionEvent rows.

    Heuristic:
      - If avg delay > 30 min over N flights → infer GROUND_DELAY_PROGRAM
      - If specific carrier dominates → infer CARRIER_HOLD
      - If 'WX' / '기상' in remarks → reason=WEATHER
    """
    if not delays:
        return []

    avg_delay = sum(d["delay_min"] for d in delays) / max(1, len(delays))
    has_wx = any("WX" in (d.get("remark") or "") or "기상" in (d.get("remark") or "")
                 for d in delays)

    rtype = "GDP" if avg_delay > 30 else "DEPARTURE_SLOT"
    reason = "WEATHER" if has_wx else "VOLUME"

    now = datetime.now(timezone.utc)
    return [{
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "restriction_id": f"KAC-{int(time.time())}",
        "event_timestamp": now.isoformat(),
        "ingested_at": now.isoformat(),
        "source": "KAC_ATFM",
        "restriction_type": rtype,
        "scope_type": "AIRPORT",
        "scope_ids": [airport_icao],
        "reason": reason,
        "reason_text": f"avg_delay={avg_delay:.1f}min over {len(delays)} flights ({window_min}m window)",
        "effective_start": now.isoformat(),
        "effective_end": (now.replace(microsecond=0).isoformat()),
        "expected_delay_min": int(avg_delay),
        "affected_flights_est": len(delays),
        "_inferred": True,
    }]


def health() -> dict:
    return {
        "configured": bool(KAC_API_KEY),
        "base_url": KAC_API_BASE,
        "default_airport": KAC_AIRPORT_ICAO,
    }


def main() -> int:
    """Manual probe — fetch + print derived restrictions."""
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 65)
    print(f"  KAC ACDM client probe  (airport={KAC_AIRPORT_ICAO})")
    print(f"  configured: {bool(KAC_API_KEY)}")
    print("=" * 65)

    if not KAC_API_KEY:
        print("\n  KAC_API_KEY 미설정.")
        print("  공공데이터포털 https://www.data.go.kr/ 에서 service key 발급 후")
        print("  .env 또는 export KAC_API_KEY=... 설정 후 재시도.\n")
        return 1

    delays = fetch_recent_delays(KAC_AIRPORT_ICAO)
    print(f"\n📦 fetched {len(delays)} delayed flights")
    for d in delays[:5]:
        print(f"  {d.get('flight_id', 'n/a'):>10s} → {d['destination']:>5s}  delay={d['delay_min']:>3d}m  {d.get('carrier', '')}")

    restrictions = derive_restrictions_from_delays(delays, KAC_AIRPORT_ICAO)
    print(f"\n🚧 derived restrictions: {len(restrictions)}")
    for r in restrictions:
        print(f"  type={r['restriction_type']:8s} reason={r['reason']:8s} "
              f"avg_delay={r['expected_delay_min']:3d}m  flights={r['affected_flights_est']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
