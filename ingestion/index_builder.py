"""
Module: index_builder
Purpose: Embeds chunks and builds a FAISS IndexFlatIP; saves .faiss and chunks.pkl to disk.
Inputs: List of tagged chunk dicts, output directory path.
Outputs: Saved .faiss index file and chunks.pkl file.
Dependencies: sentence-transformers, faiss-cpu, numpy, pickle
"""

import os
import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Load the embedding model once at module level to avoid reloading on every call
_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
_EMBEDDING_DIM = 384  # Fixed output dimension for all-MiniLM-L6-v2


def build_faiss_index(
    chunks: list[dict],
    output_dir: str,
    index_name: str,
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    texts = [chunk["text"] for chunk in chunks]

    print(f"Embedding {len(texts)} chunks...")
    # Encode in batches; normalize=True ensures vectors are unit-length,
    # which makes IndexFlatIP equivalent to cosine similarity
    embeddings = _MODEL.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    embeddings = np.array(embeddings, dtype="float32")

    # Build FAISS index — IndexFlatIP performs exact inner-product search
    index = faiss.IndexFlatIP(_EMBEDDING_DIM)
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
