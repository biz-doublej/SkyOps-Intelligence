"""
10주차 Step 2 — AWQ 4-bit 양자화

병합된 모델(qwen25_7b_merged)에 AutoAWQ를 적용해
4-bit 양자화 모델(qwen25_7b_awq)을 생성합니다.

요구사항:
    pip install autoawq

사용법:
    python serving/02_quantize_awq.py
    python serving/02_quantize_awq.py --model  data/models/llm/qwen25_7b_merged \
                                      --output data/models/llm/qwen25_7b_awq

출력:
    data/models/llm/qwen25_7b_awq/    ← vLLM --quantization awq 로 로드 가능
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

PROJECT_ROOT   = Path(__file__).parent.parent
DEFAULT_MODEL  = str(PROJECT_ROOT / "data/models/llm/qwen25_7b_merged")
DEFAULT_OUTPUT = str(PROJECT_ROOT / "data/models/llm/qwen25_7b_awq")

# AutoAWQ 권장 캘리브레이션 설정 (Qwen2.5 최적값)
AWQ_CONFIG = {
    "zero_point": True,
    "q_group_size": 128,
    "w_bit": 4,
    "version": "GEMM",   # RTX 30xx 계열 최적화 커널
}

# 캘리브레이션 데이터: 항공 관제 도메인 문장 샘플
CALIB_DATA = [
    "Delta 471, cleared for takeoff runway 28R, wind 290 at 12.",
    "United 822, descend and maintain flight level 240, expect lower in 20 miles.",
    "American 305, contact approach on 124.4, good day.",
    "Southwest 178, turn left heading 270, vectors for ILS runway 25L.",
    "N7823Q, squawk 4523 and ident.",
    "FedEx 890, radar contact, fly heading 180, climb and maintain 8,000.",
    "KAL 018, cleared to land runway 33L, wind calm.",
    "JAL 753, go around, I say again, go around, traffic on the runway.",
    "Cactus 1549, turn left heading 270, runway 28 available.",
    "Speedbird 268, descend via the CANRY2 arrival, expect runway 22L.",
    "The aircraft reported unusual fuel consumption and requested priority handling.",
    "Tower, ANA 172 declaring emergency, engine failure, request immediate landing.",
    "Gate B12 departure delayed 35 minutes due to late inbound aircraft.",
    "Weather advisory: moderate turbulence reported between FL250 and FL310 over the Rockies.",
    "NOTAM: Runway 16R/34L closed for maintenance 0600-1800 local.",
    "Airport ground stop in effect due to low visibility, expect 45-minute delays.",
    "Aircraft hold at DUNNO intersection at FL190, expect further clearance at 1430Z.",
    "Departure control, Lufthansa 441 airborne, climbing through 3000 for 15000.",
    "Emirates 215, traffic alert, Boeing 737 at your 2 o'clock, 5 miles, level.",
    "Collins 7, winds changed significantly, would you like a different runway?",
]


def quantize(model_path: str, output_path: str) -> None:
    print("=" * 60)
    print("  SkyOps Intelligence — AWQ 4-bit 양자화")
    print("=" * 60)
    print(f"  입력 모델 : {model_path}")
    print(f"  출력 경로 : {output_path}")
    print(f"  설정      : w_bit=4, group_size=128, version=GEMM")
    print()

    try:
        from awq import AutoAWQForCausalLM
        from transformers import AutoTokenizer
    except ImportError as e:
        print(f"[ERROR] autoawq 패키지 누락: {e}")
        print("  pip install autoawq")
        raise

    t0 = time.time()

    print("[1/4] 토크나이저 로드...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

    print("[2/4] 모델 로드 (float16)...")
    model = AutoAWQForCausalLM.from_pretrained(
        model_path,
        low_cpu_mem_usage=True,
        use_cache=False,
    )

    print("[3/4] AWQ 캘리브레이션 + 양자화 실행...")
    model.quantize(
        tokenizer,
        quant_config=AWQ_CONFIG,
        calib_data=CALIB_DATA,
    )

    print(f"[4/4] 양자화 모델 저장 → {output_path}")
    Path(output_path).mkdir(parents=True, exist_ok=True)
    model.save_quantized(output_path)
    tokenizer.save_pretrained(output_path)

    elapsed = time.time() - t0
    print()
    print(f"✅ AWQ 양자화 완료  ({elapsed:.0f}s)")
    print(f"   경로: {output_path}")
    print()
    print("다음 단계:")
    print("  bash serving/03_run_vllm.sh")


def main() -> None:
    parser = argparse.ArgumentParser(description="AWQ 4-bit 양자화")
    parser.add_argument("--model",  default=DEFAULT_MODEL,  help="병합된 모델 경로")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="AWQ 출력 경로")
    args = parser.parse_args()
    quantize(args.model, args.output)


if __name__ == "__main__":
    main()
