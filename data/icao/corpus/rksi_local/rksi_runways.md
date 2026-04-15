---
source: RKSI AIP (Aeronautical Information Publication)
domain: rksi_local
section: Incheon International - Runway Configuration
lang: en+ko
---

# RKSI 인천국제공항 — 활주로 구성

## 4 활주로 시스템

| Runway | Length | Width | ILS | Notes |
|--------|--------|-------|-----|-------|
| 15L/33R | 12,303 ft (3,750 m) | 60 m | CAT IIIb | 주로 이륙 |
| 15R/33L | 11,811 ft (3,600 m) | 60 m | CAT IIIb | 주로 착륙 |
| 16/34 | 13,123 ft (4,000 m) | 60 m | CAT IIIb | 양방향 운영 |
| 16R/34L | 11,811 ft (3,600 m) | 60 m | CAT IIIb | (제2여객터미널 측) |

## Standard Operating Configurations

- **South Flow (15L/15R/16 이륙, 33R/33L/34 착륙)**: 풍향 110~250° 및 풍속 5kt 이상
- **North Flow (33L/33R/34 이륙, 15L/15R/16 착륙)**: 풍향 290~70° 및 풍속 5kt 이상
- 무풍 시: 소음 영향 분산 위해 시간대별 배정 (주간 South, 야간 North)

## CAT IIIb Minimums

- DH (Decision Height): 50 ft 미만 (또는 무 DH)
- RVR (Runway Visual Range): 75 m 이상
- ILS GP/LOC integrity: monitored, automatic switchover

## 야간 운영 제한 (커튜)

- 23:00 ~ 06:00 KST: 도착편 우선, Stage 4 미인증 항공기 운영 금지
- Stage 3 noisy 기종: chap 3 noise standard 위반 항공편은 전용 fee 부과
- 활주로 폐쇄 (정비) 사전 NOTAM 예고 7일

## SkyOps와 연결

`pipeline/notam_producer.py mock` 시 RKSI runway closure 시나리오는 본 문서의 활주로 ID(15L/15R/16/16R)를 사용한다. ML phase classifier는 이착륙 결정 시 RKSI의 ILS DH/RVR 임계값을 인지해야 한다.
