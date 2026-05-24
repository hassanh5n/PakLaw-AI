"""
Module: project_readiness
Purpose: Report which required PakLaw AI artifacts are present or missing.
Inputs: Workspace files on disk.
Outputs: Human-readable readiness summary.
Dependencies: Python standard library only.
"""

from __future__ import annotations

from pathlib import Path
from importlib.util import find_spec


ROOT = Path(__file__).resolve().parents[1]


def _status(label: str, condition: bool, detail: str) -> str:
	mark = "OK" if condition else "MISSING"
	return f"[{mark}] {label}: {detail}"


def _list_pdfs(folder: Path) -> list[Path]:
	if not folder.exists():
		return []
	return sorted(path for path in folder.glob("*.pdf") if path.is_file())


def main() -> None:
	public_dir = ROOT / "data" / "public"
	public_indexes = ROOT / "indexes" / "public"
	report_pdf = ROOT / "report" / "report.pdf"
	readme_report = ROOT / "report" / "report.md"
	eval_questions = ROOT / "eval" / "test_questions.md"
	eval_paklaw = ROOT / "eval" / "results_paklaw.md"
	eval_baseline = ROOT / "eval" / "results_baseline.md"
	eval_metrics = ROOT / "eval" / "metrics.md"
	test_log = ROOT / "tests" / "q_and_a_log.md"

	public_pdfs = _list_pdfs(public_dir)
	required_public_indexes = [
		public_indexes / "pakistan_law_public.faiss",
		public_indexes / "pakistan_law_public_chunks.pkl",
		public_indexes / "pakistan_law_public_bm25.pkl",
	]

	print("PakLaw AI readiness check")
	print(_status("Public corpus PDFs", len(public_pdfs) >= 1, f"{len(public_pdfs)} PDF(s) in data/public"))
	for pdf_path in public_pdfs:
		print(f"    - {pdf_path.name}")
	print(
		_status(
			"Public indexes",
			all(path.exists() and path.stat().st_size > 0 for path in required_public_indexes),
			", ".join(path.name for path in required_public_indexes),
		)
	)
	print(_status("Report draft", readme_report.exists(), "report/report.md"))
	print(_status("Compiled report", report_pdf.exists() and report_pdf.stat().st_size > 0, "report/report.pdf"))
	print(_status("Evaluation questions", eval_questions.exists(), "eval/test_questions.md"))
	print(_status("PakLaw results scaffold", eval_paklaw.exists(), "eval/results_paklaw.md"))
	print(_status("Baseline results scaffold", eval_baseline.exists(), "eval/results_baseline.md"))
	print(_status("Metrics sheet", eval_metrics.exists(), "eval/metrics.md"))
	print(_status("Generation log", test_log.exists(), "tests/q_and_a_log.md"))
	print(_status("bcrypt package", find_spec("bcrypt") is not None, "optional auth dependency"))
	print(_status("langchain_text_splitters package", find_spec("langchain_text_splitters") is not None, "optional chunking dependency"))


if __name__ == "__main__":
	main()