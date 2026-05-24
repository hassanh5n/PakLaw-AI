# PakLaw AI — Phase Status Tracker

This file records what is actually implemented in the workspace, based on the current code and project docs.

## Verified Status

| Phase | Status | Verified evidence | Notes |
|---|---|---|---|
| Phase 1 — Environment & Data Setup | Verified with one gap | `data/public/` contains 8 PDFs; `requirements.txt` is present; `tools/project_readiness.py` reports the remaining missing artifacts | `bcrypt` is missing from the active Python environment, but `access_control.py` now falls back to PBKDF2; the public corpus indexes were missing at the start of this pass and are being rebuilt. |
| Phase 2 — Ingestion Pipeline (Public Corpus) | Implemented | `ingestion/extractor.py`, `ingestion/cleaner.py`, `ingestion/chunker.py`, `ingestion/tagger.py`, `ingestion/index_builder.py`, `build_bm25.py`, `ingest_public.py`, `vector_backends.py` | `ingestion/chunker.py` now includes a local fallback splitter, and `vector_backends.py` adds offline-safe embedding/reranking fallbacks so ingestion can still run when transformer models are unavailable. |
| Phase 3 — Ingestion Pipeline (Private Vault) | Partially implemented | `ingest_private.py` exists and reuses the ingestion pipeline | The private ingest flow is present, but I did not verify any persisted firm indexes or upload flow. |
| Phase 4 — Retrieval Engine | Implemented | `query_expander.py` and `retriever.py` now contain working query expansion, hybrid FAISS/BM25 retrieval, access filtering, and cross-encoder reranking | Retrieval still depends on the presence of built index files under `indexes/`. |
| Phase 5 — LLM Generation | Implemented | `prompts.py` now contains the fixed legal system prompt and user-prompt builder; `generator.py` now calls Groq to produce grounded answers | `tests/q_and_a_log.md` remains a placeholder until manual end-to-end testing is logged. |
| Phase 6 — Access Control | Implemented | `access_control.py` now provides SQLite user storage, bcrypt password hashing, authentication, and role/index routing helpers | The UI still needs to call these helpers to expose login and logout flows. |
| Phase 7 — UI | Implemented | `app.py` now provides public search, firm vault login/upload/search, partner-only combined search, and a logged-in sidebar | Uploads are saved under `data/firms/{firm_id}/` before ingestion. |
| Phase 8 — Evaluation | Partially implemented | `eval/test_questions.md`, `eval/results_paklaw.md`, `eval/results_baseline.md`, `eval/metrics.md`, and `tools/evaluate_retrieval.py` now provide the test set, logging templates, scoring worksheet, and a repeatable runner | Actual retrieval runs and filled scores still need to be collected. |
| Phase 9 — Docs & Cleanup | Partially implemented | `report/report.md`, `report/build_report_pdf.py`, `report/report.pdf`, `demo/demo_script.md`, and `tests/q_and_a_log.md` now provide the report draft, PDF build step, demo walkthrough, and Q&A logging scaffold | Final filled evaluation outputs are still outstanding. |
| Phase 10 — Packaging & Operational Readiness | Implemented | `tools/project_readiness.py` reports missing artifacts and optional dependencies | This phase was added to make the handoff state explicit instead of implied. |

## Verified File Notes

- `ingestion/extractor.py` extracts text with PyMuPDF and filters non-text pages.
- `ingestion/cleaner.py` removes common headers, footers, page numbers, and OCR noise.
- `ingestion/chunker.py` uses `RecursiveCharacterTextSplitter` with a fixed 400/100 configuration.
- `ingestion/tagger.py` attaches metadata such as `source_doc`, `law_domain`, `section_hint`, `firm_id`, `access_level`, and `chunk_id`.
- `ingestion/index_builder.py` builds a FAISS `IndexFlatIP` and saves the chunk metadata.
- `ingestion/index_builder.py` now uses a shared backend that falls back to deterministic hash embeddings when transformer embeddings cannot be loaded.
- `build_bm25.py` builds and persists a BM25 index from the same chunk set.
- `ingest_public.py` orchestrates public ingestion from extraction through FAISS and BM25 index creation.
- `ingest_private.py` appends firm chunks and rebuilds firm-specific FAISS and BM25 indexes.
- `query_expander.py` expands a query into three variants, using Groq when available and a heuristic fallback otherwise.
- `retriever.py` loads public or firm indexes, runs FAISS and BM25 over all query variants, deduplicates, filters by access, and reranks with a cross-encoder.
- `retriever.py` also exposes a BM25-only baseline path so evaluation can compare the hybrid pipeline against keyword search.
- `vector_backends.py` provides the shared embedding and reranking backends used by both indexing and retrieval.
- `prompts.py` locks the legal system prompt and formats retrieved chunks into a grounded user prompt.
- `generator.py` sends the prompt to Groq and returns the model answer or the exact no-found response when no chunks are retrieved.
- `access_control.py` now manages a SQLite user store, password hashing and verification, user lookup, role-to-index routing, and demo account seeding.
- `access_control.py` also falls back to PBKDF2 when `bcrypt` is unavailable in the active Python environment.
- `app.py` now provides a Streamlit UI with three tabs, login/logout handling, firm uploads, public search, firm search, combined search, and a sidebar showing the active corpus.
- `ingestion/chunker.py` now falls back to a local recursive splitter when `langchain_text_splitters` is unavailable.
- `report/report.md` provides a report draft covering introduction, architecture, implementation, evaluation plan, and conclusion.
- `report/build_report_pdf.py` generates the compiled `report/report.pdf` artifact from the markdown draft.
- `demo/demo_script.md` provides a live demo walkthrough for public search, firm vault search, combined search, and access control checks.
- `tests/q_and_a_log.md` provides a 20-question generation test log scaffold.
- `tools/project_readiness.py` reports missing artifacts and optional dependencies so the plan can be checked against the actual workspace state.
- `tools/evaluate_retrieval.py` can regenerate the PakLaw and BM25 retrieval logs plus summary metrics once the question bank is annotated.

## Overall Conclusion

The repository now has ingestion, retrieval, generation, access control, and UI implemented. Evaluation is scaffolded, and the report/demo docs are drafted, but the compiled PDF report and final run outputs still need to be completed.
