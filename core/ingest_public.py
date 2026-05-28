"""
Module: ingest_public
Purpose: Orchestrates the full ingestion pipeline for all public law PDFs.
Inputs: PDF files in /data/public/.
Outputs: FAISS index + chunks.pkl + bm25.pkl saved to /indexes/public/.
Dependencies: ingestion/*, build_bm25
"""

import os
from tqdm import tqdm

from ingestion.extractor import extract_text_from_pdf, is_text_extractable
from ingestion.cleaner import clean_text
from ingestion.chunker import chunk_text
from ingestion.tagger import tag_chunks
from ingestion.index_builder import build_faiss_index
from build_bm25 import build_bm25_index

DATA_DIR   = "data/public"
OUTPUT_DIR = "indexes/public"
INDEX_NAME = "pakistan_law_public"


def ingest_all_public_pdfs() -> None:
    pdf_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print(f"No PDF files found in '{DATA_DIR}'. Add your law PDFs and re-run.")
        return

    print(f"Found {len(pdf_files)} PDF(s) in {DATA_DIR}/\n")

    all_chunks = []

    for filename in tqdm(pdf_files, desc="Ingesting PDFs"):
        pdf_path = os.path.join(DATA_DIR, filename)

        # T1.4: Flag scanned (non-text-extractable) PDFs
        if not is_text_extractable(pdf_path):
            print(f"  [SKIP] {filename} — appears to be scanned (no extractable text)")
            continue

        # Step 1: Extract raw text page by page
        pages = extract_text_from_pdf(pdf_path)

        # Step 2: Clean each page, then join into one document string
        full_text = "\n\n".join(clean_text(text) for _, text in pages)

        # Step 3: Split into overlapping chunks (300–400 chars, 100 overlap)
        chunks = chunk_text(full_text)

        if not chunks:
            print(f"  [WARN] {filename} — produced 0 chunks after cleaning")
            continue

        # Step 4: Attach metadata to every chunk
        tagged = tag_chunks(
            chunk_texts=chunks,
            source_doc=filename,
            firm_id=None,          # Public law has no firm association
            access_level="public",
        )

        all_chunks.extend(tagged)
        print(f"  [OK]   {filename} → {len(tagged)} chunks")

    if not all_chunks:
        print("No chunks produced. Check your PDFs.")
        return

    print(f"\nTotal chunks: {len(all_chunks)}")

    # Step 5: Build FAISS index (embeddings + vectors)
    build_faiss_index(all_chunks, OUTPUT_DIR, INDEX_NAME)

    # Step 6: Build BM25 index from the same chunks.pkl
    chunks_pkl = os.path.join(OUTPUT_DIR, f"{INDEX_NAME}_chunks.pkl")
    build_bm25_index(chunks_pkl, OUTPUT_DIR, INDEX_NAME)

    print("\nIngestion complete. Indexes saved to:", OUTPUT_DIR)


if __name__ == "__main__":
    ingest_all_public_pdfs()