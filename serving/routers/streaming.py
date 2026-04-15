"""Streaming router — /aircraft/*, /anomaly/recent, /ws/*.

ADR-001 Migration Phase 1 (2026-04-14 P3).
Redis 기반 dashboard feed 및 WebSocket fanout.
"""

from __future__ import annotations

import asyncio
import json as _json
import time
import traceback

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from common.constants import REDIS_AIRCRAFT_LATEST, REDIS_ANOMALY_STREAM, REDIS_NOTAM_STREAM
from common.redis_client import get_redis, safe_float

router = APIRouter(tags=["dashboard"])


# ── Redis readers (router-local helpers) ─────────────────────────────
def _read_aircraft_from_redis() -> list[dict]:
    r = get_redis()
    if r is None:
        return []
    try:
        cutoff = time.time() - 600  # 최근 10분
        icao_list = r.zrangebyscore(REDIS_AIRCRAFT_LATEST, cutoff, "+inf")
        result = []
        for icao in icao_list[:200]:
            state = r.hgetall(f"skyops:aircraft:state:{icao}")
            if not state or not state.get("latitude"):
                continue
            result.append({
                "icao24": icao,
                "callsign": state.get("callsign", ""),
                "latitude": safe_float(state.get("latitude")) or 0.0,
                "longitude": safe_float(state.get("longitude")) or 0.0,
                "baro_altitude": safe_float(state.get("baro_altitude")) or 0.0,
                "velocity": safe_float(state.get("velocity")) or 0.0,
                "on_ground": state.get("on_ground", "false") == "true",
                "true_track": safe_float(state.get("true_track")) or 0.0,
                "vertical_rate": safe_float(state.get("vertical_rate")) or 0.0,
                "updated_at": safe_float(state.get("updated_at")) or 0.0,
            })
        return result
    except Exception:
        traceback.print_exc()
        return []


def _read_anomalies_from_redis(limit: int = 50) -> list[dict]:
    r = get_redis()
    if r is None:
        return []
    try:
        raw = r.lrange(REDIS_ANOMALY_STREAM, 0, limit - 1)
        return [_json.loads(item) for item in raw if item]
    except Exception:
        return []


# ── REST endpoints ───────────────────────────────────────────────────
@router.get("/aircraft/live")
def get_aircraft_live():
    """실시간 항공기 위치 (Redis 조회)."""
    return _read_aircraft_from_redis()


@router.get("/aircraft/h3")
def get_aircraft_h3(resolution: int = 5):
    """항공기 위치를 H3 헥사곤으로 집계."""
    try:
        import h3
    except ImportError:
        raise HTTPException(status_code=500, detail="h3 라이브러리 미설치: pip install h3")

    aircraft = _read_aircraft_from_redis()
    if not aircraft:
        return []

    hex_counts: dict[str, dict] = {}
    for a in aircraft:
        lat, lng = a.get("latitude", 0), a.get("longitude", 0)
        if lat == 0 and lng == 0:
            continue
        h3_index = h3.latlng_to_cell(lat, lng, resolution)
        if h3_index not in hex_counts:
            cell_lat, cell_lng = h3.cell_to_latlng(h3_index)
            hex_counts[h3_index] = {
                "hex_id": h3_index,
                "latitude": cell_lat,
                "longitude": cell_lng,
                "count": 0,
                "avg_altitude": 0.0,
                "avg_velocity": 0.0,
                "callsigns": [],
            }
        entry = hex_counts[h3_index]
        entry["count"] += 1
        entry["callsigns"].append(a.get("callsign", ""))
        entry["avg_altitude"] += a.get("baro_altitude", 0)
        entry["avg_velocity"] += a.get("velocity", 0)

    for entry in hex_counts.values():
        n = entry["count"]
        if n > 0:
            entry["avg_altitude"] = round(entry["avg_altitude"] / n, 1)
            entry["avg_velocity"] = round(entry["avg_velocity"] / n, 1)
        entry["callsigns"] = entry["callsigns"][:5]

    return list(hex_counts.values())


