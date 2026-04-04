"""
10주차 Step 1 — LoRA 어댑터 병합 (merge_and_unload)

DPO 최종 어댑터(qwen25_7b_dpo/final_adapter)를 베이스 모델에
병합하여 독립 실행 가능한 HuggingFace 포맷 모델을 생성합니다.

사용법:
    python serving/01_merge_model.py
    python serving/01_merge_model.py --adapter data/models/llm/qwen25_7b_dpo/final_adapter \
                                     --output  data/models/llm/qwen25_7b_merged

출력:
    data/models/llm/qwen25_7b_merged/   ← vLLM / AWQ 에 바로 공급 가능
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

# ── 기본 경로 ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_ADAPTER = str(PROJECT_ROOT / "data/models/llm/qwen25_7b_dpo/final_adapter")
DEFAULT_OUTPUT  = str(PROJECT_ROOT / "data/models/llm/qwen25_7b_merged")
BASE_MODEL      = "Qwen/Qwen2.5-7B-Instruct"


def merge(adapter_path: str, output_path: str, base_model: str) -> None:
    print("=" * 60)
    print("  SkyOps Intelligence — LoRA 병합 (merge_and_unload)")
    print("=" * 60)
    print(f"  베이스  : {base_model}")
    print(f"  어댑터  : {adapter_path}")
    print(f"  출력    : {output_path}")
    print()

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError as e:
        print(f"[ERROR] 필수 패키지 누락: {e}")
        print("  pip install transformers peft torch accelerate")
        raise

    t0 = time.time()

    # 1. 토크나이저 로드
    print("[1/4] 토크나이저 로드...")
    tokenizer = AutoTokenizer.from_pretrained(
        adapter_path,          # 어댑터 폴더에 저장된 토크나이저 사용
        trust_remote_code=True,
    )

    # 2. 베이스 모델 로드 (bfloat16 — 병합 시 정밀도 유지)
    print("[2/4] 베이스 모델 로드 (bfloat16)...")
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )

    # 3. LoRA 어댑터 로드 후 병합
    print("[3/4] LoRA 어댑터 로드 및 병합...")
    model = PeftModel.from_pretrained(base, adapter_path)
    model = model.merge_and_unload()  # ← 어댑터 가중치를 베이스에 흡수
    model.eval()

    # 4. 저장
    print(f"[4/4] 병합 모델 저장 → {output_path}")
    out = Path(output_path)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_path, safe_serialization=True)
    tokenizer.save_pretrained(output_path)

    elapsed = time.time() - t0
    print()
    print(f"✅ 병합 완료  ({elapsed:.0f}s)")
    print(f"   경로: {output_path}")
    print()
    print("다음 단계:")
    print("  python serving/02_quantize_awq.py")
    print("  bash   serving/03_run_vllm.sh")


def main() -> None:
    parser = argparse.ArgumentParser(description="LoRA 어댑터 병합")
    parser.add_argument("--adapter",    default=DEFAULT_ADAPTER, help="LoRA 어댑터 경로")
    parser.add_argument("--output",     default=DEFAULT_OUTPUT,  help="병합 모델 출력 경로")
    parser.add_argument("--base-model", default=BASE_MODEL,      help="HuggingFace 베이스 모델")
    args = parser.parse_args()
    merge(args.adapter, args.output, args.base_model)


if __name__ == "__main__":
    main()
