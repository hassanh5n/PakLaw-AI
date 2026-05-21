# PakLaw AI — Implementation Guidelines

These guidelines are the source of truth for all implementation decisions. When in doubt, refer here before changing any design.

---

## 1. Core Principle — No Hallucination

> **Every answer must be grounded in retrieved text. The system must never generate from memory.**

This is non-negotiable. PakLaw AI is a legal system. Fabricated legal advice causes real harm. The LLM is a formatter and synthesizer, not a knowledge source.

---

## 2. Project Folder Structure

```
paklaw-ai/
├── data/
│   ├── public/              # Downloaded public law PDFs
│   └── firms/               # Firm-uploaded PDFs (subdir per firm)
│       └── {firm_id}/
├── indexes/
│   ├── public/              # Public FAISS + BM25 indexes
│   │   ├── pakistan_law_public.faiss
│   │   ├── pakistan_law_public_chunks.pkl
│   │   └── pakistan_law_public_bm25.pkl
│   └── firms/               # Firm indexes (one subdir per firm)
│       └── {firm_id}/
│           ├── firm_{id}.faiss
│           ├── firm_{id}_chunks.pkl
│           └── firm_{id}_bm25.pkl
├── ingestion/
│   ├── extractor.py
│   ├── cleaner.py
│   ├── chunker.py
│   ├── tagger.py
│   └── index_builder.py
├── ingest_public.py         # Orchestrates public ingestion
├── ingest_private.py        # Orchestrates private ingestion
├── build_bm25.py
├── retriever.py
├── query_expander.py
├── generator.py
├── prompts.py
├── access_control.py
├── app.py                   # Streamlit UI
├── eval/
│   ├── test_questions.md
│   ├── results_paklaw.md
│   ├── results_baseline.md
│   └── metrics.md
├── tests/
│   └── q_and_a_log.md
├── demo/
│   └── demo_script.md
├── report/
│   └── report.pdf
└── requirements.txt
```

---

## 3. Technology Stack (Fixed — Do Not Swap)

| Component | Tool | Constraint |
|-----------|------|------------|
| PDF extraction | PyMuPDF (`fitz`) | Do not swap for pdfplumber |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | 300–400 chars, 100 overlap — do not change |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Local only, no API call at inference |
| Semantic index | `faiss-cpu` `IndexFlatIP` | One index per corpus |
| Keyword index | `rank-bm25` | Same chunks as FAISS |
| Re-ranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Runs locally on CPU |
| LLM | Groq API — `llama3-8b-8192` | Free tier |
| UI | Streamlit | 3 tabs + sidebar layout |
| Metadata | Python `pickle` or SQLite | No heavyweight DB |
| Language | Python 3.10+ | |

---

## 4. Chunking Rules

- **Chunk size:** 300–400 characters
- **Overlap:** 100 characters
- **Splitter:** `LangChain RecursiveCharacterTextSplitter`
- **Rationale:** One legal sub-clause or provision fits within this range. Overlap prevents splitting a clause across two chunks.
- **Do not** adjust chunk size to fix retrieval quality — fix the retriever instead.

Each chunk must store:

```python
{
  "text": str,
  "source_doc": str,          # filename
  "law_domain": str,          # constitutional / criminal / civil / family / private
  "section_hint": str | None, # article number if detectable
  "firm_id": str | None,      # null for public
  "access_level": str,        # public / associate / partner
  "chunk_id": str             # hash of source_doc + position
}
```

---

## 5. Index Isolation Rules

- Public index and firm indexes are **physically separate files**.
- A firm's index files live under `/indexes/firms/{firm_id}/` only.
- The retriever must **never load a firm index without first confirming the user's `firm_id` matches**.
- Cross-firm isolation is enforced at the filesystem level, not just by filter — Firm A's `.faiss` file is never loaded during a Firm B query.

---

## 6. Query Pipeline Rules

```
User query
  → Query Expander (2 alternate phrasings via Groq → 3 total queries)
  → All 3 queries through Hybrid Retriever (FAISS top-15 + BM25 top-15 per query)
  → Merge + Deduplicate by chunk_id
  → Metadata Filter (role-based)
  → Cross-Encoder Re-ranker → Top-10 chunks
  → Generator (Groq / Llama 3)
  → Answer + Citations
```