@router.get("/anomaly/recent")
def get_anomaly_recent(limit: int = 50):
    """최근 이상 탐지 이벤트 (Redis 조회)."""
    return _read_anomalies_from_redis(limit)


# ── P6-G · NOTAM live feed ────────────────────────────────────────────
def _read_notams_from_redis(limit: int = 50,
                            location_icao: str | None = None,
                            severity: str | None = None) -> list[dict]:
    """Read recent NOTAMs from skyops:notam:stream Redis list.

    swim_subscriber.py / notam_producer.py LPUSH json strings.
    """
    r = get_redis()
    if r is None:
        return []
    try:
        # 충분히 가져온 후 필터 (prod에선 별도 인덱스 권장)
        raw = r.lrange(REDIS_NOTAM_STREAM, 0, max(limit * 4, 200) - 1)
    except Exception:
        traceback.print_exc()
        return []

    items: list[dict] = []
    for s in raw:
        try:
            n = _json.loads(s)
        except Exception:
            continue
        if location_icao and (n.get("location_icao") or "").upper() != location_icao.upper():
            continue
        if severity and (n.get("severity") or "").upper() != severity.upper():
            continue
        items.append(n)
        if len(items) >= limit:
            break
    return items


@router.get("/notam/recent")
def get_notam_recent(limit: int = 50,
                     location_icao: str | None = None,
                     severity: str | None = None):
    """Recent NOTAMs (FAA SWIM live or mock).

    Filters:
      location_icao  (e.g. RKSI, EGLL)
      severity       INFO|ADVISORY|WARNING|CRITICAL
    """
    return _read_notams_from_redis(limit=limit,
                                   location_icao=location_icao,
                                   severity=severity)


@router.get("/notam/stats")
def get_notam_stats():
    """Per-airport summary of recent NOTAMs (rolling window)."""
    rows = _read_notams_from_redis(limit=500)
    by_airport: dict[str, dict] = {}
    by_class: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for n in rows:
        ap = (n.get("location_icao") or "UNKNOWN").upper()
        klass = (n.get("notam_class") or "UNKNOWN").upper()
        sev = (n.get("severity") or "INFO").upper()
        by_airport.setdefault(ap, {"airport": ap, "count": 0, "critical": 0,
                                    "warning": 0, "advisory": 0, "info": 0})
        by_airport[ap]["count"] += 1
        by_airport[ap][sev.lower()] = by_airport[ap].get(sev.lower(), 0) + 1
        by_class[klass] = by_class.get(klass, 0) + 1
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        "total": len(rows),
        "by_airport": sorted(by_airport.values(), key=lambda d: -d["count"])[:20],
        "by_class": by_class,
        "by_severity": by_severity,
    }


# ── WebSocket: NOTAM stream (P6-G) ────────────────────────────────────
@router.websocket("/ws/notams")
async def ws_notams(websocket: WebSocket):
    """5초 간격 신규 NOTAM WebSocket push."""
    await websocket.accept()
    last_count = 0
    try:
        while True:
            r = get_redis()
            if r:
                current_count = r.llen(REDIS_NOTAM_STREAM) or 0
                if current_count > last_count:
                    new_n = current_count - last_count
                    data = _read_notams_from_redis(new_n)
                    await websocket.send_json(data)
                    last_count = current_count
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ── WebSocket endpoints ──────────────────────────────────────────────
@router.websocket("/ws/aircraft")
async def ws_aircraft(websocket: WebSocket):
    """3초 간격 항공기 위치 WebSocket push."""
    await websocket.accept()
    try:
        while True:
            data = _read_aircraft_from_redis()
            await websocket.send_json(data)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@router.websocket("/ws/anomalies")
async def ws_anomalies(websocket: WebSocket):
    """1초 간격 신규 이상 이벤트 WebSocket push."""
    await websocket.accept()
    last_count = 0
    try:
        while True:
            r = get_redis()
            if r:
                current_count = r.llen(REDIS_ANOMALY_STREAM) or 0
                if current_count > last_count:
                    new_count = current_count - last_count
                    data = _read_anomalies_from_redis(new_count)
                    await websocket.send_json(data)
                    last_count = current_count
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
