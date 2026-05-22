"""
Module: index_builder
Purpose: Embeds chunks and builds a FAISS IndexFlatIP; saves .faiss and chunks.pkl to disk.
Inputs: List of tagged chunk dicts, output directory path.
Outputs: Saved .faiss index file and chunks.pkl file.
Dependencies: sentence-transformers, faiss-cpu, numpy, pickle
"""
