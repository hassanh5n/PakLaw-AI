"""
Module: setup_project
Purpose: Creates the full PakLaw AI folder structure from scratch.
Inputs: None — run this once at the start of the project.
Outputs: All required directories and placeholder files on disk.
Dependencies: os, pathlib (standard library only)
"""

import os
from pathlib import Path


def create_folder_structure(base_dir: str = ".") -> None:
    """
    Creates every directory and placeholder file required by the PakLaw AI project.

    Args:
        base_dir: Root path where the project folder will be created.
                  Defaults to the current working directory.

    Returns:
        None — creates folders/files on disk and prints a confirmation for each.
    """

    base = Path(base_dir)

    # ------------------------------------------------------------------
    # 1. Define all directories to create
    # ------------------------------------------------------------------
    dirs = [
        # Data
        "data/public",
        "data/firms",

        # Indexes
        "indexes/public",
        "indexes/firms",

        # Ingestion pipeline modules
        "ingestion",

        # Evaluation outputs
        "eval",

        # Manual test logs
        "tests",

        # Demo script
        "demo",

        # Final report
        "report",
    ]

    print("=" * 55)
    print("  PakLaw AI — Project Setup")
    print("=" * 55)

    for d in dirs:
        target = base / d
        target.mkdir(parents=True, exist_ok=True)
        print(f"  [DIR]  {target}")

    # ------------------------------------------------------------------
    # 2. Create placeholder .gitkeep files so empty dirs are tracked by Git
    # ------------------------------------------------------------------
    gitkeep_dirs = [
        "data/public",
        "data/firms",
        "indexes/public",
        "indexes/firms",
        "eval",
        "tests",
        "demo",
        "report",
    ]

    for d in gitkeep_dirs:
        gitkeep = base / d / ".gitkeep"
        gitkeep.touch(exist_ok=True)

    # ------------------------------------------------------------------
    # 3. Create placeholder Python files with correct module docstrings
    #    so every expected file exists before we fill in the code.
    # ------------------------------------------------------------------
    placeholder_modules = {
        "ingestion/__init__.py": "",

        "ingestion/extractor.py": '''\
"""
Module: extractor
Purpose: Extracts raw text from PDF files using PyMuPDF.
Inputs: Path to a PDF file.
Outputs: List of (page_number, raw_text) tuples.
Dependencies: PyMuPDF (fitz)
"""
''',
        "ingestion/cleaner.py": '''\
"""
Module: cleaner
Purpose: Cleans raw extracted text by removing headers, footers, page numbers, and OCR noise.
Inputs: Raw text string from extractor.
Outputs: Cleaned text string.
Dependencies: re (standard library)
"""
''',
        "ingestion/chunker.py": '''\
"""
Module: chunker
Purpose: Splits cleaned text into overlapping chunks using LangChain RecursiveCharacterTextSplitter.
Inputs: Cleaned text string.
Outputs: List of chunk text strings.
Dependencies: langchain
"""
''',
        "ingestion/tagger.py": '''\
"""
Module: tagger
Purpose: Attaches metadata to each chunk (source_doc, law_domain, section_hint, etc.).
Inputs: List of chunk texts, source PDF filename, firm context.
Outputs: List of chunk dicts with metadata fields.
Dependencies: hashlib (standard library)
"""
''',
        "ingestion/index_builder.py": '''\
"""
Module: index_builder
Purpose: Embeds chunks and builds a FAISS IndexFlatIP; saves .faiss and chunks.pkl to disk.
Inputs: List of tagged chunk dicts, output directory path.
Outputs: Saved .faiss index file and chunks.pkl file.
Dependencies: sentence-transformers, faiss-cpu, numpy, pickle
"""
''',
        "build_bm25.py": '''\
"""
Module: build_bm25
Purpose: Builds a BM25 index from existing chunks.pkl and saves bm25.pkl to disk.
Inputs: Path to chunks.pkl file, output directory path.
Outputs: Saved bm25.pkl file.
Dependencies: rank-bm25, pickle
"""
''',
        "ingest_public.py": '''\
"""
Module: ingest_public
Purpose: Orchestrates the full ingestion pipeline for all public law PDFs.
Inputs: PDF files in /data/public/.
Outputs: FAISS index + chunks.pkl + bm25.pkl saved to /indexes/public/.
Dependencies: ingestion/*, build_bm25
"""
''',
        "ingest_private.py": '''\
"""
Module: ingest_private
Purpose: Orchestrates the ingestion pipeline for a single firm's PDF upload.
Inputs: PDF file path, firm_id, access_level.
Outputs: Firm FAISS index + chunks.pkl + bm25.pkl saved to /indexes/firms/{firm_id}/.
Dependencies: ingestion/*, build_bm25
"""
''',
        "query_expander.py": '''\
"""
Module: query_expander
Purpose: Uses the Groq API to generate 2 alternative phrasings of the user query.
Inputs: Original query string, Groq API key.
Outputs: List of 3 query strings (original + 2 expansions).
Dependencies: groq
"""
''',
        "retriever.py": '''\
"""
Module: retriever
Purpose: Full hybrid retrieval pipeline — FAISS + BM25 + query expansion + re-ranking + access filter.
Inputs: Query string, user role, firm_id, index paths.
Outputs: Top-10 ranked, access-filtered chunk dicts.
Dependencies: faiss-cpu, rank-bm25, sentence-transformers, query_expander
"""
''',
        "generator.py": '''\
"""
Module: generator
Purpose: Constructs the LLM prompt from retrieved chunks and calls Groq to generate a cited answer.
Inputs: Original query string, list of top-10 chunk dicts.
Outputs: Answer string with citations.
Dependencies: groq, prompts
"""
''',
        "prompts.py": '''\
"""
Module: prompts
Purpose: Stores the locked system prompt and prompt-building helpers for the LLM generator.
Inputs: N/A (module-level constants).
Outputs: SYSTEM_PROMPT string, build_user_prompt() function.
Dependencies: None
"""
''',
        "access_control.py": '''\
"""
Module: access_control
Purpose: Manages user authentication, role assignment, and query routing to correct indexes.
Inputs: Username, password, role, firm_id.
Outputs: Authenticated user dict; routed index paths for a given role.
Dependencies: sqlite3, bcrypt
"""
''',
        "app.py": '''\
"""
Module: app
Purpose: Streamlit UI — 3-tab layout (Public Search, Firm Vault, Combined Search) + sidebar.
Inputs: User interactions via the web interface.
Outputs: Rendered web application at localhost:8501.
Dependencies: streamlit, retriever, generator, access_control
"""
''',
    }

    for filepath, content in placeholder_modules.items():
        full_path = base / filepath
        # Don't overwrite if it already has real content
        if not full_path.exists():
            full_path.write_text(content, encoding="utf-8")
            print(f"  [FILE] {full_path}")

    # ------------------------------------------------------------------
    # 4. Create placeholder markdown files for eval / tests / demo
    # ------------------------------------------------------------------
    md_placeholders = {
        "eval/test_questions.md":   "# PakLaw AI — Test Questions\n\n> To be filled in during Phase 8.\n",
        "eval/results_paklaw.md":   "# PakLaw AI — Retrieval Results\n\n> To be filled in during Phase 8.\n",
        "eval/results_baseline.md": "# BM25 Baseline — Retrieval Results\n\n> To be filled in during Phase 8.\n",
        "eval/metrics.md":          "# Evaluation Metrics\n\n> To be filled in during Phase 8.\n",
        "tests/q_and_a_log.md":     "# Q&A Test Log\n\n> To be filled in during Phase 5.\n",
        "demo/demo_script.md":      "# Demo Script\n\n> To be filled in during Phase 8.\n",
    }

    for filepath, content in md_placeholders.items():
        full_path = base / filepath
        if not full_path.exists():
            full_path.write_text(content, encoding="utf-8")
            print(f"  [FILE] {full_path}")

    # ------------------------------------------------------------------
    # 5. Create a .env.example so the developer knows what keys to set
    # ------------------------------------------------------------------
    env_example = base / ".env.example"
    env_example.write_text(
        "# Copy this file to .env and fill in your values\n"
        "GROQ_API_KEY=your_groq_api_key_here\n",
        encoding="utf-8",
    )
    print(f"  [FILE] {env_example}")

    # ------------------------------------------------------------------
    # 6. Create a .gitignore
    # ------------------------------------------------------------------
    gitignore_content = """\
# Environment
.env
__pycache__/
*.pyc
*.pyo
.venv/
env/

# Data & indexes (large binary files — don't commit)
data/public/*.pdf
data/firms/
indexes/

# Streamlit cache
.streamlit/

# Reports
report/*.pdf

# OS
.DS_Store
Thumbs.db
"""
    gitignore = base / ".gitignore"
    gitignore.write_text(gitignore_content, encoding="utf-8")
    print(f"  [FILE] {gitignore}")

    print("\n" + "=" * 55)
    print("  Setup complete.")
    print(f"  Project root: {base.resolve()}")
    print("=" * 55)
    print("\nNext steps:")
    print("  1. cd paklaw-ai")
    print("  2. python -m venv .venv && source .venv/bin/activate")
    print("  3. pip install -r requirements.txt")
    print("  4. cp .env.example .env  →  fill in GROQ_API_KEY")
    print("  5. Drop your law PDFs into data/public/")


if __name__ == "__main__":
    create_folder_structure(base_dir=".")