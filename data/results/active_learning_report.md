# SkyOps Active Learning Report

- **Generated**: 2026-04-14T14:38:54.203124+00:00
- **Total feedback**: 2
- **Date range**: 2026-04-14T14:06:20.802645+00:00 ~ 2026-04-14T14:35:51.967974+00:00 (0일)
- **FP rate**: 50.0%
- **Uncertain rate**: 0.0%

## Label Distribution

| Label | Count | % |
|-------|-------|---|
| false_positive | 1 | 50.0% |
| true_positive | 1 | 50.0% |

## Weekly Trend (최근 12주)

| Week | Count |
|------|-------|
| 2026-W16 | 2 |

## Top Labelers

| Labeler | Count |
|---------|-------|
| analyst_01 | 1 |
| p3 | 1 |

## Recommendations
- 🟡 WARN: FP rate 50.0% > 30% → anomaly rule threshold 재검토 권장
- 📊 Feedback 표본 부족 (n=2) → 최소 50건 이상 수집 후 재분석 권장

## 향후 연동 (P4+)

- **Active Learning query strategy**: uncertainty sampling → 라벨링 요청 queue
- **Per anomaly_type FP rate**: type별 false positive 비율 추적 → CEP threshold 튜닝
- **Monthly Isolation Forest 재학습**: label된 데이터로 contamination 재조정
- **ML phase classifier**: heuristic 대체 (feedback으로 레이블 수집)

## 참고

- Feedback 엔드포인트: `POST /anomaly/feedback` (`serving/routers/anomaly.py`)
- 저장 위치: `data/analyst_feedback/feedback.jsonl`
- Strategic Review 3번 병목 · [[2026-04-14 Strategic Review]]