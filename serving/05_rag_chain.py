"""
10주차 Step 5 — LangChain RAG 체인

ChromaDB + AviationLLM(vLLM OpenAI 호환 API)를 연결하는
RAG (Retrieval-Augmented Generation) 체인 모듈입니다.

FastAPI(api.py)에서 import 하여 사용합니다.
단독 테스트:
    python serving/05_rag_chain.py

요구사항:
    pip install langchain-openai langchain-community chromadb sentence-transformers
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent

# ── 설정 ─────────────────────────────────────────────────────────────
VECTORDB_DIR  = str(PROJECT_ROOT / "data/vectordb")
COLLECTION    = "aviation_rag"
EMBED_MODEL   = "BAAI/bge-m3"
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
LLM_MODEL_ID  = os.getenv("LLM_MODEL_ID",  "aviation-llm")

# RAG 파라미터
TOP_K         = 4     # 검색 문서 수
MAX_TOKENS    = 512
TEMPERATURE   = 0.2


SYSTEM_PROMPT = """당신은 AviationLLM — 대한민국 항공 관제사를 돕는 AI 어시스턴트입니다.

[핵심 규칙]
1. 반드시 한국어로만 답변하세요. 절대 영어, 중국어 등 다른 언어를 사용하지 마세요.
2. ATC 전문 용어(예: Squawk, Go-Around, NOTAM, FL)는 원어 그대로 사용하되, 설명은 한국어로 하세요.
3. 아래 참조 문서를 기반으로 정확하고 간결하게 답변하세요.
4. 참조 문서에 없는 내용은 일반 항공 지식으로 보완하되, 불확실한 경우 "확인이 필요합니다"라고 명시하세요.
5. 답변 형식: 핵심 내용 먼저, 부가 설명은 뒤에. 불필요한 인사말 없이 바로 본론으로."""


# ── RAG 체인 클래스 ───────────────────────────────────────────────────

class AviationRAGChain:
    """ChromaDB + vLLM 기반 항공 도메인 RAG 체인 (LCEL 기반)"""

    def __init__(self) -> None:
        self._vectorstore  = None
        self._llm          = None
        self._retriever    = None
        self._initialized  = False

    # ── 지연 초기화 ──────────────────────────────────────────────────
    def _init(self) -> None:
        if self._initialized:
            return

        from langchain_openai import ChatOpenAI
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import HuggingFaceEmbeddings

        # 1. 임베딩 모델 (로컬)
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # 2. ChromaDB 벡터스토어
        self._vectorstore = Chroma(
            collection_name=COLLECTION,
            embedding_function=embeddings,
            persist_directory=VECTORDB_DIR,
        )

        # 3. Retriever
        self._retriever = self._vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOP_K},
        )

        # 4. vLLM OpenAI 호환 LLM
        self._llm = ChatOpenAI(
            openai_api_base=VLLM_BASE_URL,
            openai_api_key="dummy",
            model_name=LLM_MODEL_ID,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            streaming=False,
        )

        self._initialized = True

    # ── 퍼블릭 API ───────────────────────────────────────────────────

    def query(self, question: str) -> dict[str, Any]:
        """질문에 대한 RAG 응답 반환."""
        self._init()
        t0 = time.time()

        # 1. 문서 검색
        docs = self._retriever.invoke(question)

        # 2. 컨텍스트 구성
        context_parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.metadata
            context_parts.append(
                f"[{i}] [{meta.get('source','')}] {meta.get('section','')}\n"
                f"{doc.page_content}"
            )
        context = "\n\n".join(context_parts)

        # 3. LLM 호출
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"### 참조 문서\n{context}\n\n### 질문\n{question}"},
        ]
        response = self._llm.invoke(messages)
        answer = response.content

        latency = (time.time() - t0) * 1000

        # 4. 소스 정보
        sources = []
        for doc in docs:
            sources.append({
                "source":  doc.metadata.get("source", ""),
                "section": doc.metadata.get("section", ""),
                "domain":  doc.metadata.get("domain", ""),
                "text":    doc.page_content[:200],
            })

        return {
            "answer":     answer,
            "sources":    sources,
            "latency_ms": round(latency, 1),
        }

    def retrieve_context(self, query: str, k: int = TOP_K) -> str:
        """검색된 문서들을 단일 컨텍스트 문자열로 반환."""
        self._init()
        docs = self._vectorstore.similarity_search(query, k=k)
        parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.metadata
            parts.append(
                f"[{i}] [{meta.get('source','')}] {meta.get('section','')}\n"
                f"{doc.page_content}"
            )
        return "\n\n".join(parts)

    @property
    def vectorstore(self):
        self._init()
        return self._vectorstore


# ── 싱글톤 인스턴스 (FastAPI에서 import 하여 사용) ─────────────────────
rag_chain = AviationRAGChain()


# ── 단독 테스트 ───────────────────────────────────────────────────────

def _test_rag() -> None:
    print("=" * 55)
    print("  AviationRAGChain — 단독 테스트")
    print("=" * 55)

    questions = [
        "항공기 이상 연료 소비 시 관제사는 어떻게 대응해야 하나요?",
        "15분 이상 지연된 항공편에 대한 절차를 설명해주세요.",
        "비상 선언 항공기에 우선 처리를 부여하는 절차는?",
    ]

    for q in questions:
        print(f"\n질문: {q}")
        try:
            result = rag_chain.query(q)
            print(f"응답: {result['answer'][:200]}...")
            print(f"지연: {result['latency_ms']}ms | 참조 문서: {len(result['sources'])}건")
            for s in result["sources"][:2]:
                print(f"  - [{s['source']}] {s['section'][:50]}")
        except Exception as e:
            print(f"[ERROR] {e}")
            print("  vLLM 서버가 실행 중인지 확인하세요: bash serving/03_run_vllm.sh")
            break


if __name__ == "__main__":
    _test_rag()
