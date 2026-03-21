"""
SkyOps Intelligence — 토픽별 샘플 100건 수집기
================================================
Kafka 3개 토픽에서 각 최대 100건씩 수집하여
pipeline/samples/ 폴더에 JSON으로 저장합니다.

실행:
    python collect_samples.py

전제 조건:
    - docker compose up -d (Kafka 실행 중)
    - opensky_producer.py 또는 metar_producer.py 가 이미 데이터를 전송한 상태
"""

import json, os, sys, time
from datetime import datetime, timezone
from collections import defaultdict

from dotenv import load_dotenv
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPICS = [
    os.getenv("KAFKA_TOPIC_FLIGHT_POSITION", "flight-position"),
    os.getenv("KAFKA_TOPIC_WEATHER_EVENT",   "weather-event"),
    os.getenv("KAFKA_TOPIC_GATE_EVENT",      "gate-event"),
]
TARGET   = 100   # 토픽당 수집 목표
TIMEOUT  = 15    # 초 — 이 시간 동안 메시지 없으면 해당 토픽 종료

os.makedirs("samples", exist_ok=True)

print("=" * 55)
print("  SkyOps — 토픽별 샘플 100건 수집기")
print("=" * 55)
print(f"  브로커  : {KAFKA_BOOTSTRAP_SERVERS}")
print(f"  목표    : 토픽당 최대 {TARGET}건")
print(f"  저장    : pipeline/samples/\n")

# ── 토픽별 개별 수집 (offset=earliest) ───────────────────────
results = {}

for topic in TOPICS:
    print(f"▶ [{topic}] 수집 중...", end=" ", flush=True)
    samples = []

    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            group_id=f"skyops-sampler-{topic}-{int(time.time())}",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            consumer_timeout_ms=TIMEOUT * 1000,
        )

        for record in consumer:
            samples.append(record.value)
            if len(samples) >= TARGET:
                break

        consumer.close()

    except NoBrokersAvailable:
        print("❌ Kafka 브로커 연결 실패. docker compose up -d 확인")
        sys.exit(1)
    except Exception as e:
        print(f"⚠️  오류: {e}")

    results[topic] = samples
    status = f"✅ {len(samples)}건" if samples else "⚠️  0건 (Producer를 먼저 실행하세요)"
    print(status)

# ── 파일 저장 ─────────────────────────────────────────────────
print()
saved_any = False
for topic, msgs in results.items():
    if not msgs:
        continue
    fname = f"samples/sample_{topic.replace('-', '_')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump({
            "topic":    topic,
            "count":    len(msgs),
            "saved_at": datetime.now(tz=timezone.utc).isoformat(),
            "messages": msgs,
        }, f, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(fname) / 1024
    print(f"  💾 {fname}  ({len(msgs)}건, {size_kb:.1f} KB)")
    saved_any = True

if not saved_any:
    print("  ⚠️  저장된 파일 없음. Producer를 실행한 후 다시 시도하세요.")

# ── 요약 ──────────────────────────────────────────────────────
print()
print("=" * 55)
print("  수집 완료 요약")
print("=" * 55)
for topic in TOPICS:
    cnt = len(results.get(topic, []))
    bar = "█" * (cnt // 5) + "░" * ((TARGET - cnt) // 5)
    print(f"  {topic:<22} {bar} {cnt}/{TARGET}건")
print()
