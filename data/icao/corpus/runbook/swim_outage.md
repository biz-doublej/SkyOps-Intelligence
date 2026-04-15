---
source: SkyOps Internal Runbook
domain: runbook
section: FAA SWIM Outage Response
lang: en+ko
---

# Runbook — FAA SWIM Subscriber Outage

## Symptoms

- Kafka topic `notam` 에 새 메시지 30분 이상 없음
- swim_subscriber.py 로그에 `SOLCLIENT_SUBCODE_*` 에러 반복
- /aircraft/live는 정상 (OpenSky는 별도 채널)

## 1단계 — 인증/연결 확인

```bash
# Trust store 무결성 확인 (c_rehash 형식)
ls -la data/secrets/swim_trust/*.0
openssl x509 -in data/secrets/swim_trust/digicert_g2_root.pem -noout -dates

# 연결 테스트
echo | openssl s_client -connect ems2.swim.faa.gov:55443 \
  -servername ems2.swim.faa.gov 2>&1 | grep -E "subject=|issuer="
```

## 2단계 — 인증 정보 확인

- .env의 SWIM_USERNAME / SWIM_PASSWORD 만료 여부 (FAA SWIM portal)
- 90일 비밀번호 만료 정책 → 미리 swim.aim.faa.gov 에서 갱신
- 연 1회 NDA 갱신 필요

## 3단계 — Solace queue 상태

FAA SWIM portal 에서 my queue depth 확인:
- Depth > 10000 → backpressure (consumer 처리 속도 부족)
- 0 → publisher side issue (FAA infrastructure 문제 가능성)

## 4단계 — Fallback

SWIM 1시간 이상 장애:
1. `NOTAM_MODE=mock python pipeline/notam_producer.py` 로 임시 전환
2. /chat 응답에 "NOTAM 데이터는 mock 데이터를 사용 중입니다" 배너 표시
3. FAA SWIM portal에서 incident ticket 발행

## 5단계 — Postmortem

- swim_subscriber.py 의 reconnection retry 로직 적정성 검토
- DLQ (dead letter queue)에 실패한 메시지가 있다면 reprocess
- 장애 기간 동안 누락된 NOTAM 수동 ingest (FAA NOTAM API REST 백업 경로)

## 관련

- AC 91-70 (Oceanic Ops) — 해양 구간 alternative communication
- ICAO Annex 15 — AIS 책임
