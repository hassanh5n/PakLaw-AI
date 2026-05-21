# PakLaw AI — Implementation Plan

## Overview

PakLaw AI is a recall-critical, dual-layer legal retrieval system for Pakistani law. Every answer is grounded in retrieved text — no hallucination permitted. This plan is organized by logical build phases, each producing a testable deliverable before the next phase begins.

---

## Phase 1 — Environment & Data Setup

**Goal:** Working environment with all public law PDFs downloaded and folder structure confirmed.

### Tasks

- **T1.1** — Create project folder structure (see `guidelines.md` for exact layout)
- **T1.2** — Install all Python dependencies and confirm imports work
- **T1.3** — Download public law PDFs from `pakistancode.gov.pk` and `na.gov.pk`
  - Constitution of Pakistan 1973
  - Pakistan Penal Code (PPC)
  - Code of Criminal Procedure (CrPC)
  - Family Laws Ordinance
  - Contract Act 1872
  - Labour Laws
  - Tax Laws
  - Corporate Laws
- **T1.4** — Verify all PDFs are text-extractable (not scanned images); flag any that need OCR

**Exit Criteria:** All PDFs in `/data/public/`, environment `requirements.txt` installed with no errors.

---

## Phase 2 — Ingestion Pipeline (Public Corpus)

**Goal:** Functional `ingest_public.py` that processes raw PDFs into dual indexes.

### Tasks

- **T2.1** — Write PDF text extractor using PyMuPDF; test on 2-3 PDFs
- **T2.2** — Write text cleaner: strip headers, footers, page numbers, OCR noise
- **T2.3** — Write chunker using `LangChain RecursiveCharacterTextSplitter` (300–400 chars, 100 overlap)
- **T2.4** — Write metadata tagger per chunk:
  - `source_doc`, `law_domain`, `section_hint`, `firm_id` (null), `access_level` (public), `chunk_id`
- **T2.5** — Write FAISS index builder: embed chunks with `all-MiniLM-L6-v2`, build `IndexFlatIP`, save `.faiss` + `chunks.pkl`
- **T2.6** — Write `build_bm25.py`: tokenize same chunks, build BM25 object, save `bm25.pkl`
- **T2.7** — Run full ingestion on all public PDFs; confirm both index files saved to `/indexes/public/`

**Exit Criteria:** `pakistan_law_public.faiss`, `pakistan_law_public_chunks.pkl`, `pakistan_law_public_bm25.pkl` all saved and non-empty.

---

## Phase 3 — Ingestion Pipeline (Private Vault)

**Goal:** Functional `ingest_private.py` that handles firm-uploaded PDFs with isolation.

### Tasks

- **T3.1** — Reuse Phase 2 extractor/cleaner/chunker; parameterize for firm context
- **T3.2** — Add firm-specific metadata: `firm_id`, `access_level` (partner/associate)
- **T3.3** — Save firm indexes to `/indexes/firms/{firm_id}/` — completely isolated from public
- **T3.4** — Test: upload one sample firm PDF, confirm it appears **only** in that firm's index

**Exit Criteria:** Firm index created at correct path; searching public index does not return firm chunks.

---

## Phase 4 — Retrieval Engine

**Goal:** Functional `retriever.py` implementing full hybrid recall pipeline.

### Tasks

