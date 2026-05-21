# PakLaw AI — Task Sheet

> Track progress by marking each task: `[ ]` Not started · `[~]` In progress · `[x]` Done

---

## Phase 1 — Environment & Data Setup

| ID | Task | File / Output | Status |
|----|------|---------------|--------|
| T1.1 | Create project folder structure | `/` (root layout) | `[ ]` |
| T1.2 | Install all dependencies; confirm imports | `requirements.txt` | `[ ]` |
| T1.3 | Download all 8 public law PDFs | `/data/public/*.pdf` | `[ ]` |
| T1.4 | Verify PDFs are text-extractable; flag scanned ones | Notes / checklist | `[ ]` |

---

## Phase 2 — Ingestion Pipeline (Public Corpus)

| ID | Task | File / Output | Status |
|----|------|---------------|--------|
| T2.1 | PDF text extractor with PyMuPDF | `ingestion/extractor.py` | `[ ]` |
| T2.2 | Text cleaner (headers, footers, noise) | `ingestion/cleaner.py` | `[ ]` |
| T2.3 | Chunker (300–400 chars, 100 overlap) | `ingestion/chunker.py` | `[ ]` |
| T2.4 | Metadata tagger per chunk | `ingestion/tagger.py` | `[ ]` |
| T2.5 | FAISS index builder; save `.faiss` + `chunks.pkl` | `ingestion/index_builder.py` | `[ ]` |
| T2.6 | BM25 index builder; save `bm25.pkl` | `build_bm25.py` | `[ ]` |
| T2.7 | Run full ingestion on all public PDFs | `/indexes/public/` | `[ ]` |

---

## Phase 3 — Ingestion Pipeline (Private Vault)

| ID | Task | File / Output | Status |
|----|------|---------------|--------|
| T3.1 | Parameterize ingestion pipeline for firm context | `ingest_private.py` | `[ ]` |
| T3.2 | Add firm-specific metadata fields | `ingest_private.py` | `[ ]` |
| T3.3 | Save firm indexes to isolated directory | `/indexes/firms/{firm_id}/` | `[ ]` |
| T3.4 | Test: firm doc stays isolated from public index | Manual test log | `[ ]` |

---

## Phase 4 — Retrieval Engine

| ID | Task | File / Output | Status |
|----|------|---------------|--------|
| T4.1 | FAISS search function (top-15) | `retriever.py` | `[ ]` |
| T4.2 | BM25 search function (top-15) | `retriever.py` | `[ ]` |
| T4.3 | Merge + deduplication function | `retriever.py` | `[ ]` |
| T4.4 | Query expander (2 alternate phrasings via Groq) | `query_expander.py` | `[ ]` |
| T4.5 | Connect: run 3 queries through hybrid retriever | `retriever.py` | `[ ]` |
| T4.6 | Metadata filter (role-based access) | `retriever.py` | `[ ]` |
| T4.7 | Cross-encoder re-ranker integration (top-10 out) | `retriever.py` | `[ ]` |

---

## Phase 5 — LLM Generation

| ID | Task | File / Output | Status |
|----|------|---------------|--------|
| T5.1 | Generator: query + chunks → Groq call → answer | `generator.py` | `[ ]` |
| T5.2 | Write and lock system prompt | `prompts.py` | `[ ]` |
| T5.3 | Test 20 questions end-to-end; record results | `tests/q_and_a_log.md` | `[ ]` |
| T5.4 | Iterate on prompt if needed (no architecture changes) | `prompts.py` | `[ ]` |

---

## Phase 6 — Access Control

| ID | Task | File / Output | Status |
|----|------|---------------|--------|
| T6.1 | User store (SQLite or dict): username, role, firm_id | `access_control.py` | `[ ]` |
| T6.2 | Login check + role assignment | `access_control.py` | `[ ]` |
| T6.3 | Query router: role → index(es) | `access_control.py` | `[ ]` |
| T6.4 | Cross-firm isolation test (zero leakage) | Manual test log | `[ ]` |

---

## Phase 7 — Streamlit UI

| ID | Task | File / Output | Status |
|----|------|---------------|--------|
| T7.1 | Scaffold: 3-tab layout + sidebar | `app.py` | `[ ]` |
| T7.2 | Tab 1 — Public Law Search | `app.py` | `[ ]` |
| T7.3 | Tab 2 — Firm Vault (login, uploader, search) | `app.py` | `[ ]` |
| T7.4 | Tab 3 — Combined Search (partner only) | `app.py` | `[ ]` |
| T7.5 | Sidebar: user info, active corpus, logout | `app.py` | `[ ]` |
| T7.6 | Full user flow test: login → upload → search → logout | Manual test log | `[ ]` |
| T7.7 | Bug fixes; source labels on every chunk | `app.py` | `[ ]` |

---

## Phase 8 — Evaluation

| ID | Task | File / Output | Status |
|----|------|---------------|--------|
| T8.1 | Write 25–30 test questions (all law domains) | `eval/test_questions.md` | `[ ]` |
| T8.2 | Annotate ground-truth sections for each question | `eval/test_questions.md` | `[ ]` |
| T8.3 | Run questions through PakLaw AI; record top-10 | `eval/results_paklaw.md` | `[ ]` |
| T8.4 | Run questions through BM25-only baseline | `eval/results_baseline.md` | `[ ]` |
| T8.5 | Compute Precision@K (K = 1, 5, 10) | `eval/metrics.md` | `[ ]` |
| T8.6 | Compute MRR | `eval/metrics.md` | `[ ]` |
| T8.7 | Build improvement comparison table | `eval/metrics.md` | `[ ]` |

---

## Phase 9 — Documentation & Cleanup

| ID | Task | File / Output | Status |
|----|------|---------------|--------|
| T9.1 | File-level docstring on every module | All `.py` files | `[ ]` |
| T9.2 | Function-level docstring on every function | All `.py` files | `[ ]` |
| T9.3 | Inline comments at key algorithmic steps | All `.py` files | `[ ]` |
| T9.4 | Write project report | `report/report.pdf` | `[ ]` |
| T9.5 | Include improvement table + architecture description | `report/report.pdf` | `[ ]` |
| T9.6 | Prepare demo: 3–4 live queries | `demo/demo_script.md` | `[ ]` |

---

## Summary Counts

| Phase | Total Tasks | Done | Remaining |
|-------|-------------|------|-----------|
| 1 — Setup | 4 | 0 | 4 |
| 2 — Public Ingestion | 7 | 0 | 7 |
| 3 — Private Ingestion | 4 | 0 | 4 |
| 4 — Retrieval | 7 | 0 | 7 |
| 5 — Generation | 4 | 0 | 4 |
| 6 — Access Control | 4 | 0 | 4 |
| 7 — UI | 7 | 0 | 7 |
| 8 — Evaluation | 7 | 0 | 7 |
| 9 — Docs | 6 | 0 | 6 |
| **Total** | **50** | **0** | **50** |
