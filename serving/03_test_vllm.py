"""
10주차 Step 3b — vLLM OpenAI 호환 API 테스트

bash serving/03_run_vllm.sh 로 서버 실행 후:
    python serving/03_test_vllm.py

출력 예시:
    [chat]   "Delta 471, cleared for takeoff..."
    [stream] "KAL 018, ..."
    [모델 목록] aviation-llm
"""

from __future__ import annotations

import json
import sys
import urllib.request
from typing import Iterator

VLLM_BASE = "http://localhost:8001"
MODEL_ID   = "aviation-llm"


# ── 유틸 ─────────────────────────────────────────────────────────────

def _post(endpoint: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{VLLM_BASE}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _post_stream(endpoint: str, payload: dict) -> Iterator[str]:
    payload["stream"] = True
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{VLLM_BASE}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        for line in r:
            line = line.decode().strip()
            if line.startswith("data: ") and line != "data: [DONE]":
                chunk = json.loads(line[6:])
                delta = chunk["choices"][0]["delta"].get("content", "")
                if delta:
                    yield delta


# ── 테스트 케이스 ─────────────────────────────────────────────────────

def test_model_list() -> None:
    print("\n[1] 모델 목록 확인")
    resp = _post("/v1/models", {})  # GET 우회
    print(f"    {resp}")


def test_chat_completion() -> None:
    print("\n[2] Chat Completion (항공 이상 탐지 설명)")
    resp = _post("/v1/chat/completions", {
        "model": MODEL_ID,
        "messages": [
            {"role": "system",
             "content": "You are AviationLLM, an AI assistant for air traffic controllers. "
                        "Answer concisely in Korean, using ATC terminology."},
            {"role": "user",
             "content": "DAL471편이 예정보다 45분 지연되고 있습니다. "
                        "이상 징후를 탐지했으며, 원인 요약과 권고 조치를 알려주세요."},
        ],
        "max_tokens": 256,
        "temperature": 0.3,
    })
    answer = resp["choices"][0]["message"]["content"]
    print(f"    응답: {answer[:200]}...")


def test_streaming() -> None:
    print("\n[3] Streaming 응답 (지연 예측 설명)")
    sys.stdout.write("    스트림: ")
    sys.stdout.flush()
    tokens = []
    for tok in _post_stream("/v1/chat/completions", {
        "model": MODEL_ID,
        "messages": [
            {"role": "system",
             "content": "You are AviationLLM. Respond in Korean."},
            {"role": "user",
             "content": "KAL902편이 15분 선행 예측에서 지연 위험이 높습니다. 간단히 설명해주세요."},
        ],
        "max_tokens": 128,
        "temperature": 0.2,
    }):
        sys.stdout.write(tok)
        sys.stdout.flush()
        tokens.append(tok)
    print(f"\n    [토큰 수: {len(tokens)}]")


def test_anomaly_prompt() -> None:
    print("\n[4] 이상 탐지 RAG 스타일 프롬프트")
    resp = _post("/v1/chat/completions", {
        "model": MODEL_ID,
        "messages": [
            {"role": "system",
             "content": "당신은 항공 관제 AI 어시스턴트입니다. "
                        "주어진 컨텍스트와 수치 데이터를 기반으로 이상 탐지 결과를 설명하세요."},
            {"role": "user",
             "content": (
                 "### 컨텍스트 (FAA SOP)\n"
                 "항공기 이상 연료 소비가 탐지되면 즉시 관제사에게 보고하고 "
                 "가장 가까운 적합 공항으로의 우회를 검토해야 합니다.\n\n"
                 "### 탐지 결과\n"
                 "항공기: AAR123 | 이상 점수: -0.35 | 특이사항: prev_dep_delay=87분, "
                 "distance_miles=2450, carrier_hist_delay=22분\n\n"
                 "이 항공편의 이상 원인과 권고 조치를 100자 이내로 설명하세요."
             )},
        ],
        "max_tokens": 150,
        "temperature": 0.1,
    })
    print(f"    응답: {resp['choices'][0]['message']['content']}")


# ── 메인 ─────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 55)
    print("  SkyOps Intelligence — vLLM API 테스트")
    print(f"  서버: {VLLM_BASE}")
    print("=" * 55)

    # 서버 접속 확인
    try:
        import urllib.request as ur
        ur.urlopen(f"{VLLM_BASE}/health", timeout=5)
    except Exception:
        print(f"\n[ERROR] vLLM 서버에 연결할 수 없습니다: {VLLM_BASE}")
        print("  bash serving/03_run_vllm.sh  을 먼저 실행하세요.")
        sys.exit(1)

    try:
        test_chat_completion()
        test_streaming()
        test_anomaly_prompt()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

    print("\n✅ 모든 vLLM API 테스트 통과\n")


if __name__ == "__main__":
    main()