- **T4.1** — Write FAISS search function: embed query, search index, return top-15 with metadata
- **T4.2** — Write BM25 search function: tokenize query, search, return top-15 with metadata
- **T4.3** — Write merge + deduplication function: combine FAISS + BM25 results, dedupe by `chunk_id`
- **T4.4** — Write `query_expander.py`: call Groq API, generate 2 alternate phrasings, return list of 3 queries
- **T4.5** — Connect: run all 3 queries through hybrid retriever, merge all results (~25–30 unique chunks)
- **T4.6** — Write metadata filter: apply `firm_id` and `access_level` filter based on user role
- **T4.7** — Integrate cross-encoder re-ranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`): score each chunk against original query, select top-10

**Exit Criteria:** Given a query and a role, `retriever.py` returns top-10 ranked, access-filtered chunks in under 3 seconds.

---

## Phase 5 — LLM Generation

**Goal:** Functional `generator.py` producing grounded, cited answers.

### Tasks

- **T5.1** — Write `generator.py`: accepts query + top-10 chunks, constructs prompt, calls Groq API (`llama3-8b-8192`)
- **T5.2** — Write and lock in the system prompt (see `guidelines.md` for exact constraints)
- **T5.3** — Test 20 questions end-to-end; record which work, which produce weak/wrong answers
- **T5.4** — Iterate on prompt if needed; do not change architecture to fix prompt problems

**Exit Criteria:** 20-question test log saved; system cites article/section/doc for every answer; never fabricates.

---

## Phase 6 — Access Control

**Goal:** Functional `access_control.py` managing users, roles, and query routing.

### Tasks

- **T6.1** — Define user store (SQLite or dict): `username`, `password_hash`, `role`, `firm_id`
- **T6.2** — Write login check and role assignment function
- **T6.3** — Write query router: maps role → correct index(es) to search
  - `public` → public index only
  - `associate` → public + firm index (access_level ≤ associate)
  - `partner` → public + firm index (all access levels)
  - `admin` → full access + upload/delete permissions
- **T6.4** — Test cross-firm isolation: confirm Firm A user cannot retrieve Firm B chunks under any role

**Exit Criteria:** All four roles route correctly; cross-firm test passes with zero leakage.

---

## Phase 7 — Streamlit UI

**Goal:** Fully functional three-tab application connecting all backend components.

### Tasks

- **T7.1** — Scaffold Streamlit app with three tabs + sidebar
- **T7.2** — Build **Tab 1 — Public Law Search**: search bar → public retriever → generator → results with source sections
- **T7.3** — Build **Tab 2 — Firm Vault**: login panel → private retriever → generator → results with doc name + page reference; document uploader + library view
- **T7.4** — Build **Tab 3 — Combined Search** (partner only): combined retriever → generator → split results display (Public Law Sources | Firm Document Sources)
- **T7.5** — Build sidebar: logged-in user info, active corpus label, logout
- **T7.6** — End-to-end user flow test: login, upload, search, combine, logout
- **T7.7** — Fix UI bugs; ensure every retrieved chunk shows its source label

**Exit Criteria:** All three tabs functional; source labels visible on every chunk; no role can access unauthorized content through the UI.

---

## Phase 8 — Evaluation

**Goal:** Quantitative proof that PakLaw AI outperforms keyword-only baseline.

### Tasks

- **T8.1** — Write 25–30 test questions covering all law domains (constitutional, criminal, civil, family, private)
- **T8.2** — For each question, manually identify the ground-truth section/article that should be retrieved
- **T8.3** — Run all questions through PakLaw AI; record top-10 chunks returned
- **T8.4** — Run same questions through BM25-only baseline (no semantic, no re-ranking)
- **T8.5** — Compute **Precision@K** (K = 1, 5, 10) for both systems
- **T8.6** — Compute **MRR** (Mean Reciprocal Rank) for both systems
- **T8.7** — Build improvement comparison table: Baseline vs PakLaw AI

**Exit Criteria:** Improvement table complete; PakLaw AI shows measurable recall gain over BM25 baseline.

---

## Phase 9 — Documentation & Code Cleanup

**Goal:** Submission-ready codebase and report.

### Tasks

- **T9.1** — Add file-level docstring to every module
- **T9.2** — Add function-level docstring (inputs, outputs, purpose) to every function
- **T9.3** — Add inline comments at all key algorithmic steps (chunking logic, merge strategy, filter logic)
- **T9.4** — Write project report: Introduction, Related Work (LawPal), System Architecture, Implementation, Results, Conclusion
- **T9.5** — Include improvement table and architecture description in report
- **T9.6** — Prepare demo: 3–4 live queries covering public search, private vault search, and combined search

**Exit Criteria:** Every function documented; report complete; demo script ready.

---

## Dependency Order (Build Sequence)

```
T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9
              ↑
         (T3 can run in parallel with T4 after T2 is done)
```

T4 (retrieval) and T5 (generation) can be developed and tested independently before wiring into the UI in T7.