Do not skip any step. Each step was designed to fix a specific failure mode:

| Step | Failure it prevents |
|------|---------------------|
| Query expansion | Missing relevant sections due to paraphrase mismatch |
| BM25 alongside FAISS | Semantic search missing exact section/article references |
| Re-ranker | Semantic drift — semantically similar but legally irrelevant chunks |
| Metadata filter | Access leakage between firms or roles |

---

## 7. LLM System Prompt (Fixed)

The system prompt must contain all four of these constraints verbatim. Do not soften them.

```
You are a legal research assistant for Pakistani law.
You must answer ONLY using the context provided below.
Always cite the specific article, section, or document name that supports your answer.
If the provided context does not contain enough information to answer, say exactly:
"I could not find a relevant provision in the available legal documents."
Never guess. Never draw on general knowledge. Never fabricate citations.
Keep answers clear enough for a non-lawyer to understand.
```

---

## 8. Access Control Rules

| Role | Can search | Can upload | Can delete |
|------|-----------|------------|------------|
| `public` | Public index only | No | No |
| `associate` | Public + own firm (access_level ≤ associate) | No | No |
| `partner` | Public + own firm (all access levels) | No | No |
| `admin` | Full access | Yes | Yes |

- A `partner` running **Combined Search** gets results from both public and firm indexes merged together, with sources clearly labelled.
- An `associate` can never see documents tagged `access_level = partner`.
- Roles are assigned server-side at login — the UI never sets its own role.

---

## 9. UI Tab Specifications

### Tab 1 — Public Law Search
- Search bar (no login required)
- Result: LLM answer + list of retrieved sections with `source_doc` and `section_hint`
- Anyone can access this tab

### Tab 2 — Firm Vault
- Login panel (username + password)
- Document uploader (PDF only, admin/partner role to upload)
- Document library: list of firm docs with upload date
- Search bar (queries firm index only)
- Result: LLM answer + source document name + page reference

### Tab 3 — Combined Search
- Requires partner login
- Search bar
- Result: split two-column display — **Public Law Sources** | **Firm Document Sources**
- Unified LLM answer synthesizing both

### Sidebar (visible when logged in)
- `Logged in as: [name], [role], [firm]`
- `Active corpus: public only / firm only / combined`
- Logout button

---

## 10. Evaluation Standards

The following metrics must be computed and reported:

- **Precision@1, @5, @10** — What fraction of top-K returned chunks contain the ground-truth section?
- **MRR (Mean Reciprocal Rank)** — What is the average reciprocal rank of the first correct result?

The comparison table must show:

| Metric | BM25 Baseline | PakLaw AI |
|--------|--------------|-----------|
| Precision@1 | — | — |
| Precision@5 | — | — |
| Precision@10 | — | — |
| MRR | — | — |

Test set: minimum 25 questions, covering at least 5 law domains.

---

## 11. Documentation Standards

Every Python file must have:

```python
"""
Module: <module_name>
Purpose: <one sentence>
Inputs: <what it receives>
Outputs: <what it produces>
Dependencies: <key libraries>
"""
```

Every function must have:

```python
def function_name(arg1, arg2):
    """
    Brief description.

    Args:
        arg1: description and type
        arg2: description and type

    Returns:
        description and type
    """
```

Key algorithmic steps (chunking logic, merge strategy, re-ranking, filter logic) must have inline comments explaining **why**, not just **what**.

---

## 12. What Not To Do

- Do not use `gpt-4` or any OpenAI model — Groq free tier is the constraint.
- Do not use `pdfplumber` — PyMuPDF only.
- Do not persist user state in Streamlit session between server restarts (use SQLite for user store).
- Do not adjust chunk size to patch retrieval quality — debug the retriever.
- Do not load another firm's index file, even temporarily, for any comparison or test.
- Do not let the LLM answer from general knowledge — if context is empty, return the "not found" response defined in the system prompt.
