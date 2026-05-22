"""
Module: retriever
Purpose: Full hybrid retrieval pipeline — FAISS + BM25 + query expansion + re-ranking + access filter.
Inputs: Query string, user role, firm_id, index paths.
Outputs: Top-10 ranked, access-filtered chunk dicts.
Dependencies: faiss-cpu, rank-bm25, sentence-transformers, query_expander
"""
