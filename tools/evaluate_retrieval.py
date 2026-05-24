"""
Module: evaluate_retrieval
Purpose: Run PakLaw AI and BM25 baseline retrieval over the annotated evaluation set and write results/metrics.
Inputs: eval/test_questions.md plus optional annotation updates in the same table format.
Outputs: eval/results_paklaw.md, eval/results_baseline.md, eval/metrics.md.
Dependencies: retriever, standard library.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retriever import retrieve_bm25_only, retrieve_chunks


QUESTIONS_PATH = ROOT / "eval" / "test_questions.md"
PAKLAW_RESULTS_PATH = ROOT / "eval" / "results_paklaw.md"
BASELINE_RESULTS_PATH = ROOT / "eval" / "results_baseline.md"
METRICS_PATH = ROOT / "eval" / "metrics.md"
DEFAULT_TOP_K = 10


@dataclass(frozen=True)
class QuestionRow:
    question_id: str
    domain: str
    question: str
    ground_truth: str
    status: str


@dataclass(frozen=True)
class ResultRow:
    question: QuestionRow
    retrieved: list[dict]
    first_correct_rank: int | None
    relevant_top1: bool
    relevant_top5: bool
    relevant_top10: bool


_TABLE_ROW_RE = re.compile(r"^\|\s*Q\d+\s*\|")


def _split_markdown_row(line: str) -> list[str]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return cells


def _parse_questions(path: Path) -> list[QuestionRow]:
    rows: list[QuestionRow] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    in_table = False

    for line in lines:
        if line.startswith("| ID | Domain | Question | Ground-truth target | Status |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|") or line.startswith("|---"):
            continue
        if not _TABLE_ROW_RE.match(line):
            continue

        cells = _split_markdown_row(line)
        if len(cells) < 5:
            continue
        rows.append(
            QuestionRow(
                question_id=cells[0],
                domain=cells[1],
                question=cells[2],
                ground_truth=cells[3],
                status=cells[4],
            )
        )

    return rows


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _is_annotated(question: QuestionRow) -> bool:
    return question.ground_truth and "annotate from corpus" not in _normalize(question.ground_truth)


def _chunk_label(chunk: dict) -> str:
    chunk_id = chunk.get("chunk_id", "?")
    source_doc = chunk.get("source_doc", "unknown")
    section_hint = chunk.get("section_hint") or "N/A"
    return f"{chunk_id}:{source_doc}:{section_hint}"


def _is_relevant(chunk: dict, ground_truth: str) -> bool:
    target = _normalize(ground_truth)
    if not target:
        return False

    haystack_parts = [
        str(chunk.get("source_doc", "")),
        str(chunk.get("section_hint", "")),
        str(chunk.get("text", "")),
    ]
    haystack = _normalize(" \n".join(haystack_parts))
    return target in haystack


def _first_correct_rank(results: Iterable[dict], ground_truth: str) -> int | None:
    for index, chunk in enumerate(results, start=1):
        if _is_relevant(chunk, ground_truth):
            return index
    return None


def _score_question(question: QuestionRow, retrieved: list[dict]) -> ResultRow:
    if not _is_annotated(question):
        return ResultRow(question, retrieved, None, False, False, False)

    first_rank = _first_correct_rank(retrieved, question.ground_truth)
    relevant_top1 = first_rank == 1
    relevant_top5 = first_rank is not None and first_rank <= 5
    relevant_top10 = first_rank is not None and first_rank <= 10
    return ResultRow(question, retrieved, first_rank, relevant_top1, relevant_top5, relevant_top10)


def _render_results_table(title: str, rows: list[ResultRow]) -> str:
    lines = [f"# {title}", "", "| ID | Question | Ground-truth target | Top-10 retrieved chunk IDs / source labels | First correct rank | Relevant in top 1 | Relevant in top 5 | Relevant in top 10 | Notes |", "|---|---|---|---|---|---|---|---|---|"]

    for row in rows:
        if row.retrieved:
            top_hits = "; ".join(_chunk_label(chunk) for chunk in row.retrieved[:DEFAULT_TOP_K])
        else:
            top_hits = ""
        first_rank = "" if row.first_correct_rank is None else str(row.first_correct_rank)
        notes = "pending annotation" if not _is_annotated(row.question) else ""
        lines.append(
            f"| {row.question.question_id} | {row.question.question} | {row.question.ground_truth} | {top_hits} | {first_rank} | {str(row.relevant_top1)} | {str(row.relevant_top5)} | {str(row.relevant_top10)} | {notes} |"
        )

    return "\n".join(lines) + "\n"


def _write_metrics(rows_paklaw: list[ResultRow], rows_baseline: list[ResultRow]) -> str:
    def compute(rows: list[ResultRow]) -> tuple[float, float, float, float]:
        annotated = [row for row in rows if _is_annotated(row.question)]
        if not annotated:
            return 0.0, 0.0, 0.0, 0.0

        precision_1 = sum(row.relevant_top1 for row in annotated) / len(annotated)
        precision_5 = sum(row.relevant_top5 for row in annotated) / len(annotated)
        precision_10 = sum(row.relevant_top10 for row in annotated) / len(annotated)
        mrr = sum(0.0 if row.first_correct_rank is None else 1 / row.first_correct_rank for row in annotated) / len(annotated)
        return precision_1, precision_5, precision_10, mrr

    paklaw_metrics = compute(rows_paklaw)
    baseline_metrics = compute(rows_baseline)

    lines = [
        "# Evaluation Metrics",
        "",
        "| Metric | BM25 Baseline | PakLaw AI |",
        "|---|---|---|",
        f"| Precision@1 | {baseline_metrics[0]:.4f} | {paklaw_metrics[0]:.4f} |",
        f"| Precision@5 | {baseline_metrics[1]:.4f} | {paklaw_metrics[1]:.4f} |",
        f"| Precision@10 | {baseline_metrics[2]:.4f} | {paklaw_metrics[2]:.4f} |",
        f"| MRR | {baseline_metrics[3]:.4f} | {paklaw_metrics[3]:.4f} |",
        "",
        "## Notes",
        "",
        "- Values are computed only for questions with annotated ground-truth targets.",
        "- If the ground-truth column still says `To annotate from corpus`, the row is skipped for scoring.",
    ]
    return "\n".join(lines) + "\n"


def _run_retrieval(rows: list[QuestionRow], mode: str, index_root: str, top_k: int) -> list[ResultRow]:
    scored_rows: list[ResultRow] = []

    for question in rows:
        if mode == "paklaw":
            try:
                retrieved = retrieve_chunks(question.question, index_root=index_root, top_k=top_k)
            except FileNotFoundError as exc:
                retrieved = []
                print(f"[WARN] {question.question_id}: {exc}")
        else:
            try:
                retrieved = retrieve_bm25_only(question.question, index_root=index_root, top_k=top_k)
            except FileNotFoundError as exc:
                retrieved = []
                print(f"[WARN] {question.question_id}: {exc}")

        scored_rows.append(_score_question(question, retrieved))

    return scored_rows


def _annotated_count(rows: list[QuestionRow]) -> int:
    return sum(1 for row in rows if _is_annotated(row))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PakLaw AI evaluation and write retrieval/metrics markdown files.")
    parser.add_argument("--questions", default=str(QUESTIONS_PATH), help="Path to eval/test_questions.md")
    parser.add_argument("--index-root", default="indexes", help="Root directory containing public and firm indexes")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Number of results to record per question")
    parser.add_argument("--skip-retrieval", action="store_true", help="Only regenerate the metrics summary from existing result files")
    args = parser.parse_args()

    questions_path = Path(args.questions)
    questions = _parse_questions(questions_path)
    if not questions:
        print(f"No questions found in {questions_path}")
        return 1

    if args.skip_retrieval:
        print("Skipping retrieval run; result files were not updated.")
        return 0

    print(f"Loaded {len(questions)} questions ({_annotated_count(questions)} annotated)")
    paklaw_rows = _run_retrieval(questions, "paklaw", args.index_root, args.top_k)
    baseline_rows = _run_retrieval(questions, "baseline", args.index_root, args.top_k)

    PAKLAW_RESULTS_PATH.write_text(_render_results_table("PakLaw AI — Retrieval Results", paklaw_rows), encoding="utf-8")
    BASELINE_RESULTS_PATH.write_text(_render_results_table("BM25 Baseline — Retrieval Results", baseline_rows), encoding="utf-8")
    METRICS_PATH.write_text(_write_metrics(paklaw_rows, baseline_rows), encoding="utf-8")

    print(f"Wrote {PAKLAW_RESULTS_PATH}")
    print(f"Wrote {BASELINE_RESULTS_PATH}")
    print(f"Wrote {METRICS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
