---
marp: true
theme: default
paginate: true
size: 16:9
---

# SkyOps Intelligence
## 중간발표 2: LLM 파인튜닝과 운영 질의응답 고도화

- 발표일: 2026-04-01
- 범위: Week 7 데이터셋 구축 + Week 8 QLoRA 학습 준비

---

# 1. 이번 발표 목표

- 기존 스트리밍/이상 탐지 플랫폼 위에 항공 운영용 LLM 계층을 추가합니다.
- 정형 이벤트를 자연어 설명으로 바꾸고, 운영자가 바로 활용할 수 있는 응답 모델을 학습하는 것이 목표입니다.
- 이번 발표는 데이터셋 구축 결과, QLoRA 학습 설계, 실제 실행 조건을 중심으로 설명합니다.

---

# 2. Week 7 결과물

- ICAO 문서 파싱, GPT-4 QA 생성, 이상 탐지 자연어 생성, 승객 안내문 생성 파이프라인을 구성했습니다.
- 최종 산출물은 Alpaca 포맷 JSONL train/val/test 세트입니다.
- 현재 빌드 시점 기준 데이터는 `15,000건`입니다.

```text
anomaly_nl         10,000
passenger_ann       5,000
-------------------------
total              15,000
```

---

# 3. 데이터셋 포맷

- 모든 샘플은 `instruction`, `input`, `output` 구조로 통일했습니다.
- 이 형식은 SFT 데이터셋으로 바로 변환하기 쉽고, 프롬프트-응답 경계를 명확하게 유지할 수 있습니다.
- 학습 시에는 이를 chat prompt/completion 형식으로 변환해 Llama Instruct 템플릿에 맞춥니다.

```json
{
  "instruction": "아래 이상 탐지 데이터의 의미와 권고 조치를 설명하세요.",
  "input": "{\"callsign\": \"WN542\", ...}",
  "output": "[주의] 속도 이상 — WN542: 87.4kt/81초 변화..."
}
```

---

# 4. 왜 QLoRA 인가

- 8B급 Instruct 모델을 전체 파인튜닝하면 메모리 비용이 너무 큽니다.
- QLoRA는 base model을 4-bit로 양자화하고, LoRA adapter만 학습해 비용을 줄입니다.
- 즉, 제한된 GPU 메모리에서도 실험 반복이 가능하고 checkpoint 관리도 단순합니다.

---

# 5. 베이스 모델 선정

- 목표 모델: `meta-llama/Llama-3.1-8B-Instruct`
- 이유:
  - 범용 instruct 성능이 안정적입니다.
  - 항공 운영 QA, 설명 생성, 안내문 생성까지 한 모델로 커버하기 좋습니다.
  - Hugging Face + TRL + PEFT 조합으로 바로 학습 파이프라인을 구성할 수 있습니다.

---

# 6. 학습 설정 확정

- Quantization
  - `load_in_4bit=True`
  - `bnb_4bit_quant_type="nf4"`
  - `bnb_4bit_use_double_quant=True`
- LoRA
  - `r=64`
  - `alpha=16`
  - `dropout=0.05`
  - `target_modules=["q_proj", "v_proj"]`
- Trainer
  - `TRL SFTTrainer`
  - prompt/completion dataset
  - completion-only loss

---

# 7. 학습 스크립트 구조

- 새 스크립트: `llm_data/fine_tune_qlora.py`
- 기능:
  - 환경 preflight 체크
  - Alpaca JSONL -> conversational prompt/completion 변환
  - NF4 + LoRA 모델 로드
  - TRL SFTTrainer 학습
  - W&B 로깅
  - 체크포인트 3개 유지

---

# 8. 실험 추적과 체크포인트

- W&B 사용 시 loss curve, eval loss, step별 로그를 자동 전송합니다.
- 체크포인트는 전체 step 기준 약 1/3 간격으로 저장합니다.
- `save_total_limit=3`로 설정해 최신 3개만 유지합니다.
- 최종 산출물은 `final_adapter/` 디렉터리에 별도로 저장합니다.

---

# 9. 실제 실행 환경 점검 결과

- 확인 시점: `2026-04-01`
- 실제 GPU: `RTX 3070 8GB`
- 현재 `llm_venv`의 Torch: `2.11.0+cu126`
- `.env` 기준 HF/W&B 토큰은 아직 비어 있습니다.

의미:

- CUDA 학습 환경 자체는 준비 완료
- Meta Llama 접근을 위한 HF_TOKEN 설정이 남아 있음
- W&B는 키가 없으면 비활성화되지만 학습 자체는 가능

---

# 10. 리스크와 대응

- 리스크 1: 8GB VRAM
  - 대응: `max_length=512`, `batch_size=1`, gradient accumulation 16
- 리스크 2: gated model 접근
  - 대응: `HF_TOKEN` 또는 `huggingface-cli login`
- 리스크 3: 실험 관리 누락
  - 대응: W&B 기본 연동 + `training_summary.json` 저장

---

# 11. 기대 산출물

- 운영 질의응답용 LLM adapter
- 이상 탐지 설명 생성 품질 향상
- 승객 안내문 생성 품질 향상
- 이후 단계에서 RAG 또는 실시간 이벤트 컨텍스트 결합 기반이 되는 SFT 모델 확보

---

# 12. 이번 주 기준 완료 사항

- Alpaca 데이터셋 빌드 완료
- `fine_tune_qlora.py` 추가 완료
- `requirements_train.txt` 추가 완료
- CUDA Torch + 학습 패키지 설치 완료
- 공개 모델 1-step smoke test 완료
- QLoRA 실행 runbook 문서화 완료
- 발표 자료 및 발표 노트 갱신 완료

---

# 13. 남은 실행 항목

1. `.env`에 `HF_TOKEN` 설정
2. 필요 시 `WANDB_API_KEY` 설정
3. `python llm_data/fine_tune_qlora.py --preflight-only`
4. `python llm_data/fine_tune_qlora.py`

---

# 14. 결론

- Week 7에서는 학습용 항공 운영 데이터셋을 완성했습니다.
- Week 8에서는 Llama 3.1 8B QLoRA 학습 파이프라인을 코드 수준에서 준비했습니다.
- 남은 것은 실행 환경 정리와 장시간 학습 수행입니다.

---

# Q&A

- 감사합니다.
- 질문 부탁드립니다.
