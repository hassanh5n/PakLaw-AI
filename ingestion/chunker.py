"""
Module: chunker
Purpose: Splits cleaned text into overlapping chunks using LangChain RecursiveCharacterTextSplitter.
Inputs: Cleaned text string.
Outputs: List of chunk text strings.
Dependencies: langchain_text_splitters when available, otherwise a local fallback splitter.
"""

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    class RecursiveCharacterTextSplitter:
        def __init__(self, chunk_size: int, chunk_overlap: int, separators: list[str]):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
            self.separators = separators

        def split_text(self, text: str) -> list[str]:
            cleaned = " ".join(text.split())
            if not cleaned:
                return []

            chunks: list[str] = []
            start = 0
            length = len(cleaned)

            while start < length:
                end = min(start + self.chunk_size, length)
                window = cleaned[start:end]

                if end < length:
                    for separator in self.separators[:-1]:
                        if not separator:
                            continue
                        cut = window.rfind(separator)
                        if cut > self.chunk_size // 2:
                            end = start + cut + len(separator)
                            window = cleaned[start:end]
                            break

                chunk = window.strip()
                if chunk:
                    chunks.append(chunk)

                if end >= length:
                    break

                start = max(end - self.chunk_overlap, start + 1)

            return chunks

# Fixed splitter — do NOT change chunk_size or chunk_overlap per guidelines.md
_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=100,
    # Try natural boundaries first: paragraphs → lines → sentences → words
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_text(cleaned_text: str) -> list[str]:
    """Split cleaned text into overlapping chunks and drop very short fragments."""
    if not cleaned_text.strip():
        return []

    chunks = _SPLITTER.split_text(cleaned_text)

    # Filter out chunks that are too short to be meaningful (< 50 chars)
    chunks = [c.strip() for c in chunks if len(c.strip()) >= 50]

    return chunks