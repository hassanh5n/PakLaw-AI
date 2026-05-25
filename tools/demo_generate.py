"""Demo: retrieve top chunks and generate a Groq-grounded answer.

Usage: python tools/demo_generate.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retriever import retrieve_chunks
from generator import generate_answer


def main():
    query = "Which section defines theft?"
    print("Demo query:", query)

    print("Running retrieval (public)...")
    hits = retrieve_chunks(query, role="public", index_root="indexes", top_k=5)
    print(f"Retrieved {len(hits)} chunks")
    for i, h in enumerate(hits, start=1):
        print(f"{i}. {h.get('chunk_id')} — {h.get('source_doc')} — {h.get('section_hint')}")

    print("\nGenerating answer via Groq...")
    answer = generate_answer(query, hits)
    print("\n--- GENERATED ANSWER ---\n")
    print(answer)
    print("\n--- END ANSWER ---\n")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
