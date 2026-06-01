# PakLaw AI

A hybrid retrieval-augmented generation system for Pakistani legal research. Users submit legal questions in natural language, the system retrieves the most relevant passages from indexed law corpora, and a Groq-hosted LLM produces a cited answer grounded in those passages.


Live view: https://pak-law-ai.vercel.app/

---

## What it does

- Searches a public corpus of Pakistani law PDFs using hybrid dense and lexical retrieval
- Allows law firms to maintain isolated private corpora alongside the public law index
- Generates cited answers constrained to retrieved passages, with no free-form speculation
- Enforces role-based access so public users never see private firm material
- Exposes two interfaces: a Streamlit development UI and a production FastAPI backend with a Next.js frontend

---

## Architecture

The system is organized into four runtime layers.

**Ingestion** reads PDFs, cleans and chunks the text, tags each chunk with metadata, builds a FAISS dense vector index, and builds a BM25 lexical index. Public and firm corpora share the same pipeline but are stored and routed separately.

**Retrieval** expands the user query using Groq/Llama 3, searches FAISS and BM25 across the applicable corpora, deduplicates candidates by chunk ID, filters by role and firm access, and reranks the shortlist using a cross-encoder.

**Generation** formats the top-ranked chunks into a grounded context block, calls Groq chat completions, and returns a cited answer. The system prompt instructs the model never to fabricate citations and to state explicitly when evidence is thin.

**Access control** stores users in SQLite, hashes passwords with bcrypt, and maps each role to the corpora it may search.

---

## Repository layout

```
PakLaw-AI/
├── app.py                  # Streamlit development UI (3-tab layout)
├── retriever.py            # Hybrid retrieval pipeline
├── generator.py            # Groq answer generation
├── access_control.py       # Auth, roles, index routing
├── build_bm25.py           # BM25 index builder
├── ingest_public.py        # Public corpus ingestion orchestrator
├── ingest_private.py       # Firm corpus ingestion orchestrator
├── requirements.txt        # Python dependencies
│
├── ingestion/              # PDF preprocessing pipeline
│   ├── extractor.py        # PyMuPDF text extraction
│   ├── cleaner.py          # Noise removal and normalization
│   ├── chunker.py          # Overlapping chunk splitting
│   ├── tagger.py           # Metadata attachment (domain, section hint, IDs)
│   └── index_builder.py    # FAISS embedding and index writing
│
├── backend/                # FastAPI production backend
│   ├── main.py             # App entry point, CORS, lifespan
│   ├── auth.py             # JWT creation and dependency injection
│   ├── config.py           # Environment-based configuration
│   ├── requirements.txt    # Backend-only dependencies
│   ├── models/schemas.py   # Pydantic request/response models
│   └── routers/
│       ├── auth.py         # /auth/login, /auth/logout, /user/me
│       ├── search.py       # /search/public, /search/firm, /search/combined
│       └── ingest.py       # /ingest/firm (admin only)
│
├── core/                   # Shared business logic used by the backend
│   ├── access_control.py
│   ├── retriever.py
│   ├── generator.py
│   ├── build_bm25.py
│   ├── ingest_private.py
│   └── ingestion/
│
├── frontend/               # Next.js web interface
│   ├── app/                # Next.js App Router pages and layout
│   ├── components/         # React components
│   │   ├── AnswerBlock.jsx
│   │   ├── ConfidenceBadge.jsx
│   │   ├── LoginPanel.jsx
│   │   ├── SearchWorkspace.jsx
│   │   ├── SourceCard.jsx
│   │   └── UploadPanel.jsx
│   └── lib/api.js          # API client (fetch wrappers)
│
└── data/
    └── public/             # Place public law PDFs here before ingestion
```

---

## Data and index layout

```
data/
  public/                   # Source PDFs for public law corpus
  firms/<firm_id>/          # Uploaded PDFs for each firm
  users.sqlite3             # User store (auto-created on first run)

indexes/
  public/
    pakistan_law_public.faiss
    pakistan_law_public_chunks.pkl
    pakistan_law_public_bm25.pkl
  firms/<firm_id>/
    firm_<firm_id>.faiss
    firm_<firm_id>_chunks.pkl
    firm_<firm_id>_bm25.pkl
```

Retrieval cannot work until the index files are present. Run ingestion before the first search.

---

## Access model

| Role   | Public corpus | Firm corpus          | Upload PDFs |
|--------|---------------|----------------------|-------------|
| public | Yes           | No                   | No          |
| user   | Yes           | Yes (own firm only)  | No          |
| admin  | Yes           | Yes (own firm only)  | Yes         |

A `firm_id` must be assigned to a user account for firm corpus access to activate. Combined search (public + firm simultaneously) is restricted to authenticated users with a firm ID.

Demo accounts seeded at startup when `PAKLAW_SEED_DEMO_USERS=true`:
- `user_demo` / `user123` — role `user`, firm `firm_alpha`
- `admin_demo` / `admin123` — role `admin`, firm `firm_alpha`

---

## Models

