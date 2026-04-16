"""RAG + LLM explanation router — /chat, /explain/anomaly.

ADR-001 Migration Phase 1 (2026-04-14 P3).
P8-C (2026-04-15): LLM_MODE=fallback for NAS deployment (no vLLM).
"""

from __future__ import annotations

import json
import os
import time
import urllib.request as ur

from fastapi import APIRouter, HTTPException

from common.constants import LLM_MODEL_ID, VLLM_BASE_URL
from common.korean import clean_korean
from common.model_store import ModelStore
from common.models import (
    AnomalyExplainRequest,
    ChatRequest,
    ChatResponse,
)
from common.telemetry import get_tracer

router = APIRouter(tags=["llm"])
tracer = get_tracer("rag")

# P8-C: NAS mode — RAG retrieve만, LLM 호출 생략
LLM_MODE = os.getenv("LLM_MODE", "vllm")  # "vllm" | "fallback"


def _fallback_answer(question: str, sources: list[dict]) -> str:
    """RAG retrieval 결과를 템플릿으로 요약 (LLM 없이, NAS 모드)."""
    if not sources:
        return ("[LLM fallback mode] 현재 vLLM 서버가 연결되지 않아 자동 응답을 생성하지 못합니다. "
                f"질문: \"{question}\". 관련 문서를 찾지 못했습니다. "
                "AI 어시스턴트 전체 기능은 GPU 환경에서 활성화됩니다.")
    head = "[LLM fallback mode — 관련 규정 요약만 제공]\n\n"
    lines = []
    for i, s in enumerate(sources[:3], 1):
        section = s.get("section", "관련 문서")
        excerpt = (s.get("text") or "")[:300].strip()
        lines.append(f"[{i}] {section}\n{excerpt}\n")
    return head + "\n".join(lines) + "\n※ 정확한 대응 절차는 관제사/담당자와 협의 후 결정하십시오."


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """AviationLLM + ChromaDB RAG 어시스턴트."""
    t0 = time.time()
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute("use_rag", req.use_rag)
        span.set_attribute("question_length", len(req.question))

        if req.use_rag:
            # P8-C: fallback mode — skip LLM call, return retrieval summary
            if LLM_MODE == "fallback":
                # v2.1.6 · RAG retrieve 실패해도 500 대신 empty-source fallback 으로 degrade.
                # 발표 시연 중에 ChromaDB 인덱스 문제·임베딩 모델 다운로드 실패 등이
                # 나도 사용자에게 보이는 건 완전히 죽은 500 이 아니라 "문서 못 찾음" 메시지.
                sources: list[dict] = []
                try:
                    with tracer.start_as_current_span("rag_retrieve_only"):
                        chain = ModelStore.rag()
                        result = chain.retrieve_only(req.question) \
                            if hasattr(chain, "retrieve_only") else chain.query(req.question)
                    sources = result.get("sources", [])
                except Exception as e:
                    print(f"⚠️  RAG retrieve 실패 → empty-source fallback: {e}")
                return ChatResponse(
                    answer=_fallback_answer(req.question, sources),
                    sources=sources,
                    latency_ms=round((time.time() - t0) * 1000, 1),
                    rag_used=bool(sources),
                )

            try:
                with tracer.start_as_current_span("rag_chain_query"):
                    chain = ModelStore.rag()
                    result = chain.query(req.question)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"RAG 응답 오류: {e}")

            return ChatResponse(
                answer=clean_korean(result["answer"]),
                sources=result["sources"],
                latency_ms=result["latency_ms"],
                rag_used=True,
            )

        # P8-C: fallback mode without RAG → terse template response
        if LLM_MODE == "fallback":
            return ChatResponse(
                answer=_fallback_answer(req.question, []),
                sources=[],
                latency_ms=round((time.time() - t0) * 1000, 1),
                rag_used=False,
            )

        # 직접 vLLM 호출 (RAG 없이)
        SYSTEM = (
            "당신은 AviationLLM — 대한민국 항공 관제사를 돕는 AI 어시스턴트입니다. "
            "반드시 한국어로만 답변하세요. 절대 영어, 중국어 등 다른 언어를 사용하지 마세요. "
            "ATC 전문 용어(Squawk, Go-Around, NOTAM, FL 등)는 원어 그대로 사용하되 설명은 한국어로 하세요. "
            "불필요한 인사말 없이 바로 본론으로 답변하세요."
        )
        payload = {
            "model": LLM_MODEL_ID,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": req.question},
            ],
            "max_tokens": req.max_tokens,
            "temperature": 0.2,
        }
        data = json.dumps(payload).encode()
        request = ur.Request(
            f"{VLLM_BASE_URL}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with tracer.start_as_current_span("vllm_direct"):
                with ur.urlopen(request, timeout=120) as r:
                    resp = json.loads(r.read())
            answer = resp["choices"][0]["message"]["content"]
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"vLLM 호출 실패: {e}")

        latency = (time.time() - t0) * 1000
        return ChatResponse(
            answer=clean_korean(answer),
            sources=[],
            latency_ms=round(latency, 1),
            rag_used=False,
        )


