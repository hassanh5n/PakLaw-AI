# PakLaw AI Project Context

## Executive Summary
PakLaw AI is a Pakistani legal research application built around a grounded search-and-answer workflow. It is designed to help a user ask a legal question, retrieve the most relevant provisions or passages from a curated corpus, and produce a cited answer that stays tied to source documents rather than free-form speculation.

This project is best understood as a retrieval-augmented generation system, but with an important nuance: it is not a generic chatbot wrapped around documents. It is a domain-specific legal research product with three tightly defined search surfaces, role-based access, and explicit source rendering. Retrieval is the primary function; generation is the final explanation layer.

In practice, the system supports:
- Public legal research over a public corpus of Pakistani law PDFs.
- Private firm-vault research over firm-specific documents.
- Combined search over public plus private sources for authenticated users with a firm identifier.
- Answer generation that is constrained by retrieved passages and displayed alongside the evidence used.

The intended outcome is practical legal search, not open-ended conversation. Users should leave with a defensible answer, the source fragments that produced it, and enough context to judge whether the result is usable.

## What The Project Is Trying To Achieve
The project stands for a few concrete goals:

- Make Pakistani legal material searchable in a way that is faster than manual PDF browsing.
- Allow a firm to maintain an isolated private corpus alongside public law.
- Preserve access boundaries so public users never see private material and authorized users only see what their role allows.
- Turn search results into readable answers with citations so the system is useful to non-specialists as well as legal staff.
- Keep the implementation small enough that the core flow is easy to understand, debug, and extend.

This is a knowledge retrieval system for law, not a legal advisor, not a document management system, and not a general-purpose assistant.

## Is It RAG?
Yes. It is a RAG-style application.

The retrieval-augmented generation pattern here is:
1. User submits a legal question.
2. The system retrieves relevant document chunks from indexed corpora.
3. The system reranks and filters those chunks by access rights and corpus scope.
4. The Groq-hosted LLM receives the retrieved chunks as grounded context.
5. The LLM produces a legal answer that cites the supporting material.

What makes this a strong RAG implementation rather than a loose approximation is that the retrieved evidence is first-class in the product UI. The app does not hide retrieval behind the model; it surfaces the source chunks and expects the answer to be grounded in them.

The retrieval side is also hybrid rather than single-method. It combines:
- Dense vector search with FAISS.
- Lexical search with BM25.
- Query expansion when an LLM is available.
- Cross-encoder reranking for the final shortlist.

That means the project is best described as a hybrid legal RAG system with access-controlled corpora.

## Product Shape
The user-facing product is a Streamlit web app with three tabs:

- Public Search for anonymous or public users.
- Firm Vault for authenticated users who have access to a firm corpus.
- Combined Search for authenticated users who are allowed to search both corpora at once.

The UI is intentionally operational rather than decorative. It shows the current user, role, firm, active corpus, answer text, and the retrieved source cards. The last result is kept in session state so users can inspect what was returned without losing the result after every interaction.

The application is not trying to be a conversational notebook or a general legal copiloting surface. It is trying to behave like a research terminal with a guided answer layer.

## Core Components
The repository is organized around a small number of runtime modules.

### [app.py](app.py)
The Streamlit entry point and orchestration layer.

Responsibilities:
- Initialize session state.
- Warm up heavy retrieval models in the background.
- Show the sidebar and the three search modes.
- Handle login, logout, PDF upload, and search actions.
- Render answers and retrieved source cards.

It is the coordination point, not the place where the retrieval logic lives.

### [retriever.py](retriever.py)
The search engine.

Responsibilities:
- Expand queries when a Groq API key is available.
- Load the FAISS index, chunk metadata, and BM25 index for the target corpus.
- Search public, firm, or combined corpora depending on role and firm ID.
- Merge FAISS and BM25 hits.
- Deduplicate by chunk ID.
- Apply role and firm access filtering.
- Rerank the final candidate set with a cross-encoder.

This file is the heart of the RAG retrieval path.

### [generator.py](generator.py)
The answer generation layer.

Responsibilities:
- Load the Groq API key.
- Build the system prompt for legal answering.
- Format retrieved chunks into a context block.
- Call Groq chat completions.
- Return a grounded answer string.

Its job is to write from evidence, not invent new evidence.

### [access_control.py](access_control.py)
The identity and routing layer.

Responsibilities:
- Store users in SQLite.
- Hash passwords with bcrypt.
- Authenticate credentials.
- Normalize user records into role and firm routing metadata.
- Map roles to accessible corpora.

This module defines who may search what.

### [build_bm25.py](build_bm25.py)
The lexical index builder.

Responsibilities:
- Read chunk metadata from disk.
- Build a BM25Okapi index.
- Persist the BM25 artifact alongside the FAISS index and chunks.

