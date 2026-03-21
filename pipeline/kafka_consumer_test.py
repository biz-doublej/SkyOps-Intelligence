"""
SkyOps Intelligence — Kafka Consumer 테스트
============================================
flight-position / weather-event / gate-event 3개 토픽의
메시지 수신 여부를 확인합니다.

실행 방법:
    python kafka_consumer_test.py                  # 3개 토픽 전체 모니터링
    python kafka_consumer_test.py flight-position  # 특정 토픽만
    python kafka_consumer_test.py --save           # 수신 메시지 JSON 저장 (샘플 수집용)
"""

import json
import os
import sys
import signal
import logging
from datetime import datetime, timezone
from collections import defaultdict

from dotenv import load_dotenv
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

load_dotenv()

# ── 로거 ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,  # kafka 내부 로그 숨김
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ConsumerTest")

# ── 설정 ──────────────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
ALL_TOPICS = [
    os.getenv("KAFKA_TOPIC_FLIGHT_POSITION", "flight-position"),
    os.getenv("KAFKA_TOPIC_WEATHER_EVENT",   "weather-event"),
    os.getenv("KAFKA_TOPIC_GATE_EVENT",      "gate-event"),
]

# 토픽별 저장할 샘플 수
SAMPLE_TARGET = 10
TIMEOUT_MS    = 10_000   # 10초 동안 메시지 없으면 종료

# ── Graceful Shutdown ─────────────────────────────────────────
stop = False
def handle_signal(s, f):
    global stop
    stop = True
signal.signal(signal.SIGINT,  handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


# ── 포맷 헬퍼 ─────────────────────────────────────────────────
TOPIC_COLORS = {
    "flight-position": "\033[94m",   # 파랑
    "weather-event":   "\033[92m",   # 초록
    "gate-event":      "\033[93m",   # 노랑
}
RESET = "\033[0m"
BOLD  = "\033[1m"

def fmt_topic(topic: str) -> str:
    color = TOPIC_COLORS.get(topic, "")
    return f"{color}{BOLD}[{topic}]{RESET}"

def fmt_flight(msg: dict) -> str:
    icao     = msg.get("icao24", "?")
    callsign = msg.get("callsign") or "------"
    lat      = msg.get("latitude")
    lon      = msg.get("longitude")
    alt      = msg.get("baro_altitude")
    vel      = msg.get("velocity")
    ground   = "🛬지상" if msg.get("on_ground") else "✈️ 비행"
    return (
        f"  {ground} | ICAO:{icao} | 콜사인:{callsign:<8} | "
        f"위도:{lat} 경도:{lon} | 고도:{alt}m | 속도:{vel}m/s"
    )

def fmt_weather(msg: dict) -> str:
    icao   = msg.get("icao", "?")
    name   = msg.get("airport_name", "")
    temp   = msg.get("temperature_c")
    wind   = msg.get("wind_speed_knots")
    vis    = msg.get("visibility_m")
    pres   = msg.get("pressure_hpa")
    source = msg.get("source", "")
    return (
        f"  [{source}] {icao} {name} | "
        f"기온:{temp}℃ | 풍속:{wind}kt | 시정:{vis}m | 기압:{pres}hPa"
    )

def fmt_gate(msg: dict) -> str:
    return f"  {json.dumps(msg, ensure_ascii=False)}"

FORMATTERS = {
    "flight-position": fmt_flight,
    "weather-event":   fmt_weather,
    "gate-event":      fmt_gate,
}


def run(topics: list, save_samples: bool):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  SkyOps Intelligence — Kafka Consumer 테스트{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"  브로커  : {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"  토픽    : {', '.join(topics)}")
    print(f"  타임아웃: {TIMEOUT_MS//1000}초 (메시지 없으면 자동 종료)")
    if save_samples:
        print(f"  샘플저장: 토픽별 최대 {SAMPLE_TARGET}건 → samples/ 폴더")
    print(f"  종료    : Ctrl+C\n")

    # ── Consumer 생성 ─────────────────────────────────────────
    try:
        consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset="earliest",       # 처음부터 읽기
            enable_auto_commit=False,            # 오프셋 커밋 안 함 (테스트용)
            group_id="skyops-consumer-test",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            consumer_timeout_ms=TIMEOUT_MS,
        )
    except NoBrokersAvailable:
        print("❌ Kafka 브로커에 연결할 수 없습니다. docker compose up -d 확인")
        sys.exit(1)

    # ── 카운터 & 샘플 버퍼 ────────────────────────────────────
    counts  = defaultdict(int)
    samples = defaultdict(list)
    os.makedirs("samples", exist_ok=True)

    print(f"{BOLD}─── 수신 메시지 ────────────────────────────────────{RESET}")

    try:
        for record in consumer:
            if stop:
                break

            topic = record.topic
            msg   = record.value
            counts[topic] += 1
            cnt = counts[topic]

            # 처음 5건만 상세 출력 (이후 10건 단위로 요약)
            if cnt <= 5 or cnt % 10 == 0:
                formatter = FORMATTERS.get(topic, lambda m: str(m))
                print(f"{fmt_topic(topic)} #{cnt}")
                print(formatter(msg))

            # 샘플 수집
            if save_samples and len(samples[topic]) < SAMPLE_TARGET:
                samples[topic].append(msg)

    except Exception as e:
        if not stop:
            print(f"\n⚠️  오류 발생: {e}")
    finally:
        consumer.close()

    # ── 결과 요약 ─────────────────────────────────────────────
    print(f"\n{BOLD}─── 수신 결과 요약 ─────────────────────────────────{RESET}")
    total = 0
    for topic in topics:
        cnt = counts[topic]
        total += cnt
        status = "✅" if cnt > 0 else "⚠️ "
        print(f"  {status} {topic:<22} : {cnt}건 수신")
    print(f"  {'합계':<24} : {total}건")

    # ── 샘플 파일 저장 ────────────────────────────────────────
    if save_samples:
        print(f"\n{BOLD}─── 샘플 저장 ───────────────────────────────────────{RESET}")
        for topic, msgs in samples.items():
            if not msgs:
                continue
            fname = f"samples/sample_{topic.replace('-', '_')}.json"
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "topic":      topic,
                        "count":      len(msgs),
                        "saved_at":   datetime.now(tz=timezone.utc).isoformat(),
                        "messages":   msgs,
                    },
                    f, ensure_ascii=False, indent=2,
                )
            print(f"  💾 {fname} ({len(msgs)}건)")

    print(f"\n{BOLD}{'='*60}{RESET}\n")

    # 수신 실패 토픽 안내
    failed = [t for t in topics if counts[t] == 0]
    if failed:
        print("⚠️  메시지가 없는 토픽:")
        for t in failed:
            if t == "flight-position":
                print(f"  → {t}: opensky_producer.py 를 먼저 실행하세요.")
            elif t == "weather-event":
                print(f"  → {t}: metar_producer.py 를 먼저 실행하세요.")
            elif t == "gate-event":
                print(f"  → {t}: 2주차에서 구현 예정입니다.")
        print()


if __name__ == "__main__":
    args      = sys.argv[1:]
    save_flag = "--save" in args
    args      = [a for a in args if a != "--save"]

    # 토픽 지정 없으면 전체
    topics = args if args else ALL_TOPICS
    # 유효한 토픽만 필터
    topics = [t for t in topics if t in ALL_TOPICS] or ALL_TOPICS

    run(topics, save_flag)
