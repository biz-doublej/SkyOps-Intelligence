#!/usr/bin/env bash
# =============================================================================
#  10주차 Step 3 — vLLM 서버 실행
#  SkyOps Intelligence AviationLLM  (Qwen2.5-7B DPO, AWQ 4-bit)
# =============================================================================
#
#  사용법:
#    bash serving/03_run_vllm.sh             # AWQ 양자화 모델 (권장)
#    bash serving/03_run_vllm.sh --no-awq    # 병합 모델 (FP16, VRAM 16GB+)
#    bash serving/03_run_vllm.sh --sft-only  # SFT 어댑터만 (어댑터 직접 로드)
#
#  포트: 8001 (FastAPI 는 8000 사용)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ── 모델 경로 ─────────────────────────────────────────────────────────
AWQ_MODEL="$PROJECT_ROOT/data/models/llm/qwen25_7b_awq"
MERGED_MODEL="$PROJECT_ROOT/data/models/llm/qwen25_7b_merged"
SFT_ADAPTER="$PROJECT_ROOT/data/models/llm/qwen25_7b_qlora/final_adapter"

PORT=8001
GPU_MEM_UTIL=0.88   # RTX 3070 8GB 최적값
MAX_MODEL_LEN=2048

# ── 인수 처리 ──────────────────────────────────────────────────────────
USE_AWQ=true
SFT_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --no-awq)   USE_AWQ=false  ;;
    --sft-only) SFT_ONLY=true  ;;
  esac
done

# ── 모델 선택 ──────────────────────────────────────────────────────────
if $SFT_ONLY; then
  # SFT LoRA 어댑터 직접 로드 (vLLM >= 0.4 지원)
  MODEL_PATH="Qwen/Qwen2.5-7B-Instruct"
  EXTRA_ARGS="--enable-lora --lora-modules aviation-llm=$SFT_ADAPTER"
  QUANT_ARGS=""
  echo "▶  모드: SFT LoRA 어댑터 직접 로드"
elif $USE_AWQ && [[ -d "$AWQ_MODEL" ]]; then
  MODEL_PATH="$AWQ_MODEL"
  EXTRA_ARGS=""
  QUANT_ARGS="--quantization awq"
  echo "▶  모드: AWQ 4-bit 양자화 모델"
else
  MODEL_PATH="$MERGED_MODEL"
  EXTRA_ARGS=""
  QUANT_ARGS=""
  echo "▶  모드: 병합 모델 FP16"
fi

echo "   모델  : $MODEL_PATH"
echo "   포트  : $PORT"
echo ""

# ── vLLM 설치 확인 ────────────────────────────────────────────────────
if ! python -c "import vllm" 2>/dev/null; then
  echo "[ERROR] vLLM 미설치. 설치 후 재실행:"
  echo "  pip install vllm"
  exit 1
fi

# ── 서버 실행 ──────────────────────────────────────────────────────────
echo "🚀 vLLM 서버 시작..."
python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_PATH" \
  --served-model-name "aviation-llm" \
  --host 0.0.0.0 \
  --port "$PORT" \
  --gpu-memory-utilization "$GPU_MEM_UTIL" \
  --max-model-len "$MAX_MODEL_LEN" \
  --dtype bfloat16 \
  --trust-remote-code \
  $QUANT_ARGS \
  $EXTRA_ARGS
