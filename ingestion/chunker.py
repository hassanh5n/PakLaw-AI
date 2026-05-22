"""
Module: chunker
Purpose: Splits cleaned text into overlapping chunks using LangChain RecursiveCharacterTextSplitter.
Inputs: Cleaned text string.
Outputs: List of chunk text strings.
Dependencies: langchain
"""

from langchain.text_splitter import RecursiveCharacterTextSplitter
# Fixed splitter — do NOT change chunk_size or chunk_overlap per guidelines.md
_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=100,
    # Try natural boundaries first: paragraphs → lines → sentences → words
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_text(cleaned_text: str) -> list[str]:
    if not cleaned_text.strip():
        return []

    chunks = _SPLITTER.split_text(cleaned_text)

    # Filter out chunks that are too short to be meaningful (< 50 chars)
    chunks = [c.strip() for c in chunks if len(c.strip()) >= 50]

    return chunks