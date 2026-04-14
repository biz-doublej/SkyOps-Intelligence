"""Notification / announcement router — /generate/announcement.

ADR-001 Migration Phase 1 (2026-04-14 P3).
"""

from __future__ import annotations

import json
import time
import urllib.request as ur

from fastapi import APIRouter, HTTPException

from common.constants import LLM_MODEL_ID, VLLM_BASE_URL
from common.korean import clean_korean
from common.models import AnnouncementRequest
from common.telemetry import get_tracer

router = APIRouter(tags=["notification"])
tracer = get_tracer("notification")


@router.post("/generate/announcement")
def generate_announcement(req: AnnouncementRequest):
    """승객 안내문 자동 생성."""
    DELAY_LABELS = {
        "weather": "기상 악화",
        "maintenance": "기체 정비",
        "mechanical": "기체 정비",
        "traffic": "항공 교통 혼잡",
        "atc": "항공 교통 관제 사유",
        "crew": "승무원 사유",
        "other": "운항 사정",
    }
    reason = DELAY_LABELS.get(req.delay_type, req.delay_type)

    SYSTEM = (
        "당신은 대한민국 항공사의 승객 안내방송 작성 전문 AI입니다.\n"
        "규칙:\n"
        "- 한국어 안내문만 작성하세요. 중국어 사용 금지.\n"
        "- 정중하고 전문적인 어조를 사용하세요.\n"
        "- '승객 여러분'으로 시작하세요.\n"
        "- 3~4문장으로 간결하게 작성하세요.\n"
        "- 안전과 양해 감사 표현을 포함하세요."
    )
    user_msg = (
        f"항공편명: {req.flight_number}\n"
        f"지연 사유: {reason}\n"
        f"예상 지연 시간: 약 {req.delay_minutes}분\n"
        f"추가 정보: {req.details or '없음'}"
    )

    t0 = time.time()
    with tracer.start_as_current_span("generate_announcement") as span:
        span.set_attribute("flight_number", req.flight_number)
        span.set_attribute("delay_type", req.delay_type)
        span.set_attribute("delay_minutes", req.delay_minutes)

        payload = {
            "model": LLM_MODEL_ID,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": 500,
            "temperature": 0.3,
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
    return {"announcement": answer, "latency_ms": round((time.time() - t0) * 1000, 1)}
