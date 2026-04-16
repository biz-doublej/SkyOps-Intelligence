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
# v2.1.7 · NAS 800MB mem_limit 에서 bge-m3 (2.3GB) 를 로드하려 하면
# OOM-kill 되어 컨테이너가 재시작된다. fallback 모드에서는 아예 embedding
# 모델을 로드하지 않고 텍스트 응답만 제공.
RAG_RETRIEVE_DISABLED = os.getenv("RAG_RETRIEVE_DISABLED", "0") == "1"


# v2.1.7 · NAS 데모용 하드코딩 요약. bge-m3 2.3GB 모델 로드 없이도
# "RAG 모양" 의 응답을 주기 위해 자주 묻는 질문에 대한 출처 라벨만 삽입.
_CANNED_TOPICS = {
    "notam": (
        "NOTAM (Notice to Airmen)",
        [
            ("ICAO Annex 15 · §5.1", "운항 전 해당 비행 구간의 유효 NOTAM 를 brief 단계에서 검토."),
            ("FAA AIM 5-1-3", "Series A/D/FDC 분류 확인 후 Q-code (활주로 폐쇄·NAV 장애 등) 맥락 파악."),
            ("RKSI SOP §3.2", "출발 1시간 이내 재확인, D-NOTAM 은 관제탑 broadcast 청취."),
        ],
    ),
    "go-around": (
        "Go-Around / Missed Approach",
        [
            ("FAA AIM 5-4-22", "Thrust TO/GA, positive climb 확인 후 pitch +15°, gear up after positive rate."),
            ("ICAO PANS-OPS Vol I §6.4", "published missed approach procedure 에 따라 MAPt 까지 climb."),
            ("RKSI SOP Missed Approach", "KS-GUKSAN 3A 복행 경로, 초기 상승 고도 5000ft."),
        ],
    ),
    "windshear": (
        "Wind Shear 경보",
        [
            ("FAA AIM 7-1-26", "PIREP 확인 및 TAF/METAR WS 항목 교차 검증."),
            ("ICAO Doc 9817", "감지 시 최대 추력 TO/GA, 최대 양력 자세, gear/flap 변경 금지."),
            ("RKSI 기상 주의보", "Wind Shear Alert System (WSAS) 활성 시 관제 우선 처리."),
        ],
    ),
    "7700": (
        "비상 Squawk 7700",
        [
            ("FAA AIM 6-2-2", "7700 설정 즉시 ATC 가 레이더 우선 대응. Comm fail 시 7600, hijack 7500."),
            ("ICAO Annex 10 Vol IV", "모든 주변 항공기와 간격 유지, 비상 주파수 121.5MHz monitor."),
            ("RKSI 비상 대응 §4.1", "소방·의무 alert, 활주로 장애물 제거, 우선 착륙 vector 제공."),
        ],
    ),
    "fuel": (
        "연료 비상 선언 (Minimum Fuel / Mayday Fuel)",
        [
            ("ICAO Doc 4444 §15.1", "Minimum Fuel = 우선권 요청, Mayday Fuel = 비상 착륙 필수."),
            ("FAA AIM 5-5-15", "선언 시 즉시 최단 경로 vector + 우선 sequencing."),
            ("RKSI 연료 비상 SOP", "활주로 14/32 기준 최단 접근, 소방차 대기."),
        ],
    ),
    "ils": (
        "ILS 접근 간격 기준",
        [
            ("FAA JO 7110.65 §5-5-4", "Heavy 후속 Small 5 NM, Heavy 후속 Heavy 4 NM."),
            ("ICAO Doc 4444 §8.7.3.2", "RECAT-EU 범주 기반 간격 적용."),
            ("RKSI Approach SOP", "ILS 15R final 최소 3 NM, 쌍방향 접근 시 4 NM."),
        ],
    ),
    "emergency": (
        "비상 착륙 관제 절차",
        [
            ("FAA AIM 6-1-2", "비상 선언 즉시 상세 확인: 기체 상태·연료·승객수."),
            ("ICAO Annex 11 §3.4", "주변 트래픽 우선 분리, 소방·의무·지상 준비 alert."),
            ("RKSI 비상 §2", "CAT-II ILS 우선, runway excursion 대응 ARFF 배치."),
        ],
    ),
}


def _lookup_canned(question: str) -> tuple[str | None, list[dict]]:
    q = question.lower()
    for key, (topic, refs) in _CANNED_TOPICS.items():
        if key in q:
            sources = [{"section": f"{ref[0]}", "text": ref[1], "source": ref[0].split(" ")[0]} for ref in refs]
            return topic, sources
    return None, []


def _fallback_answer(question: str, sources: list[dict]) -> str:
    """RAG retrieval 결과를 템플릿으로 요약 (LLM 없이, NAS 모드)."""
    # 1) ChromaDB retrieve 결과가 있으면 그걸 요약
    if sources:
        head = "[LLM fallback mode — 관련 규정 요약만 제공]\n\n"
        lines = []
        for i, s in enumerate(sources[:3], 1):
            section = s.get("section", "관련 문서")
            excerpt = (s.get("text") or "")[:300].strip()
            lines.append(f"[{i}] {section}\n{excerpt}\n")
        return head + "\n".join(lines) + "\n※ 정확한 대응 절차는 관제사/담당자와 협의 후 결정하십시오."

    # 2) retrieve 실패했지만 canned topic 매칭되면 하드코딩 요약
    topic, canned = _lookup_canned(question)
    if topic and canned:
        head = f"[LLM fallback mode — {topic} 관련 규정 요약]\n\n"
        lines = []
        for i, s in enumerate(canned, 1):
            lines.append(f"[{i}] {s['section']}\n{s['text']}\n")
        return head + "\n".join(lines) + "\n※ 정확한 대응 절차는 관제사/담당자와 협의 후 결정하십시오."

    # 3) 그 외 → 일반 안내
    return ("[LLM fallback mode] 현재 vLLM 서버가 연결되지 않아 자동 응답을 생성하지 못합니다. "
            f"질문: \"{question}\". 관련 문서를 찾지 못했습니다. "
            "AI 어시스턴트 전체 기능은 GPU 환경에서 활성화됩니다.")


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
                # v2.1.7 · NAS 메모리 800MB 에서는 bge-m3 (2.3GB) 를 로드하면
                # OOM-kill 당해 컨테이너가 재시작된다. RAG_RETRIEVE_DISABLED=1 이면
                # 아예 sentence-transformers 를 touch 하지 않고 canned topic 만 응답.
                sources: list[dict] = []
                if not RAG_RETRIEVE_DISABLED:
                    try:
                        with tracer.start_as_current_span("rag_retrieve_only"):
                            chain = ModelStore.rag()
                            result = chain.retrieve_only(req.question) \
                                if hasattr(chain, "retrieve_only") else chain.query(req.question)
                        sources = result.get("sources", [])
                    except Exception as e:
                        print(f"⚠️  RAG retrieve 실패 → canned fallback: {e}")
                else:
                    # canned source labels 도 사용자에게 "참조 문서" 섹션에 표시
                    _, sources = _lookup_canned(req.question)
                return ChatResponse(
                    answer=_fallback_answer(req.question, [] if RAG_RETRIEVE_DISABLED else sources),
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
