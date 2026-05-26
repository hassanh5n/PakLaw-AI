"""
Module: ingest_private
Purpose: Orchestrates the ingestion pipeline for a single firm's PDF upload.
Inputs: PDF file path, firm_id, access_level.
Outputs: Firm FAISS index + chunks.pkl + bm25.pkl saved to /indexes/firms/{firm_id}/.
Dependencies: ingestion/*, build_bm25
"""

import os

from ingestion.extractor import extract_text_from_pdf, is_text_extractable
from ingestion.cleaner import clean_text
from ingestion.chunker import chunk_text
from ingestion.tagger import tag_chunks
from ingestion.index_builder import build_faiss_index
from build_bm25 import build_bm25_index


def ingest_firm_pdf(
    pdf_path: str,
    firm_id: str,
    access_level: str = "firm",
) -> None:
    import pickle

    output_dir = os.path.join("indexes", "firms", firm_id)
    index_name = f"firm_{firm_id}"
    chunks_pkl_path = os.path.join(output_dir, f"{index_name}_chunks.pkl")

    filename = os.path.basename(pdf_path)

    if not is_text_extractable(pdf_path):
        raise ValueError(f"{filename} appears to be a scanned PDF — text extraction failed.")

    # --- Extract → Clean → Chunk → Tag ---
    pages = extract_text_from_pdf(pdf_path)
    full_text = "\n\n".join(clean_text(text) for _, text in pages)
    chunks = chunk_text(full_text)

    if not chunks:
        raise ValueError(f"{filename} produced 0 chunks after processing.")

    new_chunks = tag_chunks(
        chunk_texts=chunks,
        source_doc=filename,
        firm_id=firm_id,
        access_level=access_level,
    )

    # Load existing firm chunks if the index already exists, then append.
    # This preserves previously ingested documents when adding a new one.
    if os.path.exists(chunks_pkl_path):
        with open(chunks_pkl_path, "rb") as f:
            existing_chunks = pickle.load(f)
        all_chunks = existing_chunks + new_chunks
        print(f"Appending to existing firm index ({len(existing_chunks)} existing chunks)")
    else:
        all_chunks = new_chunks

    print(f"New chunks from {filename}: {len(new_chunks)}")
    print(f"Total firm chunks after merge: {len(all_chunks)}")

    # Rebuild FAISS index with all chunks (existing + new)
    build_faiss_index(all_chunks, output_dir, index_name)

    # Rebuild BM25 index from the updated chunks.pkl
    build_bm25_index(chunks_pkl_path, output_dir, index_name)

    print(f"Firm index updated → {output_dir}/")


def ingest_firm_pdfs_batch(
    pdf_paths: list[str],
    firm_id: str,
    access_level: str = "firm",
) -> None:
    import pickle

    output_dir = os.path.join("indexes", "firms", firm_id)
    index_name = f"firm_{firm_id}"
    chunks_pkl_path = os.path.join(output_dir, f"{index_name}_chunks.pkl")

    # Load existing chunks if index already exists
    if os.path.exists(chunks_pkl_path):
        with open(chunks_pkl_path, "rb") as f:
            all_chunks = pickle.load(f)
        print(f"Loaded {len(all_chunks)} existing chunks")
    else:
        all_chunks = []

    # Process each PDF and accumulate chunks — index built only once after
    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)

        if not is_text_extractable(pdf_path):
            print(f"[SKIP] {filename} — scanned PDF, skipping")
            continue

        pages = extract_text_from_pdf(pdf_path)
        full_text = "\n\n".join(clean_text(text) for _, text in pages)
        chunks = chunk_text(full_text)

        if not chunks:
            print(f"[WARN] {filename} — 0 chunks produced")
            continue

        new_chunks = tag_chunks(
            chunk_texts=chunks,
            source_doc=filename,
            firm_id=firm_id,
            access_level=access_level,
        )
        all_chunks.extend(new_chunks)
        print(f"[OK] {filename} → {len(new_chunks)} chunks")

    if not all_chunks:
        raise ValueError("No chunks produced from any of the uploaded PDFs.")

    print(f"Total chunks after batch: {len(all_chunks)}")

    # Single index rebuild for all documents combined
    build_faiss_index(all_chunks, output_dir, index_name)
    build_bm25_index(chunks_pkl_path, output_dir, index_name)
    print(f"Firm index rebuilt → {output_dir}/")