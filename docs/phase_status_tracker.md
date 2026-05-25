# PakLaw AI Phase Status Tracker

This file records what is actually implemented in the workspace, based on the current code and project docs.

## Verified Status

| Phase | Status | Verified evidence | Notes |
|---|---|---|---|
| Phase 1 - Environment & Data Setup | Verified | `data/public/` contains 8 PDFs; `requirements.txt` is present; `tools/project_readiness.py` reports readiness gaps | `bcrypt` is a required auth dependency. |
| Phase 2 - Ingestion Pipeline (Public Corpus) | Implemented | `ingestion/extractor.py`, `ingestion/cleaner.py`, `ingestion/chunker.py`, `ingestion/tagger.py`, `ingestion/index_builder.py`, `build_bm25.py`, `ingest_public.py` | `ingestion/index_builder.py` loads the transformer embedding model directly. |
| Phase 3 - Ingestion Pipeline (Private Vault) | Partially implemented | `ingest_private.py` exists and reuses the ingestion pipeline | Firm indexes are persisted under `indexes/firms/{firm_id}/` after upload or manual ingestion. |
| Phase 4 - Retrieval Engine | Implemented | `query_expander.py` and `retriever.py` contain query expansion, hybrid FAISS/BM25 retrieval, firm filtering, and cross-encoder reranking | Retrieval depends on built index files under `indexes/`. |
| Phase 5 - LLM Generation | Implemented | `prompts.py` contains the fixed legal system prompt and user-prompt builder; `generator.py` calls Groq | Generation uses one model: `llama-3.1-8b-instant`. |
| Phase 6 - Access Control | Implemented | `access_control.py` provides SQLite user storage, bcrypt password hashing, authentication, and role/index routing helpers | Roles are simplified to `public`, `user`, and `admin`. |
| Phase 7 - UI | Implemented | `app.py` provides public search, firm vault login/upload/search, login-required combined search, and a logged-in sidebar | Uploads are admin-only and saved under `data/firms/{firm_id}/` before ingestion. |
| Phase 8 - Evaluation | Partially implemented | `eval/test_questions.md`, `eval/results_paklaw.md`, `eval/results_baseline.md`, `eval/metrics.md`, and `tools/evaluate_retrieval.py` provide the test set, result templates, scoring worksheet, and runner | Actual retrieval runs and filled scores still need to be collected. |
| Phase 9 - Docs & Cleanup | Partially implemented | `report/report.md`, `demo/demo_script.md`, and `tests/q_and_a_log.md` provide the report draft, demo walkthrough, and Q&A logging scaffold | Final filled evaluation outputs are still outstanding. |
| Phase 10 - Packaging & Operational Readiness | Implemented | `tools/project_readiness.py` reports missing artifacts and dependencies | This phase makes the handoff state explicit. |

## Verified File Notes

- `ingestion/extractor.py` extracts text with PyMuPDF and filters non-text pages.
- `ingestion/cleaner.py` removes common headers, footers, page numbers, and OCR noise.
- `ingestion/chunker.py` uses `RecursiveCharacterTextSplitter` with a fixed 400/100 configuration.
- `ingestion/tagger.py` attaches metadata such as `source_doc`, `law_domain`, `section_hint`, `firm_id`, `access_level`, and `chunk_id`.
- `ingestion/index_builder.py` builds a FAISS `IndexFlatIP`, saves chunk metadata, and loads `sentence-transformers/all-MiniLM-L6-v2` directly.
- `build_bm25.py` builds and persists a BM25 index from the same chunk set.
- `ingest_public.py` orchestrates public ingestion from extraction through FAISS and BM25 index creation.
- `ingest_private.py` appends firm chunks and rebuilds firm-specific FAISS and BM25 indexes.
- `query_expander.py` asks Groq for JSON query expansions and returns the original query if expansion fails.
- `retriever.py` loads public or firm indexes, runs FAISS and BM25 over query variants, deduplicates, filters by firm access, and reranks with a cross-encoder.
- `retriever.py` also exposes a BM25-only baseline path so evaluation can compare the hybrid pipeline against keyword search.
- `prompts.py` locks the legal system prompt and formats retrieved chunks into a grounded user prompt.
- `generator.py` sends the prompt to Groq's `llama-3.1-8b-instant` model and raises an error if generation cannot complete.
- `access_control.py` manages a SQLite user store, bcrypt password hashing and verification, user lookup, three-role routing, and demo account seeding.
- `app.py` provides a Streamlit UI with three tabs, login/logout handling, admin uploads, public search, firm search, combined search, and a sidebar showing the active corpus.
- `demo/demo_script.md` provides a live demo walkthrough for public search, firm vault search, combined search, and access control checks.
- `tests/q_and_a_log.md` provides a 20-question generation test log scaffold.
- `tools/project_readiness.py` reports missing artifacts and dependencies so the plan can be checked against the actual workspace state.
- `tools/evaluate_retrieval.py` can regenerate the PakLaw and BM25 retrieval logs plus summary metrics once the question bank is annotated.

## Overall Conclusion

The repository now has ingestion, retrieval, generation, access control, and UI implemented. Evaluation is scaffolded, but final run outputs still need to be completed.