@router.post("/explain/anomaly")
def explain_anomaly(req: AnomalyExplainRequest):
    """이상 탐지 이벤트를 LLM으로 자동 설명 생성."""
    TYPE_KR = {
        "ALTITUDE_SPIKE": "고도 급변",
        "VELOCITY_SPIKE": "속도 이상",
        "PATH_DEVIATION": "경로 이탈",
    }
    SEV_KR = {"LOW": "낮음", "MEDIUM": "중간", "HIGH": "높음", "CRITICAL": "심각"}

    SYSTEM = (
        "당신은 대한민국 항공 관제사를 돕는 전문 AI입니다.\n"
        "규칙:\n"
        "- 반드시 한국어로만 답변하세요. 중국어 절대 금지. 영어도 금지.\n"
        "- 항공 약어(ICAO, AIM, FL 등)만 영문 허용. 나머지는 모두 한국어.\n"
        "- 형식: 1) 상황 요약 2) 원인 분석 3) 권고 대응 절차\n"
        "- 반드시 3문장 이내로 간결하게 답변을 마치세요."
    )
    callsign = req.callsign or req.icao24
    user_msg = (
        f"아래 이상 탐지 결과를 관제사에게 한국어로 설명해 주세요.\n\n"
        f"항공편: {callsign}\n"
        f"이상 유형: {TYPE_KR.get(req.anomaly_type, req.anomaly_type)}\n"
        f"심각도: {SEV_KR.get(req.severity, req.severity)}\n"
        f"상세: {json.dumps(req.details, ensure_ascii=False)}\n"
        f"고도: {req.altitude_m}미터, 속도: {req.velocity_m_s}미터/초"
    )

    t0 = time.time()
    with tracer.start_as_current_span("explain_anomaly") as span:
        span.set_attribute("anomaly_type", req.anomaly_type)
        span.set_attribute("severity", req.severity)

        # P8-C / v2.1.6 · NAS 모드: vLLM 없이도 템플릿 기반 설명 생성
        if LLM_MODE == "fallback" or not VLLM_BASE_URL:
            tmpl = (
                f"[LLM fallback mode] {callsign} 에서 "
                f"{TYPE_KR.get(req.anomaly_type, req.anomaly_type)}이 감지되었습니다.\n"
                f"심각도: {SEV_KR.get(req.severity, req.severity)}.\n"
            )
            if req.anomaly_type.upper() == "ALTITUDE_SPIKE":
                tmpl += (
                    "권고: ATC 와 고도 확인 후 원 할당 FL 로 복귀하거나 긴급 하강 사유 확인. "
                    "기계적 이상 가능성이 있을 경우 가까운 공항 비상 착륙 옵션 검토."
                )
            elif req.anomaly_type.upper() == "VELOCITY_SPIKE":
                tmpl += (
                    "권고: 속도 초과/부족 확인, 와류/윈드시어 가능성 체크. "
                    "필요 시 관제사 간 교신으로 주변 항공기 간격 조정."
                )
            elif req.anomaly_type.upper() == "PATH_DEVIATION":
                tmpl += (
                    "권고: Heading 재지시, 충돌 회피 확인, NOTAM/제한 공역 위반 여부 점검. "
                    "RNAV 장비 상태 확인 요청."
                )
            else:
                tmpl += "권고: 관련 SOP 및 FAA AIM·ICAO Annex 절차를 참고해 주십시오."
            return {
                "explanation": tmpl,
                "latency_ms": round((time.time() - t0) * 1000, 1),
                "mode": "fallback",
            }

        payload = {
            "model": LLM_MODEL_ID,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": 200,
            "temperature": 0.2,
        }
        data = json.dumps(payload).encode()
        request = ur.Request(
            f"{VLLM_BASE_URL}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with ur.urlopen(request, timeout=120) as r:
                resp = json.loads(r.read())
            answer = resp["choices"][0]["message"]["content"]
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"vLLM 호출 실패: {e}")

    answer = clean_korean(answer)
    return {"explanation": answer, "latency_ms": round((time.time() - t0) * 1000, 1)}
