"""
Module: ingest_public
Purpose: Orchestrates the full ingestion pipeline for all public law PDFs.
Inputs: PDF files in /data/public/.
Outputs: FAISS index + chunks.pkl + bm25.pkl saved to /indexes/public/.
Dependencies: ingestion/*, build_bm25
"""
