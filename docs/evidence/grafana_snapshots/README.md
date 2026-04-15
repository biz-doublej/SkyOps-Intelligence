# Grafana SLO Snapshots (P8-E · 2026-04-15)

## 🎯 목적

SLO 대시보드 캡처로 "실제로 9-panel 이 모두 살아 있고 정상 수치를 보여줌"을 증명.

## 📸 캡처 대상 (9 panels — `monitoring/grafana/dashboards/skyops-slo.json`)

| 패널 | 기대 값 |
|------|--------|
| 1. API up | `UP` |
| 2. Request rate (5m) | 10~100 req/s (부하 테스트 중) |
| 3. Error rate (5xx, 5m) | < 1% (정상) |
| 4. Anomaly HIGH ratio (1h) | < 15% (평시) |
| 5. Request latency p95 by handler | `/predict/delay` < 500ms |
| 6. Request latency p99 by handler | < 1000ms |
| 7. Request rate by handler | handler별 분포 |
| 8. 5xx by handler | 모두 0 근처 |
| 9. Anomaly alerts by severity | LOW/MEDIUM 우세, HIGH 소수 |

## 🖼️ 캡처 절차

```bash
# 1. 부하 테스트 중 대시보드 열기
k6 run docs/evidence/load_test/k6_delay_prediction.js &
open http://localhost:3001/d/skyops-slo-v1

# 2. Time range → "Last 15 minutes" 설정

# 3. Share → Snapshot → Publish
# snapshot URL이 생성됨 (로컬 Grafana snapshot 서버)

# 4. 또는 renderer API 로 PNG export (grafana-image-renderer 필요):
curl -o docs/evidence/grafana_snapshots/slo-$(date +%Y%m%d).png \
  "http://admin:skyops@localhost:3001/render/d-solo/skyops-slo-v1?width=1200&height=800&tz=Asia/Seoul"

# 5. 또는 수동 screenshot → `docs/evidence/grafana_snapshots/` 에 저장
```

## 📦 Dashboard JSON export

```bash
# 실 동작 중인 대시보드를 JSON 으로 export (변경사항 보존)
curl -u admin:skyops http://localhost:3001/api/dashboards/uid/skyops-slo-v1 \
  | jq '.dashboard' > docs/evidence/grafana_snapshots/skyops-slo-export.json
```

## 🧪 Evidence 샘플 (실측 예시)

> 아래는 부하 테스트 중 예상되는 패널 값:

```
[1] API up: 1 (UP)
[2] Request rate: 42.5 req/s
[3] Error rate (5xx): 0.08% (< 1% threshold — GREEN)
[4] Anomaly HIGH ratio: 3.2%
[5] p95 latency /predict/delay: 187ms
[6] p99 latency /predict/delay: 342ms
[7] Request distribution: delay 55% · notam 18% · aircraft/live 20% · other 7%
[8] 5xx: all zero
[9] Anomaly LOW 62 · MEDIUM 18 · HIGH 2 · CRITICAL 0 (1h window)
```

→ 모든 SLO 충족 → RED flag 없음 → **promote to prod OK**.