| Purpose        | Model                                        |
|----------------|----------------------------------------------|
| Embeddings     | sentence-transformers/all-MiniLM-L6-v2       |
| Reranking      | cross-encoder/ms-marco-MiniLM-L-6-v2         |
| Query expansion| llama-3.1-8b-instant (Groq)                  |
| Generation     | llama-3.1-8b-instant (Groq)                  |

Embedding and reranker models are loaded from local cache when available (`local_files_only=True`) and downloaded on first run otherwise.

---

## Setup

### Prerequisites

- Python 3.10 or later
- Node.js 18 or later (frontend only)
- A Groq API key (query expansion and answer generation)

### Python environment

```bash
git clone https://github.com/hassanh5n/PakLaw-AI.git
cd PakLaw-AI
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

Without `GROQ_API_KEY` the system still retrieves chunks but generation falls back to a static disclaimer message and query expansion is skipped.

---

## Ingesting documents

### Public corpus

Place PDF files in `data/public/`, then run:

```bash
python ingest_public.py
```

This walks the directory, extracts and cleans text, splits into overlapping chunks, tags metadata, and writes the FAISS and BM25 indexes to `indexes/public/`.

Scanned PDFs without extractable text are skipped automatically.

### Firm corpus (via CLI)

```bash
python -c "
from ingest_private import ingest_firm_pdf
ingest_firm_pdf('path/to/document.pdf', firm_id='firm_alpha', access_level='firm')
"
```

Repeated calls append to the existing firm index. The FAISS and BM25 indexes are rebuilt after each addition.

### Firm corpus (via UI)

Log in as an admin user in either the Streamlit app or the Next.js frontend and use the upload panel. The file is saved to `data/firms/<firm_id>/` and ingested immediately.

---

## Running the Streamlit development UI

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. The three-tab layout exposes:
- **Public Search** — available without login
- **Firm Vault** — requires login with a firm ID
- **Combined Search** — searches both corpora for authenticated users with a firm ID

To seed the demo users on startup:

```bash
PAKLAW_SEED_DEMO_USERS=true streamlit run app.py
```

---

## Running the production stack

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:main --host 0.0.0.0 --port 8000 --reload
```

The backend reads configuration from environment variables and the `.env` file in the project root. Key variables:

| Variable                    | Default                              | Description                        |
|-----------------------------|--------------------------------------|------------------------------------|
| `GROQ_API_KEY`              | (required for generation)            | Groq API key                       |
| `PAKLAW_JWT_SECRET`         | `paklaw-local-dev-change-me`         | JWT signing secret                 |
| `PAKLAW_INDEX_ROOT`         | `<repo_root>/indexes`                | Path to index directory            |
| `PAKLAW_DATA_ROOT`          | `<repo_root>/data`                   | Path to data directory             |
| `PAKLAW_USERS_DB`           | `<data_root>/users.sqlite3`          | SQLite user store path             |
| `PAKLAW_ACCESS_TOKEN_MINUTES` | `60`                               | JWT expiry in minutes              |
| `PAKLAW_EAGER_MODEL_LOAD`   | `true`                               | Load models at startup             |
| `PAKLAW_FRONTEND_ORIGINS`   | `http://localhost:3000,...`          | Comma-separated allowed origins    |
| `PAKLAW_SEED_DEMO_USERS`    | `false`                              | Seed demo accounts at startup      |

Change `PAKLAW_JWT_SECRET` before any deployment that handles real data.

### Frontend (Next.js)

```bash
cd frontend
cp .env.example .env.local
# Edit .env.local and set NEXT_PUBLIC_API_BASE_URL if the backend is not on localhost:8000
npm install
npm run dev
```

Opens at `http://localhost:3000`.

---

## API endpoints

| Method | Path              | Auth required | Description                        |
|--------|-------------------|---------------|------------------------------------|
| POST   | /auth/login       | No            | Returns JWT and user record        |
| POST   | /auth/logout      | No            | Clears auth cookie                 |
| GET    | /user/me          | Yes           | Returns current user info          |
| POST   | /search/public    | No            | Searches public corpus             |
| POST   | /search/firm      | user, admin   | Searches firm corpus               |
| POST   | /search/combined  | user, admin   | Searches public and firm corpora   |
| POST   | /ingest/firm      | admin         | Uploads and ingests a firm PDF     |
| GET    | /health           | No            | Returns backend status             |

### Search request body

```json
{
  "query": "What are the conditions for a valid contract under Pakistani law?",
  "top_k": 8,
  "expand": true,
  "include_answer": true
}
```

### Search response body

```json
{
  "mode": "public",
  "query": "...",
  "answer": "...",
  "confidence": "high",
  "sources": [
    {
      "chunk_id": "a1b2c3d4",
      "source_doc": "Contract_Act_1872.pdf",
      "section_hint": "Section 10",
      "law_domain": "civil",
      "access_level": "public",
      "corpus": "public",
      "text": "...",
      "relevance_score": 0.81,
      "rerank_score": 7.23,
      "low_confidence": false
    }
  ]
}
```

---

## Retrieval pipeline detail

