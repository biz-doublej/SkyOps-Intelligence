"""
SkyOps Intelligence — 모델 BLEU / ROUGE-L 평가
benchmark_eval.jsonl 의 각 항목에 대해 모델 추론을 실행하고
BLEU-1/2/4, ROUGE-L F1 을 계산한 뒤 results 에 저장한다.

Usage:
    # Fine-tuned Qwen 평가
    python evaluation/evaluate_model.py \
        --model data/models/llm/qwen25_7b_qlora/final_adapter \
        --base-model Qwen/Qwen2.5-7B-Instruct \
        --benchmark data/eval/benchmark_eval.jsonl \
        --output data/eval/results_qwen_finetuned.json \
        --tag AviationLLM-Qwen2.5-7B

    # 베이스 모델 평가
    python evaluation/evaluate_model.py \
        --model Qwen/Qwen2.5-7B-Instruct \
        --benchmark data/eval/benchmark_eval.jsonl \
        --output data/eval/results_qwen_base.json \
        --tag Qwen2.5-7B-Base

    # GPU 없을 때 오프라인 BLEU/ROUGE 만 계산 (reference = prediction)
    python evaluation/evaluate_model.py --offline
"""

import argparse
import json
import math
import time
from collections import Counter
from pathlib import Path


# ── BLEU ──────────────────────────────────────────────────────────────────────
def _ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def sentence_bleu(reference: str, hypothesis: str, max_n: int = 4) -> dict[str, float]:
    ref_tok  = reference.split()
    hyp_tok  = hypothesis.split()
    if not hyp_tok:
        return {f"bleu_{n}": 0.0 for n in range(1, max_n + 1)}

    scores = {}
    for n in range(1, max_n + 1):
        ref_ng  = _ngrams(ref_tok,  n)
        hyp_ng  = _ngrams(hyp_tok,  n)
        clipped = sum(min(c, ref_ng[g]) for g, c in hyp_ng.items())
        total   = max(1, len(hyp_tok) - n + 1)
        prec    = clipped / total

        # brevity penalty
        bp = 1.0 if len(hyp_tok) >= len(ref_tok) else math.exp(
            1 - len(ref_tok) / max(1, len(hyp_tok))
        )
        scores[f"bleu_{n}"] = bp * prec
    return scores


# ── ROUGE-L ────────────────────────────────────────────────────────────────────
def _lcs_length(a: list, b: list) -> int:
    m, n = len(a), len(b)
    dp = [0] * (n + 1)
    for i in range(m):
        prev = 0
        for j in range(n):
            temp = dp[j + 1]
            dp[j + 1] = prev + 1 if a[i] == b[j] else max(dp[j + 1], dp[j])
            prev = temp
    return dp[n]


def rouge_l(reference: str, hypothesis: str) -> float:
    ref_tok = reference.split()
    hyp_tok = hypothesis.split()
    if not ref_tok or not hyp_tok:
        return 0.0
    lcs = _lcs_length(ref_tok, hyp_tok)
    prec = lcs / len(hyp_tok)
    rec  = lcs / len(ref_tok)
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


# ── 모델 로드 + 추론 ─────────────────────────────────────────────────────────────
def _normalize_no_split_modules(model) -> None:
    """accelerate 1.13.x 는 set 타입 _no_split_modules 를 처리하지 못한다."""
    no_split = getattr(model, "_no_split_modules", None)
    if isinstance(no_split, set):
        model._no_split_modules = sorted(no_split)


def _build_model_kwargs():
    from transformers import BitsAndBytesConfig
    import torch

    if torch.cuda.is_available():
        compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        return {
            "device_map": {"": 0},
            "quantization_config": BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=compute_dtype,
            ),
            "trust_remote_code": True,
        }

    return {
        "device_map": None,
        "dtype": torch.float32,
        "low_cpu_mem_usage": True,
        "trust_remote_code": True,
    }


def load_model(model_path: str, base_model: str | None):
    """transformers + PEFT LoRA adapter 또는 순수 base model 로드."""
    from transformers import AutoTokenizer, AutoModelForCausalLM

    is_adapter = Path(model_path).is_dir() and (
        Path(model_path, "adapter_config.json").exists()
    )
    model_kwargs = _build_model_kwargs()

    if is_adapter:
        if not base_model:
            raise ValueError("--base-model is required when --model points to a LoRA adapter directory.")

        print(f"[load] LoRA adapter: {model_path}  (base: {base_model})")
        from peft import PeftModel
        tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
        base = AutoModelForCausalLM.from_pretrained(base_model, **model_kwargs)
        _normalize_no_split_modules(base)
        model = PeftModel.from_pretrained(base, model_path)
    else:
        print(f"[load] Base model: {model_path}")
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(model_path, **model_kwargs)

    _normalize_no_split_modules(model)
    model.eval()
    return model, tokenizer