### [ingest_public.py](ingest_public.py)
The public-corpus ingestion orchestrator.

Responsibilities:
- Walk the public PDF directory.
- Extract, clean, chunk, tag, and index each PDF.
- Produce the public FAISS, chunk, and BM25 artifacts.

### [ingest_private.py](ingest_private.py)
The firm-corpus ingestion orchestrator.

Responsibilities:
- Ingest a single uploaded PDF for a firm.
- Merge it into the existing firm index when present.
- Rebuild the firm FAISS and BM25 artifacts.

### [ingestion/](ingestion/)
The PDF preprocessing pipeline.

Contains the lower-level stages that convert PDFs into searchable records:
- [extractor.py](ingestion/extractor.py) extracts page text with PyMuPDF.
- [cleaner.py](ingestion/cleaner.py) removes PDF noise and normalizes the text.
- [chunker.py](ingestion/chunker.py) splits cleaned text into overlapping chunks.
- [tagger.py](ingestion/tagger.py) attaches metadata such as law domain, section hint, firm ID, access level, and chunk ID.
- [index_builder.py](ingestion/index_builder.py) embeds chunks and writes FAISS plus the chunk pickle.

## How The System Works End To End
The runtime flow is easiest to understand as a pipeline.

### 1. Document Ingestion
Public PDFs live in `data/public/`. Firm PDFs are uploaded through the Streamlit app and stored under a firm-specific directory.

The ingestion process:
- Extracts text from each PDF page.
- Cleans headers, footers, page numbers, and OCR noise.
- Chunks the text into overlapping passages.
- Tags each chunk with document metadata.
- Embeds the chunks for vector search.
- Builds the FAISS and BM25 indexes.

The output is a searchable corpus represented by three files per index:
- `.faiss` for vector search.
- `_chunks.pkl` for chunk metadata.
- `_bm25.pkl` for keyword search.

### 2. Retrieval
When a user searches:
- The app determines the allowed corpus scope from the user role and firm ID.
- The retriever optionally expands the query using Groq.
- The retriever searches FAISS and BM25.
- Candidates are deduplicated and filtered.
- A cross-encoder reranks the final list.

The output is a ranked list of chunk dictionaries with source metadata, score fields, and access context.

### 3. Generation
The ranked chunks are handed to Groq.

The generator:
- Builds a legal system prompt.
- Formats the retrieved chunks into a context block.
- Asks the model to answer the question using the retrieved evidence.
- Requires citations or source references in the answer.

If there are no chunks or the Groq key is missing, generation fails cleanly and the UI surfaces the error rather than pretending an answer exists.

### 4. Presentation
The app renders:
- The answer.
- Retrieved source cards.
- User and corpus status in the sidebar.

This is important because the product is designed to be auditable by the user, not just conversational.

## Data And Artifact Layout
The project expects a specific on-disk layout.

### Input data
- `data/public/` contains public law PDFs.
- `data/firms/<firm_id>/` contains uploaded firm PDFs.

### User store
- `data/users.sqlite3` stores usernames, bcrypt password hashes, roles, and optional firm IDs.

### Indexes
- `indexes/public/` stores the public corpus artifacts.
- `indexes/firms/<firm_id>/` stores firm-specific artifacts.

### Index file naming
Each corpus uses a consistent trio of files:
- `<index_name>.faiss`
- `<index_name>_chunks.pkl`
- `<index_name>_bm25.pkl`

For the public corpus, the index name is `pakistan_law_public`.
For firm corpora, the index name is `firm_<firm_id>`.

If these files do not exist, retrieval cannot work.

## Access And Security Model
The access model is intentionally simple and explicit.

Supported roles:
- `public`
- `user`
- `admin`

Behavior:
- Public users can search public law only.
- Logged-in `user` and `admin` accounts can access public search and, if they have a firm ID, firm search.
- Combined search is restricted to authenticated users with a firm ID.
- Admin users can upload firm PDFs.

The app seeds demo accounts when the user store is initialized, which makes first-run testing easier.

This is not enterprise SSO. It is a lightweight, local, SQLite-backed access layer meant to make corpus separation and demo authentication work reliably in a small codebase.

## Retrieval Design
The retrieval layer is the main technical differentiator of the project.

What it does well:
- Uses both dense and lexical retrieval so exact legal terms and semantically similar language can both succeed.
- Supports query expansion for better recall on legal wording.
- Uses cross-encoder reranking to improve final result quality.
- Filters candidate chunks by access level and firm ownership before ranking is returned to the user.

Why this matters for legal search:
- Law queries often contain exact phrases that benefit from BM25.
- Users also phrase legal issues in natural language, which benefits from dense embeddings.
- Legal answers are often only acceptable when the answer can be tied to a specific source passage.

