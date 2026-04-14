"""
SkyOps Intelligence — RAGAs Benchmark (P2 · 2026-04-14)
========================================================
Strategic Review 7번 병목 — grounded RAG evaluation

RAGAs 0.4.x 기반 RAG 품질 평가. judge LLM으로 로컬 vLLM(Qwen2.5-7B)을
시도하고, 실패 시 proxy metric으로 fallback. vLLM 서버 미실행 환경에서도
proxy mode로는 돌아간다.

실행:
    python evaluation/ragas_bench.py --n 20 --judge vllm
    python evaluation/ragas_bench.py --n 20 --judge proxy

입력:
    data/eval/benchmark_eval.jsonl (500 records; stratified by type)

출력:
    data/eval/ragas_results.json
    data/eval/ragas_results.md
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
EVAL_DIR = DATA_DIR / "eval"
BENCHMARK_PATH = EVAL_DIR / "benchmark_eval.jsonl"
VECTORDB_PATH = DATA_DIR / "vectordb"

RESULTS_JSON = EVAL_DIR / "ragas_results.json"
RESULTS_MD = EVAL_DIR / "ragas_results.md"

# vLLM OpenAI-compatible endpoint
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "aviation-llm")
EMBED_MODEL = "BAAI/bge-m3"


# ──────────────────────────────────────────────────────────────────────
# Dataset loading (stratified sampling)
# ──────────────────────────────────────────────────────────────────────

def load_benchmark(n: int, seed: int = 42) -> list[dict]:
    """Load benchmark_eval.jsonl, sample n items stratified by type."""
    if not BENCHMARK_PATH.exists():
        print(f"❌ Benchmark 파일 없음: {BENCHMARK_PATH}")
        sys.exit(1)

    records = []
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"✅ Benchmark 로드: {len(records):,} records")

    # Stratified sampling
    rnd = random.Random(seed)
    by_type: dict[str, list] = {}
    for r in records:
        by_type.setdefault(r.get("type", "unknown"), []).append(r)

    n_per_type = max(1, n // len(by_type))
    sampled = []
    for t, items in by_type.items():
        rnd.shuffle(items)
        sampled.extend(items[:n_per_type])
    rnd.shuffle(sampled)
    sampled = sampled[:n]

    # Cast to {question, ground_truth} schema — RAGAs input
    for r in sampled:
        # Combine instruction + input as question
        q = r["instruction"]
        if r.get("input"):
            q += "\n\n컨텍스트: " + r["input"]
        r["_question"] = q
        r["_ground_truth"] = r["reference"]
    print(f"   Stratified sample (n={len(sampled)}): {[(t, sum(1 for s in sampled if s['type']==t)) for t in by_type]}")
    return sampled


# ──────────────────────────────────────────────────────────────────────
# ChromaDB retriever (standalone, no LangChain to avoid dep hell)
# ──────────────────────────────────────────────────────────────────────

def build_retriever(k: int = 4):
    """ChromaDB retriever using BAAI/bge-m3 embeddings."""
    try:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"❌ {e} — chromadb/sentence-transformers 필요")
        sys.exit(1)

    if not VECTORDB_PATH.exists():
        print(f"❌ ChromaDB 없음: {VECTORDB_PATH}")
        print("   먼저 실행: python serving/04_build_vectordb.py")
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(VECTORDB_PATH))
    collections = client.list_collections()
    if not collections:
        print("❌ ChromaDB에 collection 없음")
        sys.exit(1)
    col = collections[0]
    print(f"✅ ChromaDB collection: {col.name} ({col.count()} docs)")

    print(f"📥 Embedding 모델 로드: {EMBED_MODEL}...")
    embedder = SentenceTransformer(EMBED_MODEL)

    def retrieve(query: str) -> list[str]:
        q_emb = embedder.encode([query]).tolist()
        result = col.query(query_embeddings=q_emb, n_results=k)
        docs = result.get("documents", [[]])[0]
        return docs

    return retrieve


# ──────────────────────────────────────────────────────────────────────
# LLM answer generation (vLLM 또는 fallback)
# ──────────────────────────────────────────────────────────────────────

def generate_answer(question: str, contexts: list[str], use_vllm: bool = True) -> str:
    """Generate answer using vLLM or fallback to retrieval concatenation."""
    context_text = "\n\n".join([f"[문서 {i+1}]\n{c}" for i, c in enumerate(contexts)])
    prompt = (
        "당신은 항공 관제 도메인 전문가입니다. 아래 참고 문서를 근거로 질문에 답하세요.\n\n"
        f"=== 참고 문서 ===\n{context_text}\n\n"
        f"=== 질문 ===\n{question}\n\n"
        "=== 답변 (간결하고 정확하게) ==="
    )

    if use_vllm:
        try:
            import urllib.request as ur
            payload = {
                "model": LLM_MODEL_ID,
                "messages": [
                    {"role": "system", "content": "항공 관제 전문가로서 주어진 문서만을 근거로 답변합니다."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 400,
                "temperature": 0.2,
            }
            data = json.dumps(payload).encode("utf-8")
            req = ur.Request(
                f"{VLLM_BASE_URL}/chat/completions",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with ur.urlopen(req, timeout=60) as r:
                resp = json.loads(r.read())
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"   ⚠️  vLLM 호출 실패 ({e}) — fallback")
            use_vllm = False

    # Fallback: 첫 2개 문서의 요약을 이어붙임 (degenerate answer)
    if contexts:
        return contexts[0][:400] + ("..." if len(contexts[0]) > 400 else "")
    return "(문서를 찾을 수 없습니다.)"


# ──────────────────────────────────────────────────────────────────────
# Proxy metrics (Judge LLM 불가 시)
# ──────────────────────────────────────────────────────────────────────

def proxy_metrics(row: dict) -> dict[str, float]:
    """Heuristic proxy metrics when RAGAs judge unavailable.

    context_hit_rate: ground_truth 키워드 중 검색 문서에 포함된 비율
    answer_rouge_l:   generated vs ground_truth ROUGE-L F1
    answer_length_ratio: sigmoid-style score, 80~500 chars가 이상적
    retrieval_coverage:  len(contexts) / expected (4)
    """
    from rouge_score import rouge_scorer

    gt = row["_ground_truth"]
    answer = row["_answer"]
    contexts = row["_contexts"]

    # ROUGE-L
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
    rouge = scorer.score(gt, answer)["rougeL"].fmeasure

    # Context hit rate (simple keyword match)
    gt_tokens = set(gt.replace(",", " ").replace(".", " ").split())
    gt_tokens = {t for t in gt_tokens if len(t) >= 3}
    joined_ctx = " ".join(contexts)
    hits = sum(1 for t in gt_tokens if t in joined_ctx)
    hit_rate = hits / max(1, len(gt_tokens))

    # Answer length ratio: ideal 80-500 chars
    L = len(answer)
    if 80 <= L <= 500:
        length_score = 1.0
    elif L < 80:
        length_score = L / 80
    else:
        length_score = max(0.0, 1 - (L - 500) / 1000)

    # Retrieval coverage
    coverage = min(1.0, len(contexts) / 4)

    return {
        "context_hit_rate": round(hit_rate, 4),
        "answer_rouge_l": round(rouge, 4),
        "answer_length_ratio": round(length_score, 4),
        "retrieval_coverage": round(coverage, 4),
    }


# ──────────────────────────────────────────────────────────────────────
# RAGAs judge (vLLM 또는 proxy)
# ──────────────────────────────────────────────────────────────────────

def run_ragas_judge(rows: list[dict]) -> dict[str, Any]:
    """Try RAGAs 0.4 with vLLM as judge LLM. Fall back to proxy on any error."""
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from langchain_openai import ChatOpenAI
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except ImportError as e:
        print(f"   ⚠️  RAGAs/Langchain import 실패: {e} — proxy mode")
        return {"mode": "proxy_only_due_to_import_error", "error": str(e)}

    # 1. vLLM을 judge LLM으로 연결
    try:
        judge_llm = ChatOpenAI(
            model=LLM_MODEL_ID,
            openai_api_base=VLLM_BASE_URL,
            openai_api_key="dummy",
            temperature=0.0,
            timeout=60,
        )
        wrapped_llm = LangchainLLMWrapper(judge_llm)
        print("✅ Judge LLM: vLLM (Qwen2.5-7B)")
    except Exception as e:
        print(f"   ⚠️  Judge LLM 초기화 실패: {e}")
        return {"mode": "proxy_only_due_to_judge_init", "error": str(e)}

    # 2. Embeddings wrapper (RAGAs requires embeddings for answer_relevancy)
    try:
        embed = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
        wrapped_embed = LangchainEmbeddingsWrapper(embed)
        print("✅ Embeddings wrapper 준비")
    except Exception as e:
        print(f"   ⚠️  Embeddings wrapper 실패: {e}")
        return {"mode": "proxy_only_due_to_embed_init", "error": str(e)}

    # 3. Dataset 구성 (RAGAs 0.4+ 명칭 체계)
    data = {
        "question": [r["_question"] for r in rows],
        "answer": [r["_answer"] for r in rows],
        "contexts": [r["_contexts"] for r in rows],
        "ground_truth": [r["_ground_truth"] for r in rows],
    }
    ds = Dataset.from_dict(data)

    # 4. RAGAs evaluate
    print(f"🔍 RAGAs evaluate 시작 (n={len(rows)})... (judge LLM 호출 多 — 시간 소요)")
    try:
        t0 = time.time()
        result = evaluate(
            dataset=ds,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=wrapped_llm,
            embeddings=wrapped_embed,
            raise_exceptions=False,
        )
        elapsed = time.time() - t0
        print(f"   ✅ RAGAs 완료 ({elapsed:.1f}초)")
        # result is EvaluationResult — convert to dict
        out = {}
        try:
            # 0.4+ API: to_pandas() 또는 직접 dict 접근
            df = result.to_pandas()
            for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
                if metric in df.columns:
                    vals = df[metric].dropna().tolist()
                    if vals:
                        out[metric] = {
                            "mean": round(float(np.mean(vals)), 4),
                            "std": round(float(np.std(vals)), 4),
                            "n_valid": len(vals),
                        }
        except Exception as e:
            print(f"   ⚠️  result parse 실패 → str fallback: {e}")
            out["raw"] = str(result)
        return {"mode": "ragas_vllm", "metrics": out, "elapsed_sec": elapsed}
    except Exception as e:
        print(f"   ⚠️  RAGAs evaluate 실패: {e}")
        traceback.print_exc()
        return {"mode": "proxy_only_due_to_eval_error", "error": str(e)}


# ──────────────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20, help="샘플 수")
    parser.add_argument("--judge", choices=["vllm", "proxy"], default="vllm")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--k", type=int, default=4, help="retrieval top-k")
    args = parser.parse_args()

    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print(f"  SkyOps Intelligence — RAGAs Benchmark (n={args.n}, judge={args.judge})")
    print("=" * 65)

    # Phase 1: sample benchmark
    rows = load_benchmark(args.n, args.seed)

    # Phase 2: retrieve + generate answers
    retrieve = build_retriever(k=args.k)
    print(f"\n🧠 RAG inference 시작 (n={len(rows)})...")
    t_infer = time.time()
    use_vllm_gen = args.judge == "vllm"
    for i, r in enumerate(rows, 1):
        q = r["_question"]
        ctxs = retrieve(q)
        r["_contexts"] = ctxs
        r["_answer"] = generate_answer(q, ctxs, use_vllm=use_vllm_gen)
        if i % 5 == 0 or i == len(rows):
            print(f"   [{i}/{len(rows)}] done")
    infer_sec = time.time() - t_infer
    print(f"   ✅ RAG inference 완료 ({infer_sec:.1f}초)")

    # Phase 3: evaluate (RAGAs or proxy)
    ragas_out = {}
    if args.judge == "vllm":
        ragas_out = run_ragas_judge(rows)

    # Always compute proxy metrics as baseline
    print("\n📊 Proxy metrics 계산 중...")
    proxies = [proxy_metrics(r) for r in rows]
    proxy_summary = {}
    for key in ["context_hit_rate", "answer_rouge_l", "answer_length_ratio", "retrieval_coverage"]:
        vals = [p[key] for p in proxies]
        proxy_summary[key] = {
            "mean": round(float(np.mean(vals)), 4),
            "std": round(float(np.std(vals)), 4),
            "n": len(vals),
        }
    print("   ✅ Proxy metrics 완료")

    # Phase 4: save results
    timestamp = datetime.now(timezone.utc).isoformat()
    result_obj = {
        "timestamp": timestamp,
        "n_samples": len(rows),
        "judge_mode": args.judge,
        "ragas": ragas_out,
        "proxy": proxy_summary,
        "per_type_breakdown": breakdown_by_type(rows, proxies),
        "infer_elapsed_sec": round(infer_sec, 1),
    }

    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(result_obj, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Results JSON: {RESULTS_JSON}")

    md = render_markdown(result_obj)
    with open(RESULTS_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"💾 Results MD:   {RESULTS_MD}")

    print("\n" + "=" * 65)
    print(f"  ✅ RAGAs Benchmark 완료")
    print("=" * 65)


def breakdown_by_type(rows: list[dict], proxies: list[dict]) -> dict:
    """Proxy metrics by question type."""
    by_type: dict[str, list] = {}
    for r, p in zip(rows, proxies):
        t = r.get("type", "unknown")
        by_type.setdefault(t, []).append(p)
    out = {}
    for t, items in by_type.items():
        out[t] = {
            "n": len(items),
            **{
                k: round(float(np.mean([p[k] for p in items])), 4)
                for k in ["context_hit_rate", "answer_rouge_l", "answer_length_ratio", "retrieval_coverage"]
            },
        }
    return out


def render_markdown(result: dict) -> str:
    lines = [
        "# SkyOps RAGAs Benchmark Results",
        "",
        f"- **Timestamp**: {result['timestamp']}",
        f"- **Samples**: {result['n_samples']}",
        f"- **Judge mode**: `{result['judge_mode']}`",
        f"- **Inference elapsed**: {result['infer_elapsed_sec']}s",
        "",
        "## RAGAs Metrics (Judge: vLLM Qwen2.5-7B)",
        "",
    ]
    ragas = result.get("ragas") or {}
    if ragas.get("mode") == "ragas_vllm" and ragas.get("metrics"):
        lines.append("| Metric | Mean | Std | N valid |")
        lines.append("|--------|------|-----|---------|")
        for metric_name, stats in ragas["metrics"].items():
            if isinstance(stats, dict) and "mean" in stats:
                lines.append(
                    f"| {metric_name} | {stats['mean']} | {stats['std']} | {stats.get('n_valid', '-')} |"
                )
        lines.append(f"\n*(elapsed: {ragas.get('elapsed_sec', '?')}s)*")
    else:
        err = ragas.get("error") or ragas.get("mode", "unknown")
        lines.append(f"> ⚠️  RAGAs 모드 사용 불가 — `{ragas.get('mode', 'none')}`")
        if err:
            lines.append(f"> 에러: `{err}`")

    lines.append("\n## Proxy Metrics (Heuristic Fallback · always computed)\n")
    lines.append("| Metric | Mean | Std | N |")
    lines.append("|--------|------|-----|---|")
    for metric, stats in result["proxy"].items():
        lines.append(f"| {metric} | {stats['mean']} | {stats['std']} | {stats['n']} |")

    lines.append("\n## Breakdown by Question Type\n")
    lines.append("| Type | N | context_hit_rate | answer_rouge_l | answer_length_ratio | retrieval_coverage |")
    lines.append("|------|---|------------------|----------------|---------------------|--------------------|")
    for t, stats in result["per_type_breakdown"].items():
        lines.append(
            f"| {t} | {stats['n']} | {stats['context_hit_rate']} | {stats['answer_rouge_l']}"
            f" | {stats['answer_length_ratio']} | {stats['retrieval_coverage']} |"
        )

    lines += [
        "",
        "## 지표 해석",
        "",
        "**RAGAs 정식 지표** (Judge LLM 필요):",
        "- **faithfulness** (0~1, 高): 답변이 retrieved context와 일치하는 정도. 낮으면 hallucination 의심.",
        "- **answer_relevancy** (0~1, 高): 답변이 질문과 관련되는 정도.",
        "- **context_precision** (0~1, 高): 검색된 문서 중 질문에 도움되는 비율.",
        "- **context_recall** (0~1, 高): 정답에 필요한 정보가 검색되었는가 (ground_truth 기반).",
        "",
        "**Proxy 지표** (LLM 불필요 · 항상 계산):",
        "- **context_hit_rate**: ground_truth 키워드가 context에 포함된 비율 (recall proxy).",
        "- **answer_rouge_l**: generated vs ground_truth ROUGE-L F1.",
        "- **answer_length_ratio**: 80~500 chars 범위일수록 1.0, 너무 짧거나 길면 감소.",
        "- **retrieval_coverage**: len(contexts) / expected (4).",
        "",
        "## 후속 과제",
        "- 샘플 수 확장 (500건 전체)",
        "- OpenAI API judge와 비교 (vLLM judge 품질 검증)",
        "- Per-chunk citation 강제 (grounded generation)",
        "- Hallucination detection threshold 튜닝",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