def _get_inference_device(model):
    import torch

    hf_device_map = getattr(model, "hf_device_map", None) or {}
    for device in hf_device_map.values():
        if isinstance(device, int):
            return torch.device(f"cuda:{device}")
        if isinstance(device, str) and device.startswith("cuda"):
            return torch.device(device)

    try:
        return next(model.parameters()).device
    except StopIteration:
        return torch.device("cpu")


def generate_response(model, tokenizer, instruction: str, context: str,
                      max_new_tokens: int = 256) -> str:
    import torch

    prompt = f"### Instruction:\n{instruction}\n"
    if context.strip():
        prompt += f"### Input:\n{context}\n"
    prompt += "### Response:\n"

    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(_get_inference_device(model)) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=1.0,
            pad_token_id=tokenizer.eos_token_id,
        )
    gen_ids = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(gen_ids, skip_special_tokens=True).strip()


# ── 오프라인 모드 (추론 없이 기존 predictions 재사용 or reference=prediction) ────
def offline_evaluate(benchmark_path: Path, output_path: Path, tag: str) -> None:
    """추론 없이 이미 저장된 predictions 파일로 점수만 계산."""
    pred_path = output_path.parent / (output_path.stem + "_predictions.jsonl")
    if not pred_path.exists():
        print(f"[offline] predictions 파일 없음: {pred_path}")
        print("[offline] reference 를 prediction 으로 사용 (upper-bound 시뮬레이션)")
        records = []
        with open(benchmark_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        preds = [(r["reference"], r["reference"]) for r in records]
    else:
        preds = []
        with open(pred_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    preds.append((d["reference"], d["prediction"]))

    _compute_and_save(preds, output_path, tag, elapsed=0.0)


def _compute_and_save(pairs: list[tuple[str, str]], output_path: Path,
                      tag: str, elapsed: float) -> None:
    all_bleu  = {f"bleu_{n}": [] for n in range(1, 5)}
    all_rouge = []
    per_item  = []

    for ref, hyp in pairs:
        b = sentence_bleu(ref, hyp)
        r = rouge_l(ref, hyp)
        for k in all_bleu:
            all_bleu[k].append(b[k])
        all_rouge.append(r)
        per_item.append({"bleu_1": round(b["bleu_1"], 4),
                         "bleu_4": round(b["bleu_4"], 4),
                         "rouge_l": round(r, 4)})

    n = len(pairs)
    summary = {
        "tag":           tag,
        "n_samples":     n,
        "bleu_1":        round(sum(all_bleu["bleu_1"]) / n, 4),
        "bleu_2":        round(sum(all_bleu["bleu_2"]) / n, 4),
        "bleu_4":        round(sum(all_bleu["bleu_4"]) / n, 4),
        "rouge_l":       round(sum(all_rouge) / n, 4),
        "elapsed_sec":   round(elapsed, 1),
    }

    print("\n===== 평가 결과 =====")
    for k, v in summary.items():
        print(f"  {k:20s}: {v}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "per_item": per_item}, f,
                  ensure_ascii=False, indent=2)
    print(f"\n=> {output_path}")


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",      default="Qwen/Qwen2.5-7B-Instruct",
                        help="모델 경로 (HuggingFace ID 또는 local adapter 디렉토리)")
    parser.add_argument("--base-model", default=None,
                        help="LoRA adapter 사용 시 베이스 모델 ID")
    parser.add_argument("--benchmark",  default="data/eval/benchmark_eval.jsonl")
    parser.add_argument("--output",     default="data/eval/results_eval.json")
    parser.add_argument("--tag",        default="model")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--offline",    action="store_true",
                        help="추론 없이 저장된 predictions 로 점수 계산")
    args = parser.parse_args()

    base        = Path(__file__).parent.parent
    bench_path  = base / args.benchmark
    output_path = base / args.output

    if args.offline:
        offline_evaluate(bench_path, output_path, args.tag)
        return

    # --- 실제 추론 ---
    records = []
    with open(bench_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"벤치마크: {len(records)}건")
    model, tokenizer = load_model(args.model, args.base_model)

    pairs = []
    pred_rows = []
    t0 = time.time()

    for i, rec in enumerate(records):
        hyp = generate_response(model, tokenizer,
                                rec["instruction"], rec.get("input", ""),
                                args.max_new_tokens)
        ref = rec["reference"]
        pairs.append((ref, hyp))
        pred_rows.append({
            "id":         rec["id"],
            "type":       rec.get("type", ""),
            "reference":  ref,
            "prediction": hyp,
        })
        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(records)}] elapsed {time.time()-t0:.0f}s")

    elapsed = time.time() - t0

    # predictions 저장
    pred_path = output_path.parent / (output_path.stem + "_predictions.jsonl")
    pred_path.parent.mkdir(parents=True, exist_ok=True)
    with open(pred_path, "w", encoding="utf-8") as f:
        for row in pred_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\npredictions => {pred_path}")

    _compute_and_save(pairs, output_path, args.tag, elapsed)


if __name__ == "__main__":
    main()
