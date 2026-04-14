"""Korean output cleaning for LLM responses.

ADR-001 Migration Phase 1 — extracted from serving/api.py (2026-04-14 P3).

Qwen2.5의 중국어 code-switching 문제를 완화하기 위해 한국어 문장만 추출.
"""

from __future__ import annotations

import re as _re


def clean_korean(text: str) -> str:
    """중국어/영어 문장이 섞인 응답에서 한국어 문장만 추출.

    - CJK Unified (0x4E00-0x9FFF) 중국어 글자가 30% 이상인 줄은 제거.
    - 줄 앞부분에 한국어가 있으면 그 부분만 살림.
    - 문장이 미완성으로 잘린 경우 마지막 완성 문장까지만 반환.
    """
    if not text:
        return text

    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        chars = [
            c for c in stripped
            if not c.isspace() and not c.isdigit()
            and c not in ".,;:!?()-/·•[]{}\"'"
        ]
        if not chars:
            cleaned.append(stripped)
            continue
        chinese_count = sum(1 for c in chars if "\u4e00" <= c <= "\u9fff")
        total = len(chars)
        if total > 0 and chinese_count / total > 0.3:
            # 줄 앞부분에 한국어가 있으면 그 부분만 살리기
            parts = _re.split(r"[\u4e00-\u9fff]{3,}", stripped)
            if parts and parts[0].strip():
                kr_part = parts[0].strip().rstrip(".,;:!? ")
                if kr_part and any("\uac00" <= c <= "\ud7a3" for c in kr_part):
                    cleaned.append(kr_part)
            continue
        cleaned.append(stripped)

    result = "\n".join(cleaned).strip()
    # 끝이 이상하게 잘린 경우 마지막 완성 문장까지만
    if result and result[-1] not in ".!?。다요":
        last_period = max(
            result.rfind("."),
            result.rfind("다."),
            result.rfind("요."),
            result.rfind("세요."),
        )
        if last_period > len(result) * 0.3:
            result = result[:last_period + 1]
    return result if result else text
