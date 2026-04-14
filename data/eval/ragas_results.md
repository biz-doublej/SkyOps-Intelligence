# SkyOps RAGAs Benchmark Results

- **Timestamp**: 2026-04-14T13:56:47.642974+00:00
- **Samples**: 30
- **Judge mode**: `proxy`
- **Inference elapsed**: 4.1s

## RAGAs Metrics (Judge: vLLM Qwen2.5-7B)

> ⚠️  RAGAs 모드 사용 불가 — `none`
> 에러: `unknown`

## Proxy Metrics (Heuristic Fallback · always computed)

| Metric | Mean | Std | N |
|--------|------|-----|---|
| context_hit_rate | 0.0388 | 0.0588 | 30 |
| answer_rouge_l | 0.0319 | 0.0741 | 30 |
| answer_length_ratio | 1.0 | 0.0 | 30 |
| retrieval_coverage | 1.0 | 0.0 | 30 |

## Breakdown by Question Type

| Type | N | context_hit_rate | answer_rouge_l | answer_length_ratio | retrieval_coverage |
|------|---|------------------|----------------|---------------------|--------------------|
| anomaly | 10 | 0.0243 | 0.0037 | 1.0 | 1.0 |
| announcement | 10 | 0.0569 | 0.0668 | 1.0 | 1.0 |
| regulation | 10 | 0.0353 | 0.0253 | 1.0 | 1.0 |

## 지표 해석

**RAGAs 정식 지표** (Judge LLM 필요):
- **faithfulness** (0~1, 高): 답변이 retrieved context와 일치하는 정도. 낮으면 hallucination 의심.
- **answer_relevancy** (0~1, 高): 답변이 질문과 관련되는 정도.
- **context_precision** (0~1, 高): 검색된 문서 중 질문에 도움되는 비율.
- **context_recall** (0~1, 高): 정답에 필요한 정보가 검색되었는가 (ground_truth 기반).

**Proxy 지표** (LLM 불필요 · 항상 계산):
- **context_hit_rate**: ground_truth 키워드가 context에 포함된 비율 (recall proxy).
- **answer_rouge_l**: generated vs ground_truth ROUGE-L F1.
- **answer_length_ratio**: 80~500 chars 범위일수록 1.0, 너무 짧거나 길면 감소.
- **retrieval_coverage**: len(contexts) / expected (4).

## 후속 과제
- 샘플 수 확장 (500건 전체)
- OpenAI API judge와 비교 (vLLM judge 품질 검증)
- Per-chunk citation 강제 (grounded generation)
- Hallucination detection threshold 튜닝