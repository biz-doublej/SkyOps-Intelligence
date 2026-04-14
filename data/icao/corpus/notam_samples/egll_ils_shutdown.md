---
source: Sample NOTAM (synthetic)
domain: notam_samples
section: EGLL
airport_icao: EGLL
---

# Sample NOTAM — EGLL ILS Shutdown

## NOTAM B0789/26

```
B0789/26 NOTAMN
Q) EGTT/QICAS/I /NBO/A /000/999/5128N00028W005
A) EGLL
B) 2604180600 C) 2604181600
E) ILS CAT III RWY 09L U/S DUE TO ANTENNA ALIGNMENT CHECK.
   CAT I APPROACH ONLY AVAILABLE. MINIMA: DH 200 FT, RVR 550 M.
   VAC (VISUAL APPROACH CHART) REFERENCE.
```

## 해설

- **QICAS**: ILS Category status change (CAT I 로 downgrade)
- **EGLL**: London Heathrow
- **운영 제한**: CAT III (DH 50 ft, RVR 200m) → CAT I (DH 200 ft, RVR 550m)
- **기간**: 2026-04-18 06:00 ~ 16:00 UTC

## 영향 분석

Heathrow는 유럽 최대 허브 공항 중 하나로, 저시정 상황에서 CAT III 운영이 필수. CAT I 로 downgrade 시:
- **시정 550m 미만 → 착륙 불가**
- **대체 공항 전환** 필요 (LGW, STN, LTN)
- **Ground Delay Program (GDP)** 발행 가능성 높음

## 조종사 대응

- Alternate 연료 필수 (영국/아일랜드/프랑스 airports)
- 시정 예보 (TAF) 지속 모니터링
- ATC 지시에 따라 holding pattern 또는 go-around 준비

## 운항 관리자 참고

- Airline OCC (Operations Control Center)는 영향 편 재분석
- Priority 화물편 (cargo) 및 long-haul 우선 배정
- 승객 공지 (passenger notification) 준비
