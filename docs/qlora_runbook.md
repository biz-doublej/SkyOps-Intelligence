# Week 8 QLoRA Runbook

## 1. 목적

- `data/alpaca/aviation_alpaca_train.jsonl`와 `data/alpaca/aviation_alpaca_val.jsonl`로 `meta-llama/Llama-3.1-8B-Instruct`를 QLoRA 방식으로 미세조정합니다.
- 양자화는 4-bit NF4, 어댑터는 LoRA `r=64`, `alpha=16`, `target_modules=q_proj,v_proj`로 고정했습니다.
- 실험 추적은 W&B, 체크포인트는 최대 3개 유지하도록 설정했습니다.

## 2. 현재 환경 기준 확인 사항

- 현재 머신 확인 시점: `2026-04-01`
- GPU: `NVIDIA GeForce RTX 3070 8GB`
- 현재 `llm_venv`의 Torch: `2.11.0+cu126`
- 학습 패키지 설치 완료: `transformers`, `datasets`, `accelerate`, `peft`, `trl`, `bitsandbytes`, `wandb`
- 현재 남은 주요 블로커는 `HF_TOKEN`과 선택적 `WANDB_API_KEY`입니다.

## 3. 설치 순서

1. CUDA 지원 PyTorch 설치
   공식 가이드: https://pytorch.org/get-started/locally/
2. 학습 패키지 설치
   `pip install -r llm_data/requirements_train.txt`
3. `.env`에 아래 값 설정
   `HF_TOKEN=...`
   `WANDB_API_KEY=...`
   `WANDB_PROJECT=skyops-qlora`

## 4. 사전 점검

```powershell
python llm_data/fine_tune_qlora.py --preflight-only
```

정상 기준:

- train/val JSONL 존재
- `torch.cuda.is_available() == True`
- `datasets`, `transformers`, `peft`, `trl`, `bitsandbytes`, `accelerate` import 가능
- HF gated model 접근 가능

## 5. 학습 실행

기본 실행:

```powershell
python llm_data/fine_tune_qlora.py
```

출력 디렉터리 지정:

```powershell
python llm_data/fine_tune_qlora.py --output-dir data/models/llm/llama31_8b_run1
```

재개:

```powershell
python llm_data/fine_tune_qlora.py --resume-from-checkpoint data/models/llm/llama31_8b_run1/checkpoint-XXX
```

## 6. 기본 하이퍼파라미터

- Model: `meta-llama/Llama-3.1-8B-Instruct`
- Quantization: `load_in_4bit=True`, `bnb_4bit_quant_type="nf4"`
- Compute dtype: GPU가 BF16 지원 시 `bfloat16`, 아니면 `float16`
- LoRA: `r=64`, `alpha=16`, `dropout=0.05`
- Targets: `q_proj`, `v_proj`
- Epochs: `2.0`
- Train batch size: `1`
- Gradient accumulation: `16`
- Max length: `512`
- Optimizer: `paged_adamw_8bit`
- Save policy: 총 step 기준 약 1/3마다 저장, 최근 3개 유지

## 7. 산출물

- `data/models/llm/<run>/checkpoint-*`
- `data/models/llm/<run>/final_adapter/`
- `data/models/llm/<run>/training_summary.json`
- `data/models/llm/<run>/train_results.json`
- `data/models/llm/<run>/eval_results.json`

## 8. 현재 블로커

- `.env`에서 `HF_TOKEN`, `WANDB_API_KEY`가 아직 확인되지 않았습니다.
- 사용자 계획에 적힌 `RTX 3090`과 달리, 실제 확인된 GPU는 `RTX 3070 8GB`입니다.
- 이 VRAM에서는 8B QLoRA가 매우 타이트하므로 `max_length=512`, `batch=1` 이하 전제를 유지해야 합니다.
- 공개 모델 `Qwen/Qwen2-0.5B-Instruct` 기준 1-step smoke test는 성공했습니다.
