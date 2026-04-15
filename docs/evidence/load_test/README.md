# Load Test Evidence (P8-E · 2026-04-15)

SLO 가 실제로 지켜지는지 증명하기 위한 재현 가능한 부하 테스트.

## 📜 시나리오

| 단계 | 지속 | VUs | 목적 |
|------|-----|-----|------|
| warmup | 1min | 10 | JIT warm-up, cache 채우기 |
| ramp | 2min | 10→30 | latency 변화 관찰 |
| steady | 5min | 50 | 실운영 가정 부하 |
| cool | 2min | 30→0 | graceful |

## 🎯 Pass/fail gates

| 지표 | 임계값 | 근거 |
|-----|-------|------|
| p95 latency | < 500ms | ADR-001 delay-inference SLO |
| p99 latency | < 1000ms | ADR-001 tail latency budget |
| error rate | < 1% | 99% 가용성 |
| check rate | > 99% | 전체 assertion pass |

## 🏃 실행

```bash
# Local Docker Compose
k6 run docs/evidence/load_test/k6_delay_prediction.js

# NAS (다른 IP)
k6 run --env BASE_URL=http://192.168.0.100:8000 \
  --summary-export docs/evidence/load_test/summary-nas.json \
  docs/evidence/load_test/k6_delay_prediction.js

# 결과 저장
k6 run --out json=docs/evidence/load_test/full-results.json \
  docs/evidence/load_test/k6_delay_prediction.js
```

## 📊 결과 해석

```json
// summary.json (k6 handleSummary output)
{
  "p50_ms": 45,
  "p95_ms": 180,
  "p99_ms": 320,
  "error_rate": 0.0012,
  "total_requests": 12450
}
```

**PASS 기준**: 위 예시는 p95 180ms, p99 320ms로 SLO 충족 → 증거로 commit.

## 📸 Evidence 수집

부하 테스트 실행 후:
1. `summary-*.json` 저장 → 이 디렉토리에 commit
2. Grafana SLO 대시보드 스냅샷 캡처 → `../grafana_snapshots/load-test-YYYYMMDD.png`
3. Jaeger trace 에서 slowest p99 요청 선정 → PNG 저장

## 🧪 스트레스 테스트 (spike)

정상 부하 위에 200 VU 스파이크 20s. SLO 회복 시간 측정:

```bash
k6 run --stage 2m:50 --stage 20s:200 --stage 2m:50 \
  docs/evidence/load_test/k6_delay_prediction.js
```

예상: 스파이크 중 p95 briefly > 500ms, 종료 후 30s 내 회복. 회복 못 하면 HPA trigger.
