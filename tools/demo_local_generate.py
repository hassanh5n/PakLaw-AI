"""Local demo: produce an extractive, cited answer from top retrieved chunk (no Groq required).

Usage: python tools/demo_local_generate.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retriever import retrieve_public_chunks


def main():
    query = "Which section defines theft?"
    print("Demo query:", query)

    hits = retrieve_public_chunks(query, index_root="indexes", top_k=5)
    if not hits:
        print("No retrieval hits found.")
        return 1

    top = hits[0]
    src = top.get("source_doc", "unknown source")
    cid = top.get("chunk_id", "?")
    text = top.get("text", "(no text available)")

    print(f"\nTop hit: {cid} — {src}\n")
    snippet = text.strip().replace("\n", " ")[:1000]
    print("--- Extractive Answer (local) ---\n")
    print(snippet)
    print("\n--- Citation ---")
    print(f"Source: {src} (chunk: {cid})")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
