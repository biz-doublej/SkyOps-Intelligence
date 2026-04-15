---
source: FAA AC 91-70B (Oceanic and Remote Continental Airspace Operations)
domain: faa_ac
section: Advisory Circular - Oceanic Ops
lang: en+ko
---

# AC 91-70B — Oceanic Operations (해양 운항)

## NAT (North Atlantic) Track System

NAT OTS(Organized Track System)는 매일 항공 교통량과 풍향에 맞춰 westbound/eastbound 트랙 5~7개를 발행한다. RVSM(Reduced Vertical Separation Minima) FL290~FL410 구간에서 1000ft 수직 분리를 적용해 capacity를 두 배로 늘렸다.

## CPDLC / ADS-C

해양 구간은 VHF 음성 통신 범위를 벗어나 CPDLC(Controller-Pilot Data Link Communication)와 ADS-C(Automatic Dependent Surveillance - Contract)로 communication과 surveillance를 수행. SkyOps의 FlightPositionEvent는 ADS-C의 14-min 또는 event-based contract reporting을 정상 ingestion한다.

## Strategic Lateral Offset Procedure (SLOP)

조종사 자율로 우측으로 0/1/2 NM offset 운항. GPS 정확도 향상으로 정중앙 운항 시 충돌 위험이 통계적으로 증가하기 때문. NAT MNPS 영역 표준.

## Plotting / Position Reporting

- Mandatory report points: 매 10°  longitude
- Required report items: position, time, FL, next waypoint ETA, next-next waypoint identifier
- 음성/CPDLC failure 시 PMR (Position Mandatory Report) on HF backup
