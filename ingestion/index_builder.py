"""
Module: index_builder
Purpose: Embeds chunks and builds a FAISS IndexFlatIP; saves .faiss and chunks.pkl to disk.
Inputs: List of tagged chunk dicts, output directory path.
Outputs: Saved .faiss index file and chunks.pkl file.
Dependencies: sentence-transformers, faiss-cpu, numpy, pickle
"""

import os
import pickle
import json

import faiss
import numpy as np
from vector_backends import EMBEDDING_DIM, get_embedding_backend


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

    # Build FAISS index — IndexFlatIP performs exact inner-product search
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(embeddings)

    # Save FAISS index
    faiss_path = os.path.join(output_dir, f"{index_name}.faiss")
    faiss.write_index(index, faiss_path)
    print(f"Saved FAISS index → {faiss_path}  ({index.ntotal} vectors)")

    # Save the original chunk dicts alongside the index so we can retrieve
    # metadata (source_doc, section_hint, etc.) from search results
    chunks_path = os.path.join(output_dir, f"{index_name}_chunks.pkl")
    with open(chunks_path, "wb") as f:
        pickle.dump(chunks, f)
    print(f"Saved chunks     → {chunks_path}  ({len(chunks)} chunks)")

    backend_name = getattr(model, "backend_name", model.__class__.__name__)
    backend_path = os.path.join(output_dir, f"{index_name}_backend.json")
    with open(backend_path, "w", encoding="utf-8") as f:
        json.dump({"embedding_backend": backend_name}, f, indent=2)
    print(f"Saved backend    → {backend_path}  ({backend_name})")
