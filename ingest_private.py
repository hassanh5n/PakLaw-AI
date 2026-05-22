"""
Module: ingest_private
Purpose: Orchestrates the ingestion pipeline for a single firm's PDF upload.
Inputs: PDF file path, firm_id, access_level.
Outputs: Firm FAISS index + chunks.pkl + bm25.pkl saved to /indexes/firms/{firm_id}/.
Dependencies: ingestion/*, build_bm25
"""
