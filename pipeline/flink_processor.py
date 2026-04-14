"""
SkyOps Intelligence — PyFlink 스트림 처리 프로세서
====================================================
3주차: flight-position 토픽 → 5분 윈도우 집계 + CEP + Redis 저장

아키텍처:
  Kafka(flight-position) ──▶ PyFlink ──┬──▶ 5분 윈도우 집계 ──▶ Redis ZSET
                                        └──▶ CEP 룰 평가    ──▶ Redis HASH (이상 이벤트)

실행 방법:
  # 1. Docker 환경 실행
  docker compose up -d

  # 2. JAR 다운로드 (최초 1회)
  chmod +x pipeline/setup_flink_jars.sh
  ./pipeline/setup_flink_jars.sh

  # 3. 프로세서 실행
  pip install apache-flink==1.18.1 redis==5.0.4 geopy==2.4.1
  python pipeline/flink_processor.py

  # 4. Redis 확인
  redis-cli ZRANGE skyops:aircraft:latest 0 -1 WITHSCORES
  redis-cli HGETALL skyops:anomaly:latest
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# ── 로깅 설정 ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("flink_processor")

# ── 설정 ───────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_FLIGHT    = os.getenv("KAFKA_TOPIC_FLIGHT_POSITION", "flight-position")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB   = int(os.getenv("REDIS_DB", "0"))

# 집계 윈도우 설정
WINDOW_SIZE_SEC   = 5 * 60   # 5분 윈도우
WINDOW_SLIDE_SEC  = 30       # 30초마다 평가 (슬라이딩 평가)
HISTORY_MAX_LEN   = 20       # icao24당 최대 이력 보관 수

# Redis 키 네임스페이스
REDIS_KEY_AIRCRAFT_LATEST  = "skyops:aircraft:latest"    # ZSET — score=timestamp
REDIS_KEY_AIRCRAFT_STATE   = "skyops:aircraft:state:{}"  # HASH — 항공기별 최신 상태
REDIS_KEY_AIRCRAFT_PHASE   = "skyops:aircraft:phase:{}"  # HASH — P2 flight phase (2026-04-14)
REDIS_KEY_WINDOW_AGG       = "skyops:window:agg:{}"      # HASH — 윈도우 집계 결과
REDIS_KEY_ANOMALY_STREAM   = "skyops:anomaly:stream"     # LIST — 최근 이상 이벤트
REDIS_KEY_ANOMALY_COUNT    = "skyops:anomaly:count"      # HASH — 유형별 카운트
REDIS_KEY_ANOMALY_DEBOUNCE = "skyops:anomaly:debounce:{}:{}"  # STR TTL — P2 debounce (2026-04-14)
REDIS_AIRCRAFT_TTL_SEC     = 600    # 10분 미수신 시 만료
REDIS_ANOMALY_STREAM_MAX   = 1000   # 이상 이벤트 최대 보관 수
ANOMALY_DEBOUNCE_SEC       = 60     # P2 동일 (icao24, type) 60초 suppression

# ── Redis 초기화 ────────────────────────────────────────────────────────
try:
    import redis

    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )
    r.ping()
    logger.info(f"✅ Redis 연결 성공: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
except ImportError:
    logger.error("❌ redis 패키지 미설치. pip install redis 실행 후 재시도하세요.")
    sys.exit(1)
except Exception as e:
    logger.error(f"❌ Redis 연결 실패: {e}")
    logger.error("   docker compose up -d 로 Redis를 먼저 실행하세요.")
    sys.exit(1)

# ── Kafka Consumer 초기화 ───────────────────────────────────────────────
try:
    from kafka import KafkaConsumer
    from kafka.errors import NoBrokersAvailable
except ImportError:
    logger.error("❌ kafka-python 패키지 미설치. pip install kafka-python 실행 후 재시도하세요.")
    sys.exit(1)

# ── CEP 룰 + Phase Classifier 임포트 ─────────────────────────────────
try:
    from cep_rules import evaluate_all_rules, AnomalyEvent
    from phase_classifier import classify_phase, FlightPhase
except ImportError:
    # pipeline/ 디렉토리 직접 실행 시
    sys.path.insert(0, os.path.dirname(__file__))
    from cep_rules import evaluate_all_rules, AnomalyEvent
    from phase_classifier import classify_phase, FlightPhase


# ── 인메모리 상태 저장소 ───────────────────────────────────────────────
class AircraftStateStore:
    """
    항공기별 이력 & 윈도우 집계를 관리하는 인메모리 저장소.
    PyFlink의 Keyed State와 동일한 역할을 수행합니다.
    (실제 클러스터 모드에서는 Flink Managed State로 교체)
    """

    def __init__(self, history_max: int = HISTORY_MAX_LEN, window_sec: int = WINDOW_SIZE_SEC):
        self.history: dict[str, deque] = defaultdict(lambda: deque(maxlen=history_max))
        self.window_buffer: dict[str, list] = defaultdict(list)
        self.window_sec = window_sec
        self.last_window_eval: dict[str, float] = {}

    def add(self, record: dict) -> None:
        """레코드를 이력 및 윈도우 버퍼에 추가합니다."""
        icao24 = record.get("icao24", "unknown")
        ts = float(record.get("time_position") or record.get("last_contact") or time.time())
        record["_ingested_at"] = ts

        self.history[icao24].append(record)

        # 윈도우 버퍼에 추가 (만료된 항목 제거)
        cutoff = time.time() - self.window_sec
        self.window_buffer[icao24] = [
            r for r in self.window_buffer[icao24]
            if float(r.get("_ingested_at", 0)) >= cutoff
        ]
        self.window_buffer[icao24].append(record)

    def get_previous(self, icao24: str) -> Optional[dict]:
        """직전 레코드를 반환합니다 (현재 레코드는 이미 추가된 상태)."""
        hist = self.history[icao24]
        if len(hist) >= 2:
            return list(hist)[-2]
        return None

    def get_history(self, icao24: str) -> list:
        """이력 리스트를 반환합니다."""
        return list(self.history[icao24])

    def get_window_records(self, icao24: str) -> list:
        """현재 윈도우 내 레코드를 반환합니다."""
        return self.window_buffer[icao24]

    def should_evaluate_window(self, icao24: str) -> bool:
        """윈도우 평가 주기(WINDOW_SLIDE_SEC)가 경과했는지 확인합니다."""
        now = time.time()
        last = self.last_window_eval.get(icao24, 0)
        if now - last >= WINDOW_SLIDE_SEC:
            self.last_window_eval[icao24] = now
            return True
        return False


# ── 윈도우 집계 함수 ───────────────────────────────────────────────────
def aggregate_window(icao24: str, records: list[dict]) -> Optional[dict]:
    """
    5분 윈도우 내 항공기 데이터를 집계합니다.

    Returns:
        집계 결과 딕셔너리 또는 None (레코드 부족 시)
    """
    if not records:
        return None

    alts = [r["baro_altitude"] for r in records if r.get("baro_altitude") is not None]
    vels = [r["velocity"] for r in records if r.get("velocity") is not None]
    lats = [r["latitude"] for r in records if r.get("latitude") is not None]
    lons = [r["longitude"] for r in records if r.get("longitude") is not None]
    vrates = [r["vertical_rate"] for r in records if r.get("vertical_rate") is not None]

    if not (alts and vels):
        return None

    latest = records[-1]

    # 이상 플래그 계산
    alt_range = max(alts) - min(alts)
    vel_range = max(vels) - min(vels)
    anomaly_flag = (
        alt_range > (500 * 0.3048 * 10) or  # 5분 동안 5000ft 이상 변화
        vel_range > (100 * 0.514444 * 5)     # 5분 동안 500kt 이상 변화
    )

    return {
        "icao24": icao24,
        "callsign": (latest.get("callsign") or "N/A").strip(),
        "window_start_ts": int(records[0].get("_ingested_at", 0)),
        "window_end_ts":   int(records[-1].get("_ingested_at", 0)),
        "record_count": len(records),
        # 집계 값
        "avg_altitude_m":    round(sum(alts) / len(alts), 2),
        "min_altitude_m":    round(min(alts), 2),
        "max_altitude_m":    round(max(alts), 2),
        "avg_velocity_m_s":  round(sum(vels) / len(vels), 2),
        "min_velocity_m_s":  round(min(vels), 2),
        "max_velocity_m_s":  round(max(vels), 2),
        "avg_vertical_rate": round(sum(vrates) / len(vrates), 4) if vrates else None,
        "altitude_range_m":  round(alt_range, 2),
        "velocity_range_m_s": round(vel_range, 2),
        # 최신 위치
        "latest_lat": latest.get("latitude"),
        "latest_lon": latest.get("longitude"),
        "latest_altitude_m": latest.get("baro_altitude"),
        "latest_velocity_m_s": latest.get("velocity"),
        "on_ground": latest.get("on_ground"),
        # 이상 플래그
        "anomaly_flag": anomaly_flag,
        "evaluated_at": int(time.time()),
    }


# ── Redis 저장 함수 ────────────────────────────────────────────────────
def save_aircraft_to_redis(record: dict, agg: Optional[dict] = None) -> None:
    """항공기 최신 상태 및 윈도우 집계 결과를 Redis에 저장합니다."""
    icao24 = record.get("icao24", "unknown")
    ts = float(record.get("time_position") or record.get("last_contact") or time.time())
    pipeline = r.pipeline()

    try:
        # 1. ZSET — 항공기 최신 타임스탬프 인덱스 (score = timestamp)
        pipeline.zadd(REDIS_KEY_AIRCRAFT_LATEST, {icao24: ts})

        # 2. HASH — 항공기별 최신 상태
        state_key = REDIS_KEY_AIRCRAFT_STATE.format(icao24)
        state_data = {
            "icao24":        icao24,
            "callsign":      (record.get("callsign") or "N/A").strip(),
            "latitude":      str(record.get("latitude") or ""),
            "longitude":     str(record.get("longitude") or ""),
            "baro_altitude": str(record.get("baro_altitude") or ""),
            "velocity":      str(record.get("velocity") or ""),
            "on_ground":     str(record.get("on_ground") or "false"),
            "true_track":    str(record.get("true_track") or ""),
            "vertical_rate": str(record.get("vertical_rate") or ""),
            "updated_at":    str(int(ts)),
        }
        pipeline.hset(state_key, mapping=state_data)
        pipeline.expire(state_key, REDIS_AIRCRAFT_TTL_SEC)

        # 3. HASH — 윈도우 집계 결과
        if agg:
            agg_key = REDIS_KEY_WINDOW_AGG.format(icao24)
            pipeline.hset(agg_key, mapping={k: str(v) for k, v in agg.items() if v is not None})
            pipeline.expire(agg_key, REDIS_AIRCRAFT_TTL_SEC * 2)

        pipeline.execute()

    except Exception as e:
        logger.warning(f"Redis 저장 실패 ({icao24}): {e}")


def save_anomaly_to_redis(event: AnomalyEvent) -> None:
    """이상 이벤트를 Redis에 저장합니다."""
    pipeline = r.pipeline()
    try:
        # 1. LIST — 최근 이상 이벤트 스트림
        pipeline.lpush(REDIS_KEY_ANOMALY_STREAM, json.dumps(event.to_dict(), ensure_ascii=False))
        pipeline.ltrim(REDIS_KEY_ANOMALY_STREAM, 0, REDIS_ANOMALY_STREAM_MAX - 1)

        # 2. HASH — 유형별 / 심각도별 카운터
        pipeline.hincrby(REDIS_KEY_ANOMALY_COUNT, event.anomaly_type, 1)
        pipeline.hincrby(REDIS_KEY_ANOMALY_COUNT, f"{event.anomaly_type}:{event.severity}", 1)
        pipeline.hincrby(REDIS_KEY_ANOMALY_COUNT, "TOTAL", 1)

        pipeline.execute()
    except Exception as e:
        logger.warning(f"Redis 이상 이벤트 저장 실패: {e}")


# ── 통계 출력 ──────────────────────────────────────────────────────────
class ProcessingStats:
    """처리 통계 추적."""

    def __init__(self):
        self.msg_count = 0
        self.anomaly_count = 0
        self.window_evals = 0
        self.start_time = time.time()
        self.last_print_time = time.time()
        self.print_interval = 30  # 30초마다 출력

    def record_message(self):
        self.msg_count += 1

    def record_anomaly(self):
        self.anomaly_count += 1

    def record_window_eval(self):
        self.window_evals += 1

    def maybe_print(self) -> None:
        now = time.time()
        if now - self.last_print_time >= self.print_interval:
            elapsed = now - self.start_time
            rate = self.msg_count / elapsed if elapsed > 0 else 0
            logger.info(
                f"📊 처리 통계 | "
                f"메시지: {self.msg_count}건 ({rate:.1f}/s) | "
                f"윈도우 평가: {self.window_evals}회 | "
                f"이상 탐지: {self.anomaly_count}건 | "
                f"가동 시간: {elapsed/60:.1f}분"
            )
            self.last_print_time = now


# ── 메인 프로세서 ──────────────────────────────────────────────────────
def run_processor() -> None:
    """
    PyFlink 스타일 스트림 처리 메인 루프.

    PyFlink DataStream API 구조:
      KafkaSource → keyBy(icao24) → ProcessFunction (CEP + 윈도우 집계) → RedisSink

    로컬 개발 환경에서는 kafka-python + 인메모리 상태로 동일 로직을 구현합니다.
    클러스터 배포 시: setup_flink_jars.sh 실행 후 flink_processor_cluster.py 로 교체.
    """
    logger.info("╔══════════════════════════════════════════════════╗")
    logger.info("║  SkyOps Intelligence — Flink 스트림 프로세서     ║")
    logger.info("╚══════════════════════════════════════════════════╝")
    logger.info(f"Kafka: {KAFKA_BOOTSTRAP} / 토픽: {TOPIC_FLIGHT}")
    logger.info(f"Redis: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    logger.info(f"윈도우: {WINDOW_SIZE_SEC}초 / 평가 주기: {WINDOW_SLIDE_SEC}초")

    # 상태 저장소 초기화
    store = AircraftStateStore()
    stats = ProcessingStats()

    # Kafka Consumer 설정
    consumer = None
    for attempt in range(5):
        try:
            consumer = KafkaConsumer(
                TOPIC_FLIGHT,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id="skyops-flink-processor",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                value_deserializer=lambda b: json.loads(b.decode("utf-8")),
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                max_poll_records=100,
                consumer_timeout_ms=5000,  # poll 타임아웃
            )
            logger.info(f"✅ Kafka Consumer 연결 성공 (시도 {attempt + 1})")
            break
        except NoBrokersAvailable:
            logger.warning(f"Kafka 브로커 연결 대기 중... ({attempt + 1}/5)")
            time.sleep(5)
    else:
        logger.error("❌ Kafka 연결 실패. docker compose up -d 확인 후 재시도하세요.")
        sys.exit(1)

    # Graceful Shutdown 처리
    running = True
    def _shutdown(sig, frame):
        nonlocal running
        logger.info("\n🛑 종료 신호 수신 — 안전하게 종료 중...")
        running = False
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("🚀 스트림 처리 시작 (Ctrl+C 로 종료)")

    # ── 메인 처리 루프 ─────────────────────────────────────────────────
    while running:
        try:
            for msg in consumer:
                if not running:
                    break

                record = msg.value
                icao24 = record.get("icao24")

                if not icao24:
                    continue

                # 1. 상태 저장소에 추가
                store.add(record)
                stats.record_message()

                # 2. 이전 레코드 조회 및 Phase 분류 (P2 · 2026-04-14)
                previous = store.get_previous(icao24)
                history = store.get_history(icao24)

                phase, phase_conf = classify_phase(record, previous=previous)
                record["_flight_phase"] = phase.value
                record["_phase_confidence"] = phase_conf

                # Redis에 phase 상태 저장 (TTL 10분)
                try:
                    phase_key = REDIS_KEY_AIRCRAFT_PHASE.format(icao24)
                    r.hset(phase_key, mapping={
                        "phase": phase.value,
                        "confidence": round(phase_conf, 4),
                        "updated_at": int(time.time()),
                    })
                    r.expire(phase_key, REDIS_AIRCRAFT_TTL_SEC)
                except Exception as e:
                    logger.debug(f"phase Redis 기록 실패: {e}")

                # 3. CEP 평가 (phase-aware)
                anomaly_events = evaluate_all_rules(
                    record, previous, history,
                    flight_phase=phase.value, phase_confidence=phase_conf,
                )
                for event in anomaly_events:
                    # Debounce: 동일 (icao24, type) 60초 내 재발생 시 HIGH 아니면 suppress
                    dkey = REDIS_KEY_ANOMALY_DEBOUNCE.format(icao24, event.anomaly_type)
                    try:
                        if event.severity != "HIGH" and r.exists(dkey):
                            logger.debug(
                                f"⏳ Debounce: {event.anomaly_type} {icao24} 억제 "
                                f"(severity={event.severity})"
                            )
                            continue
                        r.setex(dkey, ANOMALY_DEBOUNCE_SEC, "1")
                    except Exception as e:
                        logger.debug(f"debounce 체크 실패: {e}")

                    save_anomaly_to_redis(event)
                    stats.record_anomaly()
                    logger.warning(
                        f"🚨 이상 탐지 [{event.severity}] {event.anomaly_type} "
                        f"phase={event.flight_phase}({event.phase_confidence:.2f}) | "
                        f"{event.callsign} ({icao24}) — {event.description}"
                    )

                # 3. 윈도우 집계 평가 (슬라이딩 방식)
                agg_result = None
                if store.should_evaluate_window(icao24):
                    window_records = store.get_window_records(icao24)
                    agg_result = aggregate_window(icao24, window_records)
                    if agg_result:
                        stats.record_window_eval()
                        if agg_result.get("anomaly_flag"):
                            logger.info(
                                f"⚠️  윈도우 이상 플래그 | {agg_result['callsign']} | "
                                f"고도범위: {agg_result['altitude_range_m']:.0f}m | "
                                f"속도범위: {agg_result['velocity_range_m_s']:.1f}m/s"
                            )

                # 4. Redis 저장 (최신 상태 + 집계 결과)
                save_aircraft_to_redis(record, agg_result)

                # 5. 통계 출력
                stats.maybe_print()

        except StopIteration:
            # consumer_timeout_ms 경과 (메시지 없음) — 계속 대기
            pass
        except Exception as e:
            logger.error(f"처리 오류: {e}", exc_info=True)
            time.sleep(1)

    # ── 정상 종료 ──────────────────────────────────────────────────────
    if consumer:
        consumer.close()
    logger.info(
        f"✅ 프로세서 종료 | "
        f"총 처리: {stats.msg_count}건 | "
        f"윈도우 평가: {stats.window_evals}회 | "
        f"이상 탐지: {stats.anomaly_count}건"
    )


# ── Redis 상태 조회 유틸리티 ────────────────────────────────────────────
def query_redis_status() -> None:
    """Redis에 저장된 항공기 상태를 조회하여 출력합니다."""
    print("\n" + "="*60)
    print("📡 Redis 저장 현황")
    print("="*60)

    # 활성 항공기 목록 (최근 10분)
    cutoff = time.time() - 600
    aircraft_list = r.zrangebyscore(REDIS_KEY_AIRCRAFT_LATEST, cutoff, "+inf", withscores=True)
    print(f"\n[활성 항공기] {len(aircraft_list)}대 (최근 10분)")

    def _fmt(val: str, fmt: str, fallback: str = " N/A") -> str:
        """빈 문자열·'N/A' 안전 포맷 헬퍼."""
        if val in ("", "N/A", "None", None):
            return fallback
        try:
            return format(float(val), fmt)
        except (ValueError, TypeError):
            return fallback

    for icao24, ts in aircraft_list[:10]:
        state_key = REDIS_KEY_AIRCRAFT_STATE.format(icao24)
        state = r.hgetall(state_key)
        callsign = state.get("callsign", "N/A")
        alt = state.get("baro_altitude", "")
        vel = state.get("velocity", "")
        lat = state.get("latitude", "")
        lon = state.get("longitude", "")
        dt = datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%H:%M:%S")
        print(
            f"  {icao24} | {callsign:8s} | "
            f"고도: {_fmt(alt, '>7.0f'):>7}m | "
            f"속도: {_fmt(vel, '>6.1f'):>6}m/s | "
            f"({lat or 'N/A'}, {lon or 'N/A'}) | {dt} UTC"
        )
    if len(aircraft_list) > 10:
        print(f"  ... 외 {len(aircraft_list) - 10}대")

    # 이상 이벤트 카운트
    anomaly_counts = r.hgetall(REDIS_KEY_ANOMALY_COUNT)
    if anomaly_counts:
        print(f"\n[이상 탐지 누적]")
        for k, v in sorted(anomaly_counts.items()):
            print(f"  {k}: {v}건")

    # 최근 이상 이벤트
    recent = r.lrange(REDIS_KEY_ANOMALY_STREAM, 0, 4)
    if recent:
        print(f"\n[최근 이상 이벤트] (최대 5건)")
        for raw in recent:
            evt = json.loads(raw)
            ts_str = datetime.fromtimestamp(
                evt.get("detected_at", 0) / 1000, tz=timezone.utc
            ).strftime("%H:%M:%S")
            print(
                f"  🚨 [{evt['severity']:6s}] {evt['anomaly_type']:20s} | "
                f"{evt['callsign']:8s} | {evt['description'][:60]} | {ts_str}"
            )

    print("="*60)


# ── 진입점 ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SkyOps Flink 스트림 프로세서")
    parser.add_argument(
        "--query", action="store_true",
        help="Redis 현황만 조회하고 종료 (프로세서 실행 없음)"
    )
    args = parser.parse_args()

    if args.query:
        query_redis_status()
    else:
        run_processor()
