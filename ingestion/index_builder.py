"""
Module: index_builder
Purpose: Embeds chunks and builds a FAISS IndexFlatIP; saves .faiss and chunks.pkl to disk.
Inputs: List of tagged chunk dicts, output directory path.
Outputs: Saved .faiss index file and chunks.pkl file.
Dependencies: sentence-transformers, faiss-cpu, numpy, pickle
"""

import os
import pickle
from functools import lru_cache

import faiss
import numpy as np


EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_backend():
    """Load the transformer embedding model required for FAISS indexing."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required for indexing. Install requirements.txt before running ingestion."
        ) from exc

    try:
        return SentenceTransformer(EMBEDDING_MODEL_NAME)
    except Exception as exc:
        raise RuntimeError(f"Failed to load embedding model {EMBEDDING_MODEL_NAME}: {exc}") from exc


def _normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    """Normalize vectors so IndexFlatIP behaves like cosine similarity."""
    lengths = np.linalg.norm(embeddings, axis=1, keepdims=True)
    lengths[lengths == 0.0] = 1.0
    return embeddings / lengths


def build_faiss_index(
    chunks: list[dict],
    output_dir: str,
    index_name: str,
) -> None:
    """Embed chunks, build a FAISS inner-product index, and persist chunk metadata."""
    os.makedirs(output_dir, exist_ok=True)

    texts = [chunk["text"] for chunk in chunks]

    print(f"Embedding {len(texts)} chunks...")
    model = get_embedding_backend()

    try:
        embeddings = model.encode(texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    except TypeError:
        embeddings = model.encode(texts)

    embeddings = np.asarray(embeddings, dtype="float32")
    embeddings = _normalize_embeddings(embeddings)

    # IndexFlatIP performs exact inner-product search.
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss_path = os.path.join(output_dir, f"{index_name}.faiss")
    faiss.write_index(index, faiss_path)
    print(f"Saved FAISS index -> {faiss_path}  ({index.ntotal} vectors)")

    chunks_path = os.path.join(output_dir, f"{index_name}_chunks.pkl")
    with open(chunks_path, "wb") as f:
        pickle.dump(chunks, f)
    print(f"Saved chunks     -> {chunks_path}  ({len(chunks)} chunks)")
