---
source: Sample NOTAM (synthetic)
domain: notam_samples
section: RKSS
airport_icao: RKSS
---

# Sample NOTAM — RKSS NAVAID Outage

## NOTAM A0567/26

```
A0567/26 NOTAMN
Q) RKRR/QNMAS/IV/BO/AE/000/999/3732N12648E005
A) RKSS
B) 2604160300 C) 2604162200
E) VOR GMP (114.10 MHZ) U/S DUE TO GROUND EQUIPMENT MAINTENANCE.
   RNAV (GNSS) RWY 14R/32L PROCEDURES AVAILABLE AS PRIMARY.
```

## 해설 (한국어)

- **QNMAS**: VOR 운영 상태 변경 (Air Navigation — Aid out of service)
- **GMP**: 김포공항 VOR 식별자
- **U/S**: Unserviceable (사용 불가)
- **효력**: 2026-04-16 03:00 ~ 22:00 UTC

## 운영 영향

- 김포공항 (RKSS)은 VOR GMP 를 terminal navaid로 사용
- VOR 장애 시 **RNAV (GNSS) procedure**가 primary approach로 전환
- GNSS 미장착기 (RNAV 미인증기) 는 영향 받음 → **alternate 공항 (RKSI) 전환** 또는 지연 대기

## 조종사 참고

- Approach chart "RNAV (GNSS) RWY 14R" 확인
- GNSS RAIM (Receiver Autonomous Integrity Monitoring) 정상 동작 사전 확인
- DME (Distance Measuring Equipment) 는 별도 정상 운영 가능

## 관련 PIREP 요청

VOR 복구 예상보다 빠를 수 있으므로, VOR 신호 재개 확인 시 PIREP 권장.