The retriever therefore acts as the evidence collector for the whole product.

## Generation Design
The generation layer is intentionally constrained.

It is built to:
- Stay tied to the retrieved context.
- Cite sources, section hints, or chunk references.
- Return a concise answer that a non-lawyer can understand.

It is not designed to:
- Freewheel without evidence.
- Invent citations.
- Replace a lawyer’s judgment.

The system prompt explicitly tells the model to answer from retrieved evidence and to avoid fabricated citations. That makes the answer behavior aligned with the product’s legal-research purpose.

## Ingestion Design
The ingestion pipeline is a document factory for search artifacts.

Pipeline order:
1. Extract text from the PDF.
2. Clean the text.
3. Split it into overlapping chunks.
4. Tag the chunks with metadata.
5. Build the FAISS index.
6. Build the BM25 index.

Important notes:
- Scanned or non-text-extractable PDFs are skipped or rejected.
- Chunk size and overlap are intentionally fixed to preserve consistency across corpora.
- Metadata tagging adds fields used later in ranking and display.
- Public and private corpora share the same preprocessing mechanics, but they are stored and routed separately.

## UI Behavior And Product Experience
The UI is deliberately centered on the search result, not on decorative chat history.

Expected behavior:
- Public search works without login.
- Firm vault access appears only after authentication.
- Combined search is only available when the role and firm ID permit it.
- The answer block appears even when generation fails, so the user understands whether the failure happened in retrieval or generation.
- Retrieved chunks are shown below the answer to preserve transparency.

The sidebar summarizes the user identity and the active corpus so the user can always tell which search space they are in.

## What This Project Is Not
This is worth stating explicitly for users and stakeholders.

PakLaw AI is not:
- A general-purpose chatbot.
- A legal authority of record.
- A replacement for legal counsel.
- A document repository without search intelligence.
- A multi-tenant enterprise platform with complex access control.

It is a focused legal research assistant built around searchable corpora and grounded answer generation.

## Technical Constraints And Operating Assumptions
The project assumes a Windows Python environment that may be sensitive to native packages and model loading behavior.

Operational constraints:
- The first search may be slower than later searches because models are warmed in the background.
- Hugging Face and sentence-transformers dependencies can be expensive to load.
- Streamlit file watching is disabled in local config because it can interact poorly with large transformer-based dependencies.
- The app should fail visibly and informatively if indexes or models are missing.

The codebase prefers explicit, reliable control flow over additional abstraction layers.

## For Different Audiences
### For users
Use the app to search public law, search your firm’s private documents, or search both when authorized. Review the retrieved sources before trusting the answer.

### For developers
The key thing to preserve is the pipeline contract between ingestion, retrieval, and generation. If you change one side, verify the index artifacts and metadata fields still line up with the UI and generator.

### For managers
The project is a narrow legal search product with a measurable scope. It can be extended, but the current value proposition is legal retrieval with grounded generation and access separation.

### For business stakeholders
The product can support research workflows, document search, and knowledge reuse. Its differentiator is corpus isolation plus answer generation with evidence, which makes it suitable for public legal information and firm-specific knowledge bases.

### For LLMs and automated agents
Treat retrieval as mandatory context. Do not assume the model should answer from memory. The source documents, access role, and firm ID determine what the model may see. The safest mental model is:
- `app.py` orchestrates the flow.
- `retriever.py` finds evidence.
- `generator.py` writes the answer from evidence.
- `access_control.py` determines visibility.
- `ingestion/` creates the artifacts that retrieval depends on.

## Extension Points
The most natural places to extend the project are:
- Add more public or private corpora by extending ingestion and index routing.
- Improve ranking by tuning query expansion, BM25, or reranking in [retriever.py](retriever.py).
- Improve answer quality by adjusting prompt structure in [generator.py](generator.py).
- Improve identity and routing by extending [access_control.py](access_control.py).
- Improve PDF preprocessing by refining [ingestion/cleaner.py](ingestion/cleaner.py) or [ingestion/chunker.py](ingestion/chunker.py).
- Improve the UI states in [app.py](app.py) for loading, missing indexes, and search failures.

When extending the system, always answer four questions first:
1. What new user flow is being added?
2. What data artifact does it require?
3. Which corpus or role should be allowed to see it?
4. What should the user see if the prerequisite artifact is missing?

## Current Project Shape
The repository is intentionally small and centered on the product path. The main runtime shape is:
- Streamlit UI.
- Access control and routing.
- Hybrid retrieval.
- Grounded generation.
- PDF ingestion and index building.
- Prepared data and indexes.
- Dependency configuration and Streamlit configuration.

That is the project’s intended identity: a compact, accessible, corpus-aware Pakistani legal RAG system.
