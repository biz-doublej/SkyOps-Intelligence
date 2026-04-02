"""
SkyOps Intelligence - Week 8: QLoRA fine-tuning for Qwen2.5-7B-Instruct
=========================================================================

Supervised fine-tuning script for the Alpaca-format aviation dataset using:
  - base model: Qwen/Qwen2.5-7B-Instruct  (non-gated, no HF_TOKEN required)
  - quantization: bitsandbytes 4-bit NF4
  - adapter: LoRA (r=64, alpha=16, q/k/v/o_proj)
  - trainer: TRL SFTTrainer

RTX 3070 8GB: max_length=512, batch_size=1, grad_accum=16 으로 동작 확인

Usage:
  python llm_data/fine_tune_qlora.py --preflight-only
  python llm_data/fine_tune_qlora.py
  python llm_data/fine_tune_qlora.py --output-dir data/models/llm/qwen25_7b_run1

Prerequisites:
  1. Install a CUDA-enabled PyTorch build.
  2. pip install -r llm_data/requirements_train.txt
  3. HF_TOKEN 불필요 (Qwen2.5 는 public 모델)
  4. Optionally set WANDB_API_KEY for experiment tracking.

Outputs:
  data/models/llm/<run_name>/
    - checkpoint-*/
    - final_adapter/
    - train_results.json
    - eval_results.json
    - training_summary.json
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRAIN_FILE = PROJECT_ROOT / "data" / "alpaca" / "aviation_alpaca_train.jsonl"
DEFAULT_VAL_FILE = PROJECT_ROOT / "data" / "alpaca" / "aviation_alpaca_val.jsonl"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "models" / "llm"
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_SYSTEM_PROMPT = (
    "You are SkyOps Intelligence, an aviation operations assistant. "
    "Provide concise, accurate, operationally useful answers for dispatchers, "
    "controllers, and airline operations staff."
)


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(PROJECT_ROOT / ".env")


def get_env_value(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def detect_runtime() -> dict:
    info = {
        "torch_installed": False,
        "torch_version": None,
        "cuda_available": False,
        "device_count": 0,
        "gpu_name": None,
        "gpu_memory_gb": None,
        "bf16_supported": False,
        "torch_error": None,
    }
    try:
        torch = importlib.import_module("torch")
    except Exception as exc:
        info["torch_error"] = f"{type(exc).__name__}: {exc}"
        return info

    info["torch_installed"] = True
    info["torch_version"] = getattr(torch, "__version__", "unknown")
    info["cuda_available"] = bool(torch.cuda.is_available())
    if info["cuda_available"]:
        info["device_count"] = int(torch.cuda.device_count())
        info["gpu_name"] = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        info["gpu_memory_gb"] = round(props.total_memory / (1024 ** 3), 2)
        bf16_probe = getattr(torch.cuda, "is_bf16_supported", None)
        if callable(bf16_probe):
            info["bf16_supported"] = bool(bf16_probe())
    return info


def find_missing_modules(names: list[str]) -> list[str]:
    missing = []
    for name in names:
        try:
            importlib.import_module(name)
        except Exception:
            missing.append(name)
    return missing


def is_local_model_path(model_name_or_path: str) -> bool:
    return Path(model_name_or_path).exists()


def parse_target_modules(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def build_user_prompt(example: dict) -> str:
    instruction = example["instruction"].strip()
    user_parts = [instruction]
    input_text = example.get("input", "").strip()
    if input_text:
        user_parts.append(f"[Context]\n{input_text}")
    return "\n\n".join(user_parts)


def convert_to_prompt_completion(example: dict, system_prompt: str) -> dict:
    prompt = []
    if system_prompt:
        prompt.append({"role": "system", "content": system_prompt})
    prompt.append({"role": "user", "content": build_user_prompt(example)})
    completion = [{"role": "assistant", "content": example["output"].strip()}]
    return {"prompt": prompt, "completion": completion}


def estimate_training_steps(
    train_records: int,
    per_device_train_batch_size: int,
    gradient_accumulation_steps: int,
    num_train_epochs: float,
    world_size: int,
) -> tuple[int, int, int]:
    effective_batch = max(
        per_device_train_batch_size * max(world_size, 1) * gradient_accumulation_steps,
        1,
    )
    steps_per_epoch = max(math.ceil(train_records / effective_batch), 1)
    total_steps = max(math.ceil(steps_per_epoch * num_train_epochs), 1)
    return effective_batch, steps_per_epoch, total_steps


def preflight_report(args: argparse.Namespace) -> tuple[dict, list[str], list[str]]:
    load_env()

    summary = {
        "train_file": str(args.train_file),
        "val_file": str(args.val_file),
        "train_rows": count_jsonl_rows(args.train_file),
        "val_rows": count_jsonl_rows(args.val_file),
        "model_name_or_path": args.model_name_or_path,
        "hf_token_found": bool(get_env_value("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN")),
        "wandb_api_key_found": bool(get_env_value("WANDB_API_KEY")),
        "runtime": detect_runtime(),
        "missing_modules": find_missing_modules(
            ["datasets", "transformers", "accelerate", "peft", "trl", "bitsandbytes"]
        ),
    }

    errors: list[str] = []
    warnings: list[str] = []

    if not args.train_file.exists():
        errors.append(f"train 파일이 없습니다: {args.train_file}")
    if not args.val_file.exists():
        errors.append(f"val 파일이 없습니다: {args.val_file}")
    if summary["train_rows"] == 0:
        errors.append("train 데이터가 비어 있습니다.")
    if summary["val_rows"] == 0:
        warnings.append("val 데이터가 비어 있어 eval 단계가 비활성화됩니다.")

    if summary["missing_modules"]:
        errors.append(
            "학습 패키지가 누락되었습니다: "
            + ", ".join(summary["missing_modules"])
            + "  -> pip install -r llm_data/requirements_train.txt"
        )

    runtime = summary["runtime"]
    if not runtime["torch_installed"]:
        errors.append("PyTorch가 설치되어 있지 않습니다.")
    elif not runtime["cuda_available"]:
        errors.append("현재 Python 환경의 PyTorch가 CUDA를 보지 못합니다. GPU 빌드 Torch가 필요합니다.")

    if runtime["gpu_memory_gb"] is not None and runtime["gpu_memory_gb"] < 10:
        warnings.append(
            f"GPU 메모리 {runtime['gpu_memory_gb']}GB 환경입니다. "
            "Qwen2.5-7B QLoRA는 max_length=512, batch_size=1 설정으로 8GB에서 동작합니다."
        )

    # Qwen2.5 는 public 모델 — HF_TOKEN 불필요
    GATED_PREFIXES = ("meta-llama/", "google/gemma", "mistralai/")
    if (
        any(args.model_name_or_path.startswith(p) for p in GATED_PREFIXES)
        and not is_local_model_path(args.model_name_or_path)
        and not summary["hf_token_found"]
    ):
        warnings.append(
            "HF_TOKEN 환경 변수를 찾지 못했습니다. "
            "이미 huggingface-cli login 상태가 아니면 gated model 다운로드가 실패할 수 있습니다."
        )

    if args.report_to == "wandb" and not summary["wandb_api_key_found"]:
        errors.append("report_to=wandb 인데 WANDB_API_KEY 가 없습니다.")
    elif args.report_to == "auto" and not summary["wandb_api_key_found"]:
        warnings.append("WANDB_API_KEY 가 없어 W&B 로깅은 자동 비활성화됩니다.")

    return summary, errors, warnings


def print_preflight(summary: dict, errors: list[str], warnings: list[str]) -> None:
    runtime = summary["runtime"]
    print("=" * 72)
    print("  SkyOps Intelligence - QLoRA Preflight")
    print("=" * 72)
    print(f"  모델:          {summary['model_name_or_path']}")
    print(f"  Train rows:    {summary['train_rows']:,}")
    print(f"  Val rows:      {summary['val_rows']:,}")
    print(f"  HF_TOKEN:      {'yes' if summary['hf_token_found'] else 'no'}")
    print(f"  WANDB_API_KEY: {'yes' if summary['wandb_api_key_found'] else 'no'}")
    print(f"  Torch:         {runtime['torch_version'] or 'missing'}")
    print(f"  CUDA:          {'yes' if runtime['cuda_available'] else 'no'}")
    if runtime["gpu_name"]:
        print(f"  GPU:           {runtime['gpu_name']} ({runtime['gpu_memory_gb']} GB)")
        print(f"  BF16:          {'yes' if runtime['bf16_supported'] else 'no'}")
    if summary["missing_modules"]:
        print(f"  Missing:       {', '.join(summary['missing_modules'])}")

    if warnings:
        print("\n경고:")
        for item in warnings:
            print(f"  - {item}")

    if errors:
        print("\n실행 불가 항목:")
        for item in errors:
            print(f"  - {item}")
    else:
        print("\n실행 가능: 필수 조건 충족")


def maybe_login_wandb(enabled: bool) -> None:
    if not enabled:
        return

    key = get_env_value("WANDB_API_KEY")
    if not key:
        return

    try:
        import wandb

        wandb.login(key=key, relogin=True)
    except Exception as exc:
        print(f"WARN: wandb 로그인 실패: {exc}")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Llama 3.1 8B Instruct QLoRA fine-tuning")
    parser.add_argument("--model-name-or-path", default=DEFAULT_MODEL,
                        help="Hugging Face model id or local model path")
    parser.add_argument("--train-file", type=Path, default=DEFAULT_TRAIN_FILE,
                        help="Alpaca train JSONL path")
    parser.add_argument("--val-file", type=Path, default=DEFAULT_VAL_FILE,
                        help="Alpaca validation JSONL path")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT / "qwen25_7b_qlora",
                        help="Output directory for checkpoints and final adapter")
    parser.add_argument("--run-name", default="skyops-qwen25-7b-qlora",
                        help="Experiment name")
    parser.add_argument("--num-train-epochs", type=float, default=2.0,
                        help="Number of training epochs")
    parser.add_argument("--learning-rate", type=float, default=2e-4,
                        help="Learning rate")
    parser.add_argument("--per-device-train-batch-size", type=int, default=1,
                        help="Per-device train batch size")
    parser.add_argument("--per-device-eval-batch-size", type=int, default=1,
                        help="Per-device eval batch size")
    parser.add_argument("--gradient-accumulation-steps", type=int, default=16,
                        help="Gradient accumulation steps")
    parser.add_argument("--max-length", type=int, default=512,
                        help="Max token length per sample")
    parser.add_argument("--max-train-samples", type=int, default=0,
                        help="Optional limit for train samples (0 = all)")
    parser.add_argument("--max-eval-samples", type=int, default=0,
                        help="Optional limit for eval samples (0 = all)")
    parser.add_argument("--max-steps", type=int, default=-1,
                        help="Optional max optimizer steps override (-1 = use epochs)")
    parser.add_argument("--warmup-ratio", type=float, default=0.03,
                        help="Warmup ratio")
    parser.add_argument("--logging-steps", type=int, default=10,
                        help="Logging interval in steps")
    parser.add_argument("--save-steps", type=int, default=0,
                        help="Checkpoint interval in steps (0 = auto thirds)")
    parser.add_argument("--save-total-limit", type=int, default=3,
                        help="Max retained checkpoints")
    parser.add_argument("--lora-r", type=int, default=64,
                        help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=16,
                        help="LoRA alpha")
    parser.add_argument("--lora-dropout", type=float, default=0.05,
                        help="LoRA dropout")
    parser.add_argument("--target-modules", default="q_proj,k_proj,v_proj,o_proj",
                        help="Comma-separated target modules (Qwen2.5 기본: q/k/v/o_proj)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    parser.add_argument("--report-to", choices=["auto", "wandb", "none"], default="auto",
                        help="Experiment logger")
    parser.add_argument("--resume-from-checkpoint", default=None,
                        help="Optional checkpoint path to resume from")
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT,
                        help="System prompt prepended to every training sample")
    parser.add_argument("--preflight-only", action="store_true",
                        help="Only validate environment and dataset")
    parser.add_argument("--trust-remote-code", action="store_true",
                        help="Allow custom model code from the Hub if needed")
    return parser


def main(args: argparse.Namespace) -> None:
    summary, errors, warnings = preflight_report(args)
    print_preflight(summary, errors, warnings)

    if args.preflight_only:
        sys.exit(0 if not errors else 1)

    if errors:
        print("\n학습을 시작할 수 없습니다. 위 항목을 먼저 해결하세요.")
        sys.exit(1)

    load_env()

    torch = importlib.import_module("torch")
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        set_seed,
    )
    from trl import SFTConfig, SFTTrainer

    hf_token = get_env_value("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN")
    use_wandb = args.report_to == "wandb" or (
        args.report_to == "auto" and bool(get_env_value("WANDB_API_KEY"))
    )

    maybe_login_wandb(use_wandb)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    final_adapter_dir = output_dir / "final_adapter"

    set_seed(args.seed)

    raw_datasets = load_dataset(
        "json",
        data_files={
            "train": str(args.train_file),
            "validation": str(args.val_file),
        },
    )
    train_columns = raw_datasets["train"].column_names
    val_columns = raw_datasets["validation"].column_names
    train_dataset = raw_datasets["train"].map(
        lambda ex: convert_to_prompt_completion(ex, args.system_prompt),
        remove_columns=train_columns,
    )
    eval_dataset = raw_datasets["validation"].map(
        lambda ex: convert_to_prompt_completion(ex, args.system_prompt),
        remove_columns=val_columns,
    )

    if args.max_train_samples > 0:
        train_dataset = train_dataset.select(range(min(args.max_train_samples, len(train_dataset))))
    if args.max_eval_samples > 0:
        eval_dataset = eval_dataset.select(range(min(args.max_eval_samples, len(eval_dataset))))

    world_size = int(os.getenv("WORLD_SIZE", "1"))
    effective_batch, steps_per_epoch, total_steps = estimate_training_steps(
        train_records=len(train_dataset),
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        num_train_epochs=args.num_train_epochs,
        world_size=world_size,
    )
    if args.max_steps > 0:
        total_steps = args.max_steps
    save_steps = args.save_steps or max(total_steps // 3, 1)
    eval_strategy = "steps" if len(eval_dataset) > 0 else "no"
    report_to = ["wandb"] if use_wandb else "none"
    bf16 = bool(summary["runtime"]["bf16_supported"])
    compute_dtype = torch.bfloat16 if bf16 else torch.float16

    print("\n학습 계획:")
    print(f"  Effective batch size: {effective_batch}")
    print(f"  Steps / epoch:        {steps_per_epoch}")
    print(f"  Estimated total step: {total_steps}")
    print(f"  Save steps:           {save_steps}")
    print(f"  Compute dtype:        {'bfloat16' if bf16 else 'float16'}")
    print(f"  Report to:            {report_to}")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name_or_path,
        token=hf_token,
        trust_remote_code=args.trust_remote_code,
        use_fast=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name_or_path,
        token=hf_token,
        trust_remote_code=args.trust_remote_code,
        device_map="auto",
        quantization_config=bnb_config,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=parse_target_modules(args.target_modules),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())

    training_args = SFTConfig(
        output_dir=str(output_dir),
        run_name=args.run_name,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_train_epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        warmup_ratio=args.warmup_ratio,
        logging_steps=args.logging_steps,
        logging_first_step=True,
        report_to=report_to,
        save_strategy="steps",
        save_steps=save_steps,
        save_total_limit=args.save_total_limit,
        eval_strategy=eval_strategy,
        eval_steps=save_steps if eval_strategy == "steps" else None,
        load_best_model_at_end=(eval_strategy == "steps"),
        metric_for_best_model="eval_loss" if eval_strategy == "steps" else None,
        greater_is_better=False if eval_strategy == "steps" else None,
        max_length=args.max_length,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        max_grad_norm=0.3,
        bf16=bf16,
        fp16=not bf16,
        completion_only_loss=True,
        packing=False,
        seed=args.seed,
    )

    trainer_kwargs = {
        "model": model,
        "args": training_args,
        "train_dataset": train_dataset,
        "eval_dataset": eval_dataset if len(eval_dataset) > 0 else None,
        "processing_class": tokenizer,
    }
    try:
        trainer = SFTTrainer(**trainer_kwargs)
    except TypeError:
        trainer_kwargs.pop("processing_class")
        trainer_kwargs["tokenizer"] = tokenizer
        trainer = SFTTrainer(**trainer_kwargs)

    summary_path = output_dir / "training_summary.json"
    training_summary = {
        "created_at": datetime.now().isoformat(),
        "model_name_or_path": args.model_name_or_path,
        "train_file": str(args.train_file),
        "val_file": str(args.val_file),
        "train_records": len(train_dataset),
        "eval_records": len(eval_dataset),
        "runtime": summary["runtime"],
        "quantization": {
            "load_in_4bit": True,
            "bnb_4bit_quant_type": "nf4",
            "bnb_4bit_use_double_quant": True,
            "bnb_4bit_compute_dtype": "bfloat16" if bf16 else "float16",
        },
        "lora": {
            "r": args.lora_r,
            "alpha": args.lora_alpha,
            "dropout": args.lora_dropout,
            "target_modules": parse_target_modules(args.target_modules),
        },
        "training": {
            "run_name": args.run_name,
            "num_train_epochs": args.num_train_epochs,
            "max_steps": args.max_steps,
            "learning_rate": args.learning_rate,
            "per_device_train_batch_size": args.per_device_train_batch_size,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "max_length": args.max_length,
            "max_train_samples": args.max_train_samples,
            "max_eval_samples": args.max_eval_samples,
            "effective_batch_size": effective_batch,
            "steps_per_epoch": steps_per_epoch,
            "estimated_total_steps": total_steps,
            "save_steps": save_steps,
            "save_total_limit": args.save_total_limit,
            "report_to": report_to,
        },
        "parameter_counts": {
            "trainable": int(trainable_params),
            "total": int(total_params),
            "trainable_ratio": round(trainable_params / max(total_params, 1) * 100, 4),
        },
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(training_summary, f, ensure_ascii=False, indent=2)

    print("\n[START] 학습 시작")
    train_result = trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_metrics("train", train_result.metrics)
    trainer.save_state()

    if len(eval_dataset) > 0:
        eval_metrics = trainer.evaluate()
        trainer.save_metrics("eval", eval_metrics)
        training_summary["final_eval_metrics"] = eval_metrics

    final_adapter_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(final_adapter_dir)
    tokenizer.save_pretrained(final_adapter_dir)

    training_summary["finished_at"] = datetime.now().isoformat()
    training_summary["train_metrics"] = train_result.metrics
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(training_summary, f, ensure_ascii=False, indent=2)

    print("\n[DONE] QLoRA 학습 완료")
    print(f"   체크포인트 위치: {output_dir}")
    print(f"   최종 어댑터:      {final_adapter_dir}")
    print(f"   실행 요약:        {summary_path}")


if __name__ == "__main__":
    main(create_parser().parse_args())
