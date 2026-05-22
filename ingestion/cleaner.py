"""
Module: cleaner
Purpose: Cleans raw extracted text by removing headers, footers, page numbers, and OCR noise.
Inputs: Raw text string from extractor.
Outputs: Cleaned text string.
Dependencies: re (standard library)
"""

import re


def clean_text(raw_text: str) -> str:
    text = raw_text

    # Remove standalone page numbers (e.g. "- 12 -", "Page 12", "12\n")
    text = re.sub(r'(?i)\bpage\s+\d+\b', '', text)
    text = re.sub(r'\b-\s*\d+\s*-\b', '', text)
    text = re.sub(r'(?m)^\s*\d+\s*$', '', text)  # Line that is only a number

    # Remove common header/footer patterns found in Pakistani legal PDFs
    text = re.sub(r'(?i)(national assembly of pakistan|senate of pakistan)', '', text)
    text = re.sub(r'(?i)(islamabad\s*,?\s*the\s+\d+)', '', text)
    text = re.sub(r'(?i)(gazette of pakistan)', '', text)

    # Collapse excessive whitespace while preserving paragraph breaks
    text = re.sub(r'\n{3,}', '\n\n', text)   # 3+ newlines → 2 newlines
    text = re.sub(r'[ \t]{2,}', ' ', text)   # Multiple spaces/tabs → one space
    text = re.sub(r' \n', '\n', text)         # Trailing spaces before newline

    # Remove null bytes and non-printable characters (common OCR artifacts)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    return text.strip()