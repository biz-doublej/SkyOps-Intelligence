"""
SkyOps Intelligence — DPOTrainer 선호도 정렬 학습
QLoRA 파인튜닝 완료 어댑터 위에 DPO (Direct Preference Optimization) 를 적용한다.

Reference:
  Rafailov et al., "Direct Preference Optimization: Your Language Model is
  Secretly a Reward Model" (NeurIPS 2023)

Usage:
    python dpo/train_dpo.py \
        --model  data/models/llm/qwen25_7b_qlora/final_adapter \
        --base-model Qwen/Qwen2.5-7B-Instruct \
        --dataset data/dpo/dpo_pairs.jsonl \
        --output-dir data/models/llm/qwen25_7b_dpo

    # 빠른 smoke test (CPU / 소형 모델)
    python dpo/train_dpo.py --smoke-test
"""

import argparse
import inspect
import json
import sys
from pathlib import Path


# ── preflight ─────────────────────────────────────────────────────────────────
def preflight(base_model: str, adapter_dir: str | None, dataset_path: Path) -> bool:
    ok = True

    try:
        import torch
        import transformers
        import trl
        import peft
        print(f"[preflight] torch={torch.__version__}  transformers={transformers.__version__}  trl={trl.__version__}")
        print(f"[preflight] CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                print(f"            GPU {i}: {props.name}  {props.total_memory//1024**3} GB")
    except ImportError as e:
        print(f"[preflight] WARN: {e}")

    if adapter_dir and not Path(adapter_dir).exists():
        print(f"[preflight] WARN: adapter 디렉토리 없음 — {adapter_dir}")
        print("           base model 단독으로 DPO 학습을 진행합니다.")

    if not dataset_path.exists():
        print(f"[preflight] ERROR: DPO 데이터셋 없음 — {dataset_path}")
        print("           먼저 python dpo/build_dpo_pairs.py 를 실행하세요.")
        ok = False

    return ok


# ── Dataset ───────────────────────────────────────────────────────────────────
def load_dpo_dataset(path: Path):
    """JSONL → HuggingFace Dataset (prompt / chosen / rejected)"""
    from datasets import Dataset

    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    return Dataset.from_list([
        {"prompt": r["prompt"], "chosen": r["chosen"], "rejected": r["rejected"]}
        for r in rows
    ])


def truncate_prompt(prompt: str, tokenizer, max_prompt_length: int) -> str:
    tokenized = tokenizer(
        prompt,
        add_special_tokens=False,
        truncation=True,
        max_length=max_prompt_length,
    )
    return tokenizer.decode(tokenized["input_ids"], skip_special_tokens=True)


# ── 학습 ──────────────────────────────────────────────────────────────────────
def train(args) -> None:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import PeftModel, LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import DPOTrainer, DPOConfig

    base = Path(__file__).parent.parent
    dataset_path = base / args.dataset
    output_dir   = base / args.output_dir

    if not preflight(args.base_model, args.model, dataset_path):
        sys.exit(1)

    # ── 토크나이저 ────────────────────────────────────────────────────────────
    print(f"\n[load] tokenizer: {args.base_model}")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"   # DPO requires left-padding

    # ── 베이스 모델 + 기존 LoRA 어댑터 로드 ──────────────────────────────────
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    print(f"[load] base model: {args.base_model}")
    base_model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    base_model = prepare_model_for_kbit_training(base_model)

    adapter_path = base / args.model if not Path(args.model).is_absolute() else Path(args.model)
    if adapter_path.exists() and (adapter_path / "adapter_config.json").exists():
        print(f"[load] LoRA adapter: {adapter_path}")
        model = PeftModel.from_pretrained(base_model, str(adapter_path), is_trainable=True)
    else:
        # 어댑터 없으면 새 LoRA 부착
        print("[load] 새 LoRA adapter 생성 (기존 어댑터 없음)")
        lora_cfg = LoraConfig(
            r=32,
            lora_alpha=16,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(base_model, lora_cfg)

    model.print_trainable_parameters()

    # ── 데이터셋 ──────────────────────────────────────────────────────────────
    print(f"\n[data] {dataset_path}")
    dataset = load_dpo_dataset(dataset_path)
    dpo_config_signature = inspect.signature(DPOConfig.__init__)
    supports_max_prompt_length = "max_prompt_length" in dpo_config_signature.parameters
    if not supports_max_prompt_length:
        print(
            "[compat] installed TRL does not expose max_prompt_length; "
            "prompts will be truncated during dataset prep instead."
        )
        dataset = dataset.map(
            lambda row: {
                "prompt": truncate_prompt(row["prompt"], tokenizer, args.max_prompt_length)
            },
            desc="Truncating prompts",
        )
    split   = dataset.train_test_split(test_size=0.05, seed=42)
    train_ds = split["train"]
    eval_ds  = split["test"]
    print(f"  train={len(train_ds)}  eval={len(eval_ds)}")

    # ── DPO 학습 설정 ─────────────────────────────────────────────────────────
    dpo_config_kwargs = dict(
        output_dir                  = str(output_dir),
        num_train_epochs            = args.epochs,
        per_device_train_batch_size = args.batch_size,
        per_device_eval_batch_size  = args.batch_size,
        gradient_accumulation_steps = args.grad_accum,
        learning_rate               = args.lr,
        beta                        = args.beta,         # DPO temperature
        max_length                  = args.max_length,
        logging_steps               = 10,
        eval_strategy               = "steps",
        eval_steps                  = 50,
        save_strategy               = "steps",
        save_steps                  = 100,
        save_total_limit            = 2,
        warmup_ratio                = 0.1,
        bf16                        = torch.cuda.is_bf16_supported(),
        fp16                        = not torch.cuda.is_bf16_supported() and torch.cuda.is_available(),
        report_to                   = "none",
        run_name                    = "skyops-dpo",
        remove_unused_columns       = False,
    )
    if supports_max_prompt_length:
        dpo_config_kwargs["max_prompt_length"] = args.max_prompt_length
    dpo_config = DPOConfig(**dpo_config_kwargs)

    trainer_kwargs = dict(
        model           = model,
        ref_model       = None,   # implicit reference (PEFT 어댑터 방식)
        args            = dpo_config,
        train_dataset   = train_ds,
        eval_dataset    = eval_ds,
    )
    trainer_signature = inspect.signature(DPOTrainer.__init__)
    if "processing_class" in trainer_signature.parameters:
        trainer_kwargs["processing_class"] = tokenizer
    else:
        trainer_kwargs["tokenizer"] = tokenizer
    trainer = DPOTrainer(**trainer_kwargs)

    print("\n[train] DPO 학습 시작...")
    trainer.train()

    # ── 저장 ──────────────────────────────────────────────────────────────────
    final_dir = output_dir / "final_adapter"
    trainer.model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    print(f"\n[done] DPO 어댑터 저장: {final_dir}")

    # 학습 로그 저장
    log_path = output_dir / "dpo_train_log.json"
    history  = trainer.state.log_history
    with open(log_path, "w") as f:
        json.dump(history, f, indent=2)
    print(f"[done] 학습 로그: {log_path}")


# ── smoke test ────────────────────────────────────────────────────────────────
def smoke_test() -> None:
    """BLEU/ROUGE 계산 + DPO 페어 로직만 확인 (GPU 불필요)"""
    print("[smoke] DPO 페어 열화 함수 테스트")
    sys.path.insert(0, str(Path(__file__).parent))
    from build_dpo_pairs import degrade, detect_type

    samples = [
        {"instruction": "이상 탐지 결과 설명", "input": "",
         "output": "[경고] KE731 — 속도 28초 이내 87.4kt 급등. FAA AIM 7-6-4 기준 확인 교신 필요."},
        {"instruction": "승객 안내방송 작성", "input": "KE731편 기상 지연 30분",
         "output": "KE731편 탑승객 여러분, 기상 악화로 약 30분 지연 출발 예정입니다. 양해해 주시기 바랍니다."},
    ]
    for s in samples:
        dtype    = detect_type(s)
        chosen   = s["output"]
        rejected = degrade(chosen, dtype)
        print(f"  type    : {dtype}")
        print(f"  chosen  : {chosen}")
        print(f"  rejected: {rejected}")
        assert chosen != rejected or len(chosen) < 5, "열화 실패"
        print()

    print("[smoke] OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",            default="data/models/llm/qwen25_7b_qlora/final_adapter",
                        help="SFT 어댑터 경로 (없으면 새 LoRA 생성)")
    parser.add_argument("--base-model",       default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--dataset",          default="data/dpo/dpo_pairs.jsonl")
    parser.add_argument("--output-dir",       default="data/models/llm/qwen25_7b_dpo")
    parser.add_argument("--epochs",           type=int,   default=1)
    parser.add_argument("--batch-size",       type=int,   default=1)
    parser.add_argument("--grad-accum",       type=int,   default=8)
    parser.add_argument("--lr",               type=float, default=5e-5)
    parser.add_argument("--beta",             type=float, default=0.1,
                        help="DPO beta — KL 패널티 계수 (기본 0.1)")
    parser.add_argument("--max-length",       type=int,   default=512)
    parser.add_argument("--max-prompt-length",type=int,   default=256)
    parser.add_argument("--smoke-test",       action="store_true")
    args = parser.parse_args()

    if args.smoke_test:
        smoke_test()
    else:
        train(args)
