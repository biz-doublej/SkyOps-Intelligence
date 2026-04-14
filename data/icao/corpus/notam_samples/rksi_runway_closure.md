---
source: Sample NOTAM (synthetic, schema-compliant)
domain: notam_samples
section: RKSI
airport_icao: RKSI
---

# Sample NOTAM — RKSI Runway Closure

## NOTAM A1234/26

```
A1234/26 NOTAMN
Q) RKRR/QMRLC/IV/NBO/A /000/999/3727N12626E005
A) RKSI
B) 2604150800 C) 2604151800
E) RWY 15L/33R CLOSED DUE TO PAVEMENT REPAIR.
   ALTN RWY 15R/33L AVAILABLE. EXPECTED DELAY UP TO 25 MIN DURING PEAK HOURS.
```

## 해설 (한국어)

- **A1234/26**: NOTAM 번호, 2026년 1234번째
- **Q-code QMRLC**: Runway Closed
- **A) RKSI**: 대상 공항 (인천국제공항)
- **B) ~ C)**: 유효 기간 2026-04-15 08:00 ~ 18:00 UTC
- **E)**: 본문 — 활주로 15L/33R 노면 보수 폐쇄, 대체 활주로 15R/33L 사용, 피크 시간 최대 25분 지연 예상

## 운영 영향

- 인천 공항은 병렬 활주로 2쌍(15L/33R, 15R/33L)을 운영하므로 **half closure**에서도 정상 운항 유지 가능
- Peak 시간(06~09, 17~21 KST)에 **capacity 50% 감소** 가능성 → ATFM slot allocation 조정 필요
- 인접 공항 김포(RKSS) 전환 대응 플랜 준비

## 관제 조치

- Tower: 모든 이·착륙 15R/33L 통합 배정
- Ground: taxiway Delta/Echo 경유 재배치, taxi-time +5~8분
- Approach: 33L ILS CAT III 단일 운영
