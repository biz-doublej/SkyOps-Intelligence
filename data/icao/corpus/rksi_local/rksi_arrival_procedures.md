---
source: RKSI AIP - STAR
domain: rksi_local
section: Incheon - Standard Arrival Routes
lang: en+ko
---

# RKSI — Standard Arrival Routes (STAR)

## Primary STARs (RWY 33L/33R 운용 시)

- **GUKDO 1A** — 동쪽 도착 (KSCS, GTC 방면)
- **POTON 1A** — 남쪽 도착 (KMC, OLMEN 방면)
- **PUNAM 1A** — 서쪽 도착 (REGOX, IGEBO 방면)
- **REPOV 1A** — 북쪽 도착 (KARBU 방면, North Korea ADIZ 회피 routing)

## Holding Patterns

- **GUKDO**: 17,000 ft, right turns, 4 nm legs
- **OLMEN**: 15,000 ft, left turns, 4 nm legs
- 평균 holding time during peak hours: 8~12분
- ATC가 expected approach time(EAT) 통보

## Speed Restrictions

- FL245 미만에서 250 KIAS
- 10nm final 부터 180 KIAS 이하
- 5nm final 부터 160 KIAS 이하 (평균 turn-on speed)

## Wake Turbulence Categories

ICAO Doc 4444 Appendix 5 + RECAT-EU 기반:
- A380, B748: SUPER (J)
- B777, A350: HEAVY (H)
- A330, B767: HEAVY-MID (분리 7nm)
- B737, A320: MEDIUM (M)
- 분리: HEAVY behind SUPER 6 nm, MEDIUM behind HEAVY 5 nm

## SkyOps anomaly 시나리오

- holding pattern 진입 후 anomaly_score 급증 → ML phase classifier가 APPROACH 로 분류했지만 실제로는 holding (turning circle)
- 해결: phase classifier 에 holding pattern (sustained turn rate + level alt) feature 추가 (P7 후보)
