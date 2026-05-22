"""
Module: build_bm25
Purpose: Builds a BM25 index from existing chunks.pkl and saves bm25.pkl to disk.
Inputs: Path to chunks.pkl file, output directory path.
Outputs: Saved bm25.pkl file.
Dependencies: rank-bm25, pickle
"""

import os
import pickle

from rank_bm25 import BM25Okapi


def build_bm25_index(chunks_pkl_path: str, output_dir: str, index_name: str) -> None:
    # Load chunk dicts produced by index_builder.py
    with open(chunks_pkl_path, "rb") as f:
        chunks = pickle.load(f)

    # Tokenize each chunk: lowercase and split on whitespace.
    # BM25 matches exact tokens, so consistent tokenization matters.
    tokenized = [chunk["text"].lower().split() for chunk in chunks]

    bm25 = BM25Okapi(tokenized)

    os.makedirs(output_dir, exist_ok=True)
    bm25_path = os.path.join(output_dir, f"{index_name}_bm25.pkl")
    with open(bm25_path, "wb") as f:
        pickle.dump(bm25, f)

    print(f"Saved BM25 index → {bm25_path}  ({len(chunks)} documents)")


if __name__ == "__main__":
    # Quick CLI usage: python build_bm25.py
    build_bm25_index(
        chunks_pkl_path="indexes/public/pakistan_law_public_chunks.pkl",
        output_dir="indexes/public",
        index_name="pakistan_law_public",
    )
