# PakLaw AI Implementation Guidelines

These guidelines are the source of truth for implementation decisions.

## 1. Core Principle: No Hallucination

Every answer must be grounded in retrieved text. The LLM is a formatter and synthesizer, not a knowledge source.

The system prompt must preserve these constraints:

```text
You are a legal research assistant for Pakistani law.
You must answer ONLY using the context provided below.
Always cite the specific article, section, or document name that supports your answer.
If the provided context does not contain enough information to answer, say exactly:
"I could not find a relevant provision in the available legal documents."
Never guess. Never draw on general knowledge. Never fabricate citations.
Keep answers clear enough for a non-lawyer to understand.
```

## 2. Project Structure

```text
paklaw-ai/
  data/public/                 Public law PDFs
  data/firms/{firm_id}/         Firm-uploaded PDFs
  indexes/public/               Public FAISS, chunks, and BM25 files
  indexes/firms/{firm_id}/      Firm FAISS, chunks, and BM25 files
  ingestion/                    Extract, clean, chunk, tag, and build FAISS
  eval/                         Question set, result logs, and metrics
  demo/                         Demo script
  report/                       Report draft/artifacts
  app.py                        Streamlit UI
  retriever.py                  Hybrid retrieval engine
  generator.py                  Groq-grounded answer generation
  access_control.py             SQLite and bcrypt auth
```

## 3. Technology Stack

| Component | Tool | Constraint |
|---|---|---|
| PDF extraction | PyMuPDF (`fitz`) | Do not swap for pdfplumber |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | 300-400 chars, 100 overlap |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Required local transformer model |
| Semantic index | `faiss-cpu` `IndexFlatIP` | One index per corpus |
| Keyword index | `rank-bm25` | Same chunks as FAISS |
| Re-ranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Required local cross-encoder |
| LLM | Groq `llama-3.1-8b-instant` | Single generation model |
| UI | Streamlit | 3 tabs + sidebar |
| Auth | SQLite + bcrypt | No custom password hashing fallback |

## 4. Chunk Metadata

Each chunk must store:

```python
{
    "text": str,
    "source_doc": str,
    "law_domain": str,
    "section_hint": str | None,
    "firm_id": str | None,
    "access_level": str,  # public / firm
    "chunk_id": str,
}
```

## 5. Index Isolation

- Public and firm indexes are physically separate.
- A firm's index files live under `indexes/firms/{firm_id}/`.
- The retriever must never load a firm index unless the user's `firm_id` matches that firm.
- Cross-firm isolation is enforced by routing to the correct index directory, then by metadata filtering.

## 6. Query Pipeline

```text
User query
  -> Query expander (Groq JSON array, or original query only)
  -> FAISS top-15 + BM25 top-15 per query
  -> Merge + deduplicate by chunk_id
  -> Firm/role filter
  -> Cross-encoder reranker
  -> Top-10 chunks
  -> Groq grounded answer with citations
```

The query expander should parse a JSON array only. If parsing or the API call fails, it returns `[original_query]`.

## 7. Access Control

| Role | Can search | Can upload |
|---|---|---|
| `public` | Public index only, no login required | No |
| `user` | Public + own firm index, login required | No |
| `admin` | Public + own firm index, login required | Yes |

- Roles are assigned server-side at login.
- `user` and `admin` can search their own firm documents.
- `admin` is the only upload role.
- There is no associate/partner distinction in the current project scope.

## 8. UI Tabs

### Public Search

- No login required.
- Shows the grounded answer and retrieved public sources.

### Firm Vault

- Requires login with a firm-linked account.
- Shows firm search and the firm document library.
- Shows upload controls only for `admin`.

### Combined Search

- Requires login with `user` or `admin`.
- Searches public and firm corpora together.
- Splits retrieved sources into public law sources and firm document sources.

### Sidebar

- Shows login status, role, firm, active corpus, and logout when applicable.

## 9. Evaluation Standards

Report these metrics for the annotated question set:

- Precision@1
- Precision@5
- Precision@10
- MRR

Compare BM25 baseline against PakLaw AI.

## 10. What Not To Do

- Do not use OpenAI models; this project uses Groq.
- Do not use offline hash embeddings or heuristic rerankers.
- Do not generate a `_backend.json` sidecar for indexes.
- Do not silently switch generation models.
- Do not auto-annotate evaluation ground truth with PakLaw AI itself.
- Do not load another firm's index file, even temporarily.
