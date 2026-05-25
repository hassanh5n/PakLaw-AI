# PakLaw AI Task Sheet

Track progress by marking each task: `[ ]` Not started, `[~]` In progress, `[x]` Done.

## Phase 1 - Environment & Data Setup

| ID | Task | File / Output | Status |
|---|---|---|---|
| T1.1 | Create project folder structure | `/` | `[ ]` |
| T1.2 | Install all dependencies; confirm imports | `requirements.txt` | `[ ]` |
| T1.3 | Download all public law PDFs | `data/public/*.pdf` | `[ ]` |
| T1.4 | Verify PDFs are text-extractable | Notes / checklist | `[ ]` |

## Phase 2 - Public Ingestion

| ID | Task | File / Output | Status |
|---|---|---|---|
| T2.1 | PDF text extractor with PyMuPDF | `ingestion/extractor.py` | `[ ]` |
| T2.2 | Text cleaner | `ingestion/cleaner.py` | `[ ]` |
| T2.3 | Chunker | `ingestion/chunker.py` | `[ ]` |
| T2.4 | Metadata tagger | `ingestion/tagger.py` | `[ ]` |
| T2.5 | FAISS index builder | `ingestion/index_builder.py` | `[ ]` |
| T2.6 | BM25 index builder | `build_bm25.py` | `[ ]` |
| T2.7 | Run full public ingestion | `indexes/public/` | `[ ]` |

## Phase 3 - Private Vault

| ID | Task | File / Output | Status |
|---|---|---|---|
| T3.1 | Parameterize ingestion for firm context | `ingest_private.py` | `[ ]` |
| T3.2 | Add firm metadata fields | `ingest_private.py` | `[ ]` |
| T3.3 | Save firm indexes to isolated directory | `indexes/firms/{firm_id}/` | `[ ]` |
| T3.4 | Test firm isolation | Manual test log | `[ ]` |

## Phase 4 - Retrieval

| ID | Task | File / Output | Status |
|---|---|---|---|
| T4.1 | FAISS search function | `retriever.py` | `[ ]` |
| T4.2 | BM25 search function | `retriever.py` | `[ ]` |
| T4.3 | Merge + deduplication | `retriever.py` | `[ ]` |
| T4.4 | JSON-based query expander | `query_expander.py` | `[ ]` |
| T4.5 | Connect query variants to hybrid retrieval | `retriever.py` | `[ ]` |
| T4.6 | Firm and role filter | `retriever.py` | `[ ]` |
| T4.7 | Cross-encoder reranker | `retriever.py` | `[ ]` |

## Phase 5 - Generation

| ID | Task | File / Output | Status |
|---|---|---|---|
| T5.1 | Generator using Groq `llama-3.1-8b-instant` | `generator.py` | `[ ]` |
| T5.2 | Write and lock system prompt | `prompts.py` | `[ ]` |
| T5.3 | Test 20 questions end-to-end | `tests/q_and_a_log.md` | `[ ]` |
| T5.4 | Iterate on prompt if needed | `prompts.py` | `[ ]` |

## Phase 6 - Access Control

| ID | Task | File / Output | Status |
|---|---|---|---|
| T6.1 | User store with `public`, `user`, `admin` roles | `access_control.py` | `[ ]` |
| T6.2 | Login check + role assignment | `access_control.py` | `[ ]` |
| T6.3 | Query router to index paths | `access_control.py` | `[ ]` |
| T6.4 | Cross-firm isolation test | Manual test log | `[ ]` |

## Phase 7 - Streamlit UI

| ID | Task | File / Output | Status |
|---|---|---|---|
| T7.1 | 3-tab layout + sidebar | `app.py` | `[ ]` |
| T7.2 | Public Law Search | `app.py` | `[ ]` |
| T7.3 | Firm Vault | `app.py` | `[ ]` |
| T7.4 | Combined Search (login required) | `app.py` | `[ ]` |
| T7.5 | Sidebar user info and logout | `app.py` | `[ ]` |
| T7.6 | Full user flow test | Manual test log | `[ ]` |
| T7.7 | Source labels on every chunk | `app.py` | `[ ]` |

## Phase 8 - Evaluation

| ID | Task | File / Output | Status |
|---|---|---|---|
| T8.1 | Write 25-30 test questions | `eval/test_questions.md` | `[ ]` |
| T8.2 | Annotate ground-truth sections | `eval/test_questions.md` | `[ ]` |
| T8.3 | Run PakLaw AI retrieval | `eval/results_paklaw.md` | `[ ]` |
| T8.4 | Run BM25 baseline | `eval/results_baseline.md` | `[ ]` |
| T8.5 | Compute Precision@K | `eval/metrics.md` | `[ ]` |
| T8.6 | Compute MRR | `eval/metrics.md` | `[ ]` |
| T8.7 | Build comparison table | `eval/metrics.md` | `[ ]` |

## Phase 9 - Documentation & Cleanup

| ID | Task | File / Output | Status |
|---|---|---|---|
| T9.1 | File-level docstrings | All `.py` files | `[ ]` |
| T9.2 | Function-level docstrings | All functions | `[ ]` |
| T9.3 | Key algorithm comments | All `.py` files | `[ ]` |
| T9.4 | Write project report | `report/report.md` | `[ ]` |
| T9.5 | Include metrics and architecture | `report/report.md` | `[ ]` |
| T9.6 | Prepare demo queries | `demo/demo_script.md` | `[ ]` |