1. **Query variants** — the original query, a normalized form, a stopword-stripped form, and up to three LLM-generated rephrasings (when Groq is available) are searched independently.
2. **FAISS search** — each variant is embedded with `all-MiniLM-L6-v2` and searched against the inner-product index (top 25 per variant).
3. **BM25 search** — each variant is tokenized and scored against the `BM25Okapi` index (top 25 per variant).
4. **Deduplication** — candidates are merged by `chunk_id`, keeping the highest `combined_score` for each.
5. **Access filtering** — chunks are filtered by `access_level` and `firm_id` against the requesting user's role.
6. **Cross-encoder reranking** — remaining candidates are scored by `ms-marco-MiniLM-L-6-v2` as query-passage pairs.
7. **Relevance filtering** — a weighted composite score (60% rerank, 25% FAISS, 15% BM25, normalized within the result set) is computed. Results below the irrelevance cutoff are dropped. Results below the low-confidence cutoff are returned but flagged.
8. **Fallback** — if no results pass thresholds, the top reranked hits are returned marked as low-confidence rather than returning an empty set.

---

## Ingestion pipeline detail

Each PDF goes through these stages in order:

1. `extractor.py` — extracts page text with PyMuPDF; skips pages with fewer than 50 characters
2. `cleaner.py` — removes page numbers, common header/footer patterns, excess whitespace, and non-printable characters
3. `chunker.py` — splits cleaned text with `RecursiveCharacterTextSplitter` (chunk size 700, overlap 150, separators: paragraph, line, sentence, word)
4. `tagger.py` — attaches `source_doc`, `law_domain` (inferred from filename), `section_hint` (from leading Article/Section pattern), `firm_id`, `access_level`, and a short stable `chunk_id`
5. `index_builder.py` — embeds all chunks in batches of 64, builds a `faiss.IndexFlatIP`, and writes the `.faiss` and `_chunks.pkl` files
6. `build_bm25.py` — reads `_chunks.pkl`, tokenizes with lowercase split, builds `BM25Okapi`, and writes `_bm25.pkl`

---

## Generation design

The system prompt instructs the model to:
- Answer using retrieved context as primary evidence
- Cite the specific source document, section hint, or bracketed chunk number for every material claim
- State explicitly when evidence is thin rather than refusing to answer
- Never fabricate citations

When fewer than three chunks are retrieved, the answer is prefixed with an evidence warning. When no chunks are retrieved and a Groq key is configured, the model is instructed to provide a cautious high-level response and suggest consulting specific statutes or a lawyer. When no Groq key is configured and chunks are present, the backend raises a `RuntimeError` surfaced to the UI rather than silently returning a hallucinated answer.

---

## Dependencies

### Core (requirements.txt)

| Package                  | Version   | Purpose                              |
|--------------------------|-----------|--------------------------------------|
| PyMuPDF                  | latest    | PDF text extraction                  |
| langchain-text-splitters | latest    | RecursiveCharacterTextSplitter       |
| sentence-transformers    | 3.0.1     | Embedding model and cross-encoder    |
| faiss-cpu                | 1.13.1    | Dense vector index                   |
| numpy                    | 2.3.5     | Vector arrays                        |
| torch                    | 2.6.0     | Backend for sentence-transformers    |
| rank-bm25                | latest    | BM25Okapi keyword index              |
| groq                     | latest    | Groq API client                      |
| streamlit                | 1.57.0    | Development UI                       |
| bcrypt                   | latest    | Password hashing                     |
| python-dotenv            | latest    | .env loading                         |
| tqdm                     | latest    | Ingestion progress bars              |

### Backend (backend/requirements.txt)

| Package                     | Version   | Purpose                          |
|-----------------------------|-----------|----------------------------------|
| fastapi                     | 0.115.6   | API framework                    |
| uvicorn[standard]           | 0.32.1    | ASGI server                      |
| python-jose[cryptography]   | 3.3.0     | JWT encoding and decoding        |
| python-multipart            | 0.0.20    | File upload parsing              |
| anyio                       | latest    | Thread offloading for sync code  |

### Frontend (frontend/package.json)

| Package       | Version   | Purpose               |
|---------------|-----------|-----------------------|
| next          | 15.x      | React framework       |
| react         | 19.x      | UI rendering          |
| tailwindcss   | 3.x       | Utility CSS           |
| lucide-react  | 0.468.x   | Icon set              |

---

## Known constraints

- Scanned PDFs without embedded text cannot be ingested. The pipeline detects and skips them.
- The first retrieval request after startup is slower because embedding and reranker models are loaded lazily (or eagerly if `PAKLAW_EAGER_MODEL_LOAD=true`).
- The `_load_corpus_assets` function caches index files in memory using `lru_cache`. If a firm index is rebuilt while the server is running, restart the backend to pick up the new files.
- The Streamlit UI and the FastAPI backend are independent surfaces; they do not share a session or JWT. Run one or the other, not both against the same user store concurrently during development.
- `PAKLAW_JWT_SECRET` defaults to a plaintext development value. Replace it with a randomly generated secret before handling any non-demo credentials.
