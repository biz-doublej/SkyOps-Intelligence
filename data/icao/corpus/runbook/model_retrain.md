---
source: SkyOps Internal Runbook
domain: runbook
section: Model Retraining
lang: en+ko
---

# Runbook — XGBoost Delay Model Retrain

## Frequency

- 정기 batch 재학습: 월 1회 (매월 첫째 일요일 02:00 KST)
- 트리거 재학습:
  - Test RMSE drift > 5분 (월별 비교)
  - PSI(Population Stability Index) > 0.2 (input feature distribution)
  - Conformal coverage가 85% 미만으로 떨어짐

## Pre-flight checklist

- [ ] data/raw/flights.csv 최신본 다운로드 (한국공항공사 ACDM 또는 BTS)
- [ ] feature_engineering.py 의 RENAME_MAP 신규 컬럼 확인
- [ ] MLflow tracking server 가용성 확인 (`mlflow ui --port 5000`)
- [ ] disk 공간 ≥ 5 GB (5.7M rows × 53 cols 학습 산출물)

## Execution

```bash
PYTHONIOENCODING=utf-8 python analysis/feature_engineering.py
PYTHONIOENCODING=utf-8 python analysis/prepare_dataset.py
PYTHONIOENCODING=utf-8 python analysis/xgboost_model.py --trials 30
```

## Validation gates

- Val RMSE ≤ 25분 (P1 baseline 22.61 대비 회귀 허용 +2.5분)
- Test R² ≥ 0.40 (P1 baseline 0.4328)
- 5-Fold CV std ≤ 3 (P1 baseline 1.51)
- Delay accuracy (Val) ≥ 88%

게이트 통과 시:
```bash
PYTHONIOENCODING=utf-8 python analysis/conformal_calibration.py --mode split
PYTHONIOENCODING=utf-8 python analysis/quantile_regression.py --alpha 0.1 --sample-frac 0.5
PYTHONIOENCODING=utf-8 python analysis/conformal_calibration.py --mode cqr
```

## 신규 모델 배포 (canary)

1. `data/models/xgboost_best.pkl.bak` ← 직전 모델 백업
2. 새 `xgboost_best.pkl` 가 자동으로 자리잡음
3. ModelStore의 `.reload_signal` touch:
   ```bash
   touch data/models/.reload_signal
   ```
4. /predict/delay 한 건 smoke test → 응답 정상 확인
5. Grafana SLO 대시보드에서 5xx rate, p95 latency 1시간 모니터링
6. 이상 시 즉시 `mv xgboost_best.pkl.bak xgboost_best.pkl && touch data/models/.reload_signal`로 롤백
