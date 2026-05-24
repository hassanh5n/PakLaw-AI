"""
Module: extractor
Purpose: Extracts raw text from PDF files using PyMuPDF.
Inputs: Path to a PDF file.
Outputs: List of (page_number, raw_text) tuples.
Dependencies: PyMuPDF (fitz)
"""

import fitz


def extract_text_from_pdf(pdf_path: str) -> list[tuple[int, str]]:
    """Extract non-empty page text from a PDF as (page_number, text) tuples."""
    pages = []
    doc = fitz.open(pdf_path)

    for page_index in range(len(doc)):
        page = doc[page_index]
        raw_text = page.get_text()

        # Only keep pages that have actual text content
        if raw_text.strip():
            pages.append((page_index + 1, raw_text))

    doc.close()
    return pages


def is_text_extractable(pdf_path: str) -> bool:
    """Return True when at least 10% of the PDF pages contain meaningful text."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    text_pages = 0

    for page in doc:
        if len(page.get_text().strip()) > 50:  # 50 chars = meaningful content
            text_pages += 1

    doc.close()
    return (text_pages / total_pages) >= 0.1 if total_pages > 0 else False