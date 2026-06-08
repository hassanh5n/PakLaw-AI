"""
evaluate_paklaw.py
------------------
Terminal evaluation script for PakLaw AI.

Place this file in the root of your PakLaw-AI project and run:

    python evaluate_paklaw.py

Useful options:

    python evaluate_paklaw.py --top-k 8 --role public --corpora public
    python evaluate_paklaw.py --top-k 8 --role admin --firm-id firm_alpha --corpora combined
    python evaluate_paklaw.py --no-generate

What it evaluates:
- Retrieval: Precision@K, Recall@K, Hit@K, MRR@K, NDCG@K
- Baseline comparison: your hybrid retriever vs BM25-only retriever
- Runtime: retrieval time, generation time, total time
- Answer checks: required answer-term coverage and source-citation coverage

Important:
This script uses weak labels from EVAL_CASES below. For a real report, edit EVAL_CASES
so each query has the correct expected_doc_hints / expected_chunk_ids / expected_text_terms
for your own indexed Pakistani law PDFs.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any


# -----------------------------------------------------------------------------
# 1) EDIT THIS BENCHMARK FOR YOUR OWN CORPUS
# -----------------------------------------------------------------------------
# Keep 10-30 queries for your final report. For each query, add the expected law
# document hints, section hints, text terms, or exact chunk IDs after checking your
# retrieved source cards once manually.
#
# Relevance grading used by this script:
#   3 = exact expected_chunk_id match
#   2 = source/section hint + expected text-term match
#   1 = source/section hint OR expected text-term match
#   0 = not relevant
#
# Precision/MRR use grade > 0 as relevant. NDCG uses the 0-3 graded relevance.

EVAL_CASES: list[dict[str, Any]] = [
    {
        "id": "contract_validity_01",
        "query": "What are the conditions for a valid contract under Pakistani law?",
        "expected_doc_hints": ["contract"],
        "expected_section_hints": ["section 10", "10"],
        "expected_text_terms": ["free consent", "lawful consideration", "lawful object", "competent"],
        "answer_terms": ["free consent", "lawful consideration", "lawful object"],
        "expected_min_relevant": 1,
    },
    {
        "id": "contract_minor_02",
        "query": "Can a minor enter into a valid contract in Pakistan?",
        "expected_doc_hints": ["contract"],
        "expected_section_hints": ["section 11", "11"],
        "expected_text_terms": ["minor", "age of majority", "competent to contract"],
        "answer_terms": ["minor", "competent", "majority"],
        "expected_min_relevant": 1,
    },
    {
        "id": "constitution_equality_03",
        "query": "What does the Constitution of Pakistan say about equality before law?",
        "expected_doc_hints": ["constitution"],
        "expected_section_hints": ["article 25", "25"],
        "expected_text_terms": ["equality", "equal protection", "law"],
        "answer_terms": ["equality", "equal protection", "article 25"],
        "expected_min_relevant": 1,
    },
    {
        "id": "constitution_life_liberty_04",
        "query": "Which constitutional provision protects life and liberty in Pakistan?",
        "expected_doc_hints": ["constitution"],
        "expected_section_hints": ["article 9", "9"],
        "expected_text_terms": ["life", "liberty", "law"],
        "answer_terms": ["life", "liberty", "article 9"],
        "expected_min_relevant": 1,
    },
    {
        "id": "criminal_theft_05",
        "query": "What is theft under the Pakistan Penal Code?",
        "expected_doc_hints": ["penal", "ppc"],
        "expected_section_hints": ["section 378", "378"],
        "expected_text_terms": ["theft", "dishonestly", "movable property"],
        "answer_terms": ["dishonestly", "movable property", "theft"],
        "expected_min_relevant": 1,
    },
    {
        "id": "criminal_murder_06",
        "query": "What section of PPC deals with punishment for murder?",
        "expected_doc_hints": ["penal", "ppc"],
        "expected_section_hints": ["section 302", "302"],
        "expected_text_terms": ["qatl-i-amd", "murder", "death", "imprisonment"],
        "answer_terms": ["302", "murder", "punishment"],
        "expected_min_relevant": 1,
    },
    {
        "id": "labour_wages_07",
        "query": "What does Pakistani labour law say about payment of wages?",
        "expected_doc_hints": ["wages", "labour", "payment"],
        "expected_section_hints": [],
        "expected_text_terms": ["wages", "payment", "deduction"],
        "answer_terms": ["wages", "payment"],
        "expected_min_relevant": 1,
    },
    {
        "id": "company_directors_08",
        "query": "What are the legal duties or responsibilities of company directors in Pakistan?",
        "expected_doc_hints": ["companies", "company"],
        "expected_section_hints": [],
        "expected_text_terms": ["director", "duties", "company"],
        "answer_terms": ["director", "company"],
        "expected_min_relevant": 1,
    },
    {
        "id": "family_guardian_09",
        "query": "What law is relevant for guardianship of minors in Pakistan?",
        "expected_doc_hints": ["guardian", "minor", "family"],
        "expected_section_hints": [],
        "expected_text_terms": ["guardian", "minor", "court"],
        "answer_terms": ["guardian", "minor"],
        "expected_min_relevant": 1,
    },
    {
        "id": "adversarial_fake_10",
        "query": "Is it true that verbal threats always allow immediate arrest without any legal process?",
        "expected_doc_hints": ["criminal", "crpc", "penal", "ppc"],
        "expected_section_hints": [],
        "expected_text_terms": ["arrest", "threat", "offence", "warrant"],
        "answer_terms": ["depends", "arrest", "offence"],
        "expected_min_relevant": 1,
    },
]


# -----------------------------------------------------------------------------
# 2) IMPORT PROJECT MODULES
# -----------------------------------------------------------------------------

def add_project_paths() -> None:
    root = Path.cwd()
    candidates = [root, root / "core"]
    for path in candidates:
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))


def import_project_functions():
    add_project_paths()
    try:
        from retriever import retrieve_chunks
    except Exception as exc:
        raise RuntimeError(
            "Could not import retrieve_chunks from retriever.py. "
            "Run this file from the PakLaw-AI project root."
        ) from exc

    try:
        from retriever import retrieve_bm25_only
    except Exception:
        retrieve_bm25_only = None

    try:
        from generator import generate_answer
    except Exception:
        generate_answer = None

    return retrieve_chunks, retrieve_bm25_only, generate_answer


# -----------------------------------------------------------------------------
# 3) METRIC HELPERS
# -----------------------------------------------------------------------------

def norm(text: Any) -> str:
    return " ".join(str(text or "").lower().replace("_", " ").replace("-", " ").split())


def contains_any(haystack: str, needles: list[str]) -> bool:
    h = norm(haystack)
    return any(norm(n) in h for n in needles if norm(n))


def count_terms(haystack: str, terms: list[str]) -> int:
    h = norm(haystack)
    return sum(1 for term in terms if norm(term) and norm(term) in h)


def relevance_grade(result: dict[str, Any], case: dict[str, Any]) -> int:
    chunk_id = str(result.get("chunk_id", ""))
    source_doc = norm(result.get("source_doc", ""))
    section_hint = norm(result.get("section_hint", ""))
    text = norm(result.get("text", ""))

    expected_chunk_ids = {str(x) for x in case.get("expected_chunk_ids", [])}
    if expected_chunk_ids and chunk_id in expected_chunk_ids:
        return 3

    doc_hit = contains_any(source_doc, case.get("expected_doc_hints", []))
    section_hit = contains_any(section_hint, case.get("expected_section_hints", []))

    terms = case.get("expected_text_terms", [])
    term_hits = count_terms(text, terms)
    term_hit = term_hits > 0

    if (doc_hit or section_hit) and term_hit:
        return 2
    if doc_hit or section_hit or term_hit:
        return 1
    return 0


def precision_at_k(grades: list[int], k: int) -> float:
    if k <= 0:
        return 0.0
    considered = grades[:k]
    if not considered:
        return 0.0
    return sum(1 for g in considered if g > 0) / k


def recall_at_k(grades: list[int], k: int, expected_min_relevant: int) -> float:
    if expected_min_relevant <= 0:
        expected_min_relevant = 1
    found = sum(1 for g in grades[:k] if g > 0)
    return min(found / expected_min_relevant, 1.0)


def reciprocal_rank(grades: list[int], k: int) -> float:
    for i, g in enumerate(grades[:k], start=1):
        if g > 0:
            return 1.0 / i
    return 0.0


def dcg_at_k(grades: list[int], k: int) -> float:
    score = 0.0
    for i, g in enumerate(grades[:k], start=1):
        score += (2**g - 1) / math.log2(i + 1)
    return score


def ndcg_at_k(grades: list[int], k: int) -> float:
    actual = dcg_at_k(grades, k)
    ideal_grades = sorted(grades, reverse=True)
    ideal = dcg_at_k(ideal_grades, k)
    return actual / ideal if ideal > 0 else 0.0


def answer_term_coverage(answer: str, case: dict[str, Any]) -> float:
    terms = case.get("answer_terms", [])
    if not terms:
        return 0.0
    return count_terms(answer, terms) / len(terms)


def source_coverage(answer: str, results: list[dict[str, Any]]) -> float:
    # Checks whether the generated answer visibly cites/mentions source document names.
    # This is a lightweight proxy, not a substitute for human legal citation review.
    docs = []
    for r in results[:5]:
        doc = str(r.get("source_doc", "")).strip()
        if not doc:
            continue
        stem = Path(doc).stem.lower()
        if stem and stem not in docs:
            docs.append(stem)
    if not docs:
        return 0.0
    ans = norm(answer)
    hits = 0
    for doc in docs:
        compact_doc = norm(doc)
        # Accept either full stem or first meaningful token from file name.
        tokens = [t for t in compact_doc.split() if len(t) >= 4]
        if compact_doc in ans or (tokens and any(t in ans for t in tokens[:3])):
            hits += 1
    return hits / len(docs)


def avg(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


# -----------------------------------------------------------------------------
# 4) EVALUATION RUNNER
# -----------------------------------------------------------------------------

def resolve_corpora_arg(corpora: str) -> list[str] | None:
    value = corpora.strip().lower()
    if value == "combined":
        return None
    if value in {"public", "firm"}:
        return [value]
    raise ValueError("--corpora must be one of: public, firm, combined")


def run_retriever(name: str, fn, case: dict[str, Any], args) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        results = fn(
            case["query"],
            role=args.role,
            firm_id=args.firm_id,
            index_root=args.index_root,
            expand=args.expand,
            top_k=args.top_k,
            corpora=resolve_corpora_arg(args.corpora),
        )
        error = None
    except Exception as exc:
        results = []
        error = str(exc)
    elapsed = time.perf_counter() - started

    grades = [relevance_grade(r, case) for r in results]
    expected_min = int(case.get("expected_min_relevant", 1) or 1)

    metrics = {
        "precision_at_k": precision_at_k(grades, args.top_k),
        "recall_at_k": recall_at_k(grades, args.top_k, expected_min),
        "hit_at_k": 1.0 if any(g > 0 for g in grades[: args.top_k]) else 0.0,
        "mrr_at_k": reciprocal_rank(grades, args.top_k),
        "ndcg_at_k": ndcg_at_k(grades, args.top_k),
        "retrieval_time_ms": elapsed * 1000,
        "result_count": len(results),
        "low_confidence_count": sum(1 for r in results if r.get("low_confidence")),
    }

    return {
        "name": name,
        "results": results,
        "grades": grades,
        "metrics": metrics,
        "error": error,
    }


def generate_answer_safe(generate_answer, query: str, results: list[dict[str, Any]], enabled: bool) -> tuple[str, float, str | None]:
    if not enabled:
        return "", 0.0, None
    if generate_answer is None:
        return "", 0.0, "generator.generate_answer could not be imported"

    started = time.perf_counter()
    try:
        answer = generate_answer(query, results)
        error = None
    except Exception as exc:
        answer = ""
        error = str(exc)
    elapsed = time.perf_counter() - started
    return answer, elapsed * 1000, error


def print_result_rows(results: list[dict[str, Any]], grades: list[int], top_n: int) -> None:
    print("\nTop retrieved sources:")
    print("rank | rel | score   | source_doc | section | method | low_conf")
    print("-----+-----+---------+------------+---------+--------+---------")
    for i, (r, grade) in enumerate(zip(results[:top_n], grades[:top_n]), start=1):
        score = r.get("relevance_score", r.get("rerank_score", r.get("combined_score", 0.0)))
        try:
            score_text = f"{float(score):.4f}"
        except Exception:
            score_text = str(score)[:8]
        source = str(r.get("source_doc", "unknown"))[:42]
        section = str(r.get("section_hint") or "-")[:16]
        method = str(r.get("retrieval_method", "-"))[:10]
        low_conf = "yes" if r.get("low_confidence") else "no"
        print(f"{i:>4} | {grade:>3} | {score_text:<7} | {source:<42} | {section:<16} | {method:<10} | {low_conf}")


def summarize_runs(records: list[dict[str, Any]], retriever_name: str) -> dict[str, float]:
    selected = [r for r in records if r["retriever"] == retriever_name]
    fields = [
        "precision_at_k",
        "recall_at_k",
        "hit_at_k",
        "mrr_at_k",
        "ndcg_at_k",
        "retrieval_time_ms",
        "generation_time_ms",
        "answer_term_coverage",
        "source_coverage",
        "result_count",
        "low_confidence_count",
    ]
    return {field: avg([float(r.get(field, 0.0)) for r in selected]) for field in fields}


def print_summary(name: str, summary: dict[str, float], k: int) -> None:
    print(f"\n{name} aggregate results")
    print("-" * 72)
    print(f"Precision@{k}:        {summary['precision_at_k']:.3f}")
    print(f"Recall@{k}:           {summary['recall_at_k']:.3f}")
    print(f"Hit@{k}:              {summary['hit_at_k']:.3f}")
    print(f"MRR@{k}:              {summary['mrr_at_k']:.3f}")
    print(f"NDCG@{k}:             {summary['ndcg_at_k']:.3f}")
    print(f"Retrieval time:       {summary['retrieval_time_ms']:.1f} ms/query")
    print(f"Generation time:      {summary['generation_time_ms']:.1f} ms/query")
    print(f"Answer term coverage: {summary['answer_term_coverage']:.3f}")
    print(f"Source coverage:      {summary['source_coverage']:.3f}")
    print(f"Avg returned chunks:  {summary['result_count']:.1f}")
    print(f"Avg low-conf chunks:  {summary['low_confidence_count']:.1f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate PakLaw AI retrieval and generated terminal answers.")
    parser.add_argument("--top-k", type=int, default=8, help="Number of retrieved chunks to evaluate.")
    parser.add_argument("--role", default="public", choices=["public", "user", "admin"], help="Access role for retrieval.")
    parser.add_argument("--firm-id", default=None, help="Firm id for firm/combined evaluation, e.g. firm_alpha.")
    parser.add_argument("--corpora", default="public", choices=["public", "firm", "combined"], help="Corpus scope.")
    parser.add_argument("--index-root", default="indexes", help="Path to index root directory.")
    parser.add_argument("--expand", action="store_true", help="Enable query expansion if GROQ_API_KEY exists.")
    parser.add_argument("--no-generate", action="store_true", help="Skip LLM answer generation and only evaluate retrieval.")
    parser.add_argument("--show-text", action="store_true", help="Print text preview for each top retrieved chunk.")
    parser.add_argument("--json-out", default="eval_results.json", help="Where to save machine-readable results.")
    args = parser.parse_args()

    print("PakLaw AI Evaluation")
    print("=" * 72)
    print(f"Working directory: {Path.cwd()}")
    print(f"Role/corpora: {args.role}/{args.corpora} | firm_id={args.firm_id or '-'} | top_k={args.top_k}")
    print(f"Query expansion: {'on' if args.expand else 'off'} | Generation: {'off' if args.no_generate else 'on'}")

    retrieve_chunks, retrieve_bm25_only, generate_answer = import_project_functions()
    retrievers = [("HYBRID_FAISS_BM25_RERANK", retrieve_chunks)]
    if retrieve_bm25_only is not None:
        retrievers.append(("BM25_ONLY_BASELINE", retrieve_bm25_only))
    else:
        print("\n[WARN] retrieve_bm25_only was not found, so BM25 baseline will be skipped.")

    all_records: list[dict[str, Any]] = []

    for case_index, case in enumerate(EVAL_CASES, start=1):
        print("\n" + "=" * 72)
        print(f"CASE {case_index}/{len(EVAL_CASES)}: {case['id']}")
        print(f"Query: {case['query']}")
        print(f"Expected doc hints: {case.get('expected_doc_hints', [])}")
        print(f"Expected section hints: {case.get('expected_section_hints', [])}")
        print(f"Expected text terms: {case.get('expected_text_terms', [])}")

        for retriever_name, retriever_fn in retrievers:
            print("\n" + "-" * 72)
            print(f"Retriever: {retriever_name}")
            run = run_retriever(retriever_name, retriever_fn, case, args)

            if run["error"]:
                print(f"[ERROR] Retrieval failed: {run['error']}")

            metrics = run["metrics"]
            print(
                f"Metrics: P@{args.top_k}={metrics['precision_at_k']:.3f}, "
                f"R@{args.top_k}={metrics['recall_at_k']:.3f}, "
                f"Hit@{args.top_k}={metrics['hit_at_k']:.0f}, "
                f"MRR@{args.top_k}={metrics['mrr_at_k']:.3f}, "
                f"NDCG@{args.top_k}={metrics['ndcg_at_k']:.3f}, "
                f"retrieval={metrics['retrieval_time_ms']:.1f}ms"
            )

            print_result_rows(run["results"], run["grades"], args.top_k)

            if args.show_text:
                for i, r in enumerate(run["results"][: args.top_k], start=1):
                    preview = " ".join(str(r.get("text", "")).split())[:500]
                    print(f"\nChunk {i} preview: {preview}")

            # Generate answer only for the main hybrid system, not for BM25 baseline.
            answer = ""
            generation_time_ms = 0.0
            generation_error = None
            ans_term_cov = 0.0
            src_cov = 0.0
            if retriever_name == "HYBRID_FAISS_BM25_RERANK":
                answer, generation_time_ms, generation_error = generate_answer_safe(
                    generate_answer,
                    case["query"],
                    run["results"],
                    enabled=not args.no_generate,
                )
                if generation_error:
                    print(f"\n[ANSWER ERROR] {generation_error}")
                elif answer:
                    print("\nGenerated answer:")
                    print(answer)
                ans_term_cov = answer_term_coverage(answer, case) if answer else 0.0
                src_cov = source_coverage(answer, run["results"]) if answer else 0.0
                if not args.no_generate:
                    print(
                        f"\nAnswer checks: term_coverage={ans_term_cov:.3f}, "
                        f"source_coverage={src_cov:.3f}, generation={generation_time_ms:.1f}ms"
                    )

            record = {
                "case_id": case["id"],
                "query": case["query"],
                "retriever": retriever_name,
                **metrics,
                "generation_time_ms": generation_time_ms,
                "answer_term_coverage": ans_term_cov,
                "source_coverage": src_cov,
                "error": run["error"],
                "generation_error": generation_error,
                "top_results": [
                    {
                        "rank": i,
                        "grade": run["grades"][i - 1] if i - 1 < len(run["grades"]) else 0,
                        "chunk_id": r.get("chunk_id"),
                        "source_doc": r.get("source_doc"),
                        "section_hint": r.get("section_hint"),
                        "corpus": r.get("corpus"),
                        "relevance_score": r.get("relevance_score"),
                        "rerank_score": r.get("rerank_score"),
                        "bm25_score": r.get("bm25_score"),
                        "faiss_score": r.get("faiss_score"),
                        "low_confidence": bool(r.get("low_confidence")),
                    }
                    for i, r in enumerate(run["results"][: args.top_k], start=1)
                ],
                "answer": answer,
            }
            all_records.append(record)

    print("\n" + "=" * 72)
    print("FINAL SUMMARY")
    print("=" * 72)

    hybrid_summary = summarize_runs(all_records, "HYBRID_FAISS_BM25_RERANK")
    print_summary("Hybrid FAISS + BM25 + reranker", hybrid_summary, args.top_k)

    if retrieve_bm25_only is not None:
        bm25_summary = summarize_runs(all_records, "BM25_ONLY_BASELINE")
        print_summary("BM25-only baseline", bm25_summary, args.top_k)

        print("\nDifference: hybrid minus BM25 baseline")
        print("-" * 72)
        for field in ["precision_at_k", "recall_at_k", "hit_at_k", "mrr_at_k", "ndcg_at_k", "retrieval_time_ms"]:
            print(f"{field:<22} {hybrid_summary[field] - bm25_summary[field]:+.3f}")

    output = {
        "config": {
            "top_k": args.top_k,
            "role": args.role,
            "firm_id": args.firm_id,
            "corpora": args.corpora,
            "index_root": args.index_root,
            "expand": args.expand,
            "generation": not args.no_generate,
        },
        "records": all_records,
        "summaries": {
            "hybrid": hybrid_summary,
            "bm25": summarize_runs(all_records, "BM25_ONLY_BASELINE") if retrieve_bm25_only is not None else None,
        },
    }
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved detailed results to: {args.json_out}")

    print("\nNotes:")
    print("1. If scores look unfair, edit EVAL_CASES with exact expected_chunk_ids after manual inspection.")
    print("2. For the report, use at least 20 labeled queries: simple, moderate, complex, and adversarial.")
    print("3. Retrieval metrics are meaningful only when your labels match your actual indexed PDFs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
