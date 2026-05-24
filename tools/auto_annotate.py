"""Auto-annotate evaluation questions using top retrieval hits.

Outputs lines: QUESTION_ID\tGROUND_TRUTH
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluate_retrieval import _parse_questions
from retriever import retrieve_public_chunks


def main():
    questions = _parse_questions(Path("eval/test_questions.md"))
    for q in questions:
        hits = retrieve_public_chunks(q.question, index_root="indexes", top_k=1)
        if hits:
            doc = hits[0].get("source_doc", "")
            section = hits[0].get("section_hint") or ""
            gt = f"{doc} | {section}" if section else f"{doc}"
        else:
            gt = ""
        print(f"{q.question_id}\t{gt}")


if __name__ == "__main__":
    main()
