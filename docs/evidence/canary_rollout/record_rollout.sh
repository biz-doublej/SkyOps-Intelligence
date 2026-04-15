#!/usr/bin/env bash
# SkyOps canary rollout recorder (P8-E · 2026-04-15)
# ============================================================================
# Argo Rollouts 진행 상황 + AnalysisRun 결과를 evidence 로 캡처.
# 각 step 종료 후 kubectl get 결과 + Prometheus 메트릭 스냅샷 저장.
#
# Usage:
#   bash docs/evidence/canary_rollout/record_rollout.sh <namespace> <rollout-name>
#   bash docs/evidence/canary_rollout/record_rollout.sh skyops skyops-api

set -euo pipefail

NAMESPACE="${1:-skyops}"
ROLLOUT="${2:-skyops-api}"
OUT_DIR="$(dirname "$0")/runs/$(date -u +%Y%m%d-%H%M%S)"
mkdir -p "$OUT_DIR"

echo "📸 Recording rollout → $OUT_DIR"

# 1. Rollout spec snapshot
kubectl get rollout "$ROLLOUT" -n "$NAMESPACE" -o yaml > "$OUT_DIR/rollout-spec.yaml"

# 2. Live state poll every 30s until promoted or aborted
loop=0
while true; do
  phase=$(kubectl get rollout "$ROLLOUT" -n "$NAMESPACE" -o jsonpath='{.status.phase}')
  weight=$(kubectl get rollout "$ROLLOUT" -n "$NAMESPACE" -o jsonpath='{.status.currentStepWeight}' 2>/dev/null || echo "0")
  step=$(kubectl get rollout "$ROLLOUT" -n "$NAMESPACE" -o jsonpath='{.status.currentStepIndex}' 2>/dev/null || echo "0")

  snapshot_file="$OUT_DIR/state-$(printf '%02d' $loop)-step${step}-w${weight}.yaml"
  kubectl get rollout "$ROLLOUT" -n "$NAMESPACE" -o yaml > "$snapshot_file"

  # Capture AnalysisRuns for this rollout
  kubectl get analysisruns -n "$NAMESPACE" -l rollouts-pod-template-hash \
    -o yaml > "$OUT_DIR/analysisruns-$(printf '%02d' $loop).yaml" 2>/dev/null || true

  # Pull current Prometheus metrics
  if [ -n "${PROM_URL:-}" ]; then
    curl -s "$PROM_URL/api/v1/query?query=skyops:http_request_latency_seconds:p95_5m" \
      > "$OUT_DIR/prom-p95-$(printf '%02d' $loop).json"
    curl -s "$PROM_URL/api/v1/query?query=skyops:http_5xx_rate_5m" \
      > "$OUT_DIR/prom-5xx-$(printf '%02d' $loop).json"
  fi

  echo "  [$loop] phase=$phase  step=$step  weight=${weight}%"

  case "$phase" in
    Healthy|Degraded|Paused|Progressing)
      # continue monitoring
      ;;
    *)
      echo "unknown phase '$phase' — stopping"
      break
      ;;
  esac

  # Terminal?
  if [ "$phase" = "Healthy" ] && [ "$weight" = "100" ]; then
    echo "✅ Rollout healthy at 100% — done"
    break
  fi
  if [ "$phase" = "Degraded" ]; then
    echo "❌ Rollout degraded — abort captured"
    break
  fi

  loop=$((loop + 1))
  if [ $loop -gt 60 ]; then
    echo "⏰ Timeout after 30min — ended capture"
    break
  fi
  sleep 30
done

# 3. Final events + pod list
kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' \
  --field-selector type!=Normal > "$OUT_DIR/events.log" 2>&1 || true
kubectl get pods -n "$NAMESPACE" -l app=skyops-api -o wide > "$OUT_DIR/final-pods.txt"

# 4. Human summary
cat > "$OUT_DIR/SUMMARY.md" <<EOF
# Canary Rollout Evidence — $(date -u +%Y-%m-%dT%H:%M:%SZ)

- **Namespace**: \`$NAMESPACE\`
- **Rollout**: \`$ROLLOUT\`
- **Final phase**: \`$phase\`
- **Final weight**: ${weight}%
- **Snapshots captured**: $((loop + 1))

## Artifacts

- \`rollout-spec.yaml\` — initial Rollout resource
- \`state-NN-stepN-wN.yaml\` — periodic state snapshots (30s interval)
- \`analysisruns-NN.yaml\` — Prometheus gate evaluations
- \`prom-p95-NN.json\` — p95 latency query at each step
- \`prom-5xx-NN.json\` — 5xx rate query at each step
- \`events.log\` — k8s warning events during rollout
- \`final-pods.txt\` — final pod state

## 결과 해석 가이드

**Healthy**: AnalysisRuns 모두 success + weight 100% → promote 성공
**Degraded**: 하나 이상 AnalysisRun 실패 → abort, 구 버전 유지
**Paused**: 수동 promote 대기 중 — 운영자 \`kubectl argo rollouts promote\` 필요
EOF

echo "✅ Evidence saved to $OUT_DIR"
echo "   Review:  cat $OUT_DIR/SUMMARY.md"
