---
source: SkyOps Internal Runbook
domain: runbook
section: Incident Response - P1 (Critical)
lang: en+ko
---

# Runbook — P1 Incident Response (SLO breach 또는 모델 실패)

## Trigger 조건 (Grafana 알람 기준)

- `ApiHighErrorRate`: API 5xx > 1% 5분 지속
- `DelayLatencyHigh`: /predict/delay p95 > 500ms 10분 지속
- `AnomalyPrecisionDrift`: HIGH severity ratio가 24h baseline 대비 +15pp
- `IFModelStaleAlert`: data/models/.reload_signal 24h 이상 미갱신

## 1단계 — 즉시 대응 (0~5분)

1. PagerDuty 알람 확인 → on-call engineer + ML team lead 동시 호출
2. Grafana SkyOps SLO 대시보드에서 영향 범위 확인 (handler별 latency / error)
3. Jaeger UI에서 최근 trace span 확인 — 어떤 단계가 느린가?
4. /health endpoint 확인 — 모델 가용성, vLLM URL, Feast block

## 2단계 — Mitigate (5~15분)

- 모델 inference 실패: `kubectl rollout undo deployment/api -n skyops`로 직전 버전 롤백
- vLLM 응답 지연: vLLM container 재시작, GPU 사용률 nvidia-smi 확인
- Conformal 폭주 (interval width > 60min): conformal_calibrator.pkl 무결성 확인, fallback 모드 활성화
- ChromaDB lock 이슈: `data/vectordb/` 읽기 전용 마운트 확인

## 3단계 — Root cause (15~60분)

1. MLflow에서 직전 batch 학습 metric 확인 — 데이터 drift 감지?
2. EvidentlyAI report 생성: `python monitoring/drift_detector.py`
3. Active learning report 확인 — FP rate 급증?
4. SWIM subscriber log 확인 — 외부 NOTAM 폭주?

## 4단계 — Postmortem (~24h 내)

- Postmortem doc 작성 (blameless format)
- ADR 갱신 필요 시 `docs/adr/ADR-XXX.md` 신규 작성
- Runbook 업데이트 — 이번 incident에서 발견한 step 추가

## 에스컬레이션

- P1 unresolved > 30min: VP Engineering 호출
- 항공 안전 영향 가능성: 즉시 안전 부서 + (실 운영) ATC 운영센터 통지
