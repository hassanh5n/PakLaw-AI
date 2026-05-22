"""
Module: tagger
Purpose: Attaches metadata to each chunk (source_doc, law_domain, section_hint, etc.).
Inputs: List of chunk texts, source PDF filename, firm context.
Outputs: List of chunk dicts with metadata fields.
Dependencies: hashlib (standard library)
"""

import hashlib
import re

# Mapping from filename keywords to law_domain values
_DOMAIN_MAP = {
    "constitution":  "constitutional",
    "penal":         "criminal",
    "ppc":           "criminal",
    "criminal_proc": "criminal",
    "crpc":          "criminal",
    "family":        "family",
    "contract":      "civil",
    "labour":        "labour",
    "tax":           "taxation",
    "income_tax":    "taxation",
    "companies":     "corporate",
    "corporate":     "corporate",
}


def _detect_domain(filename: str) -> str:
    lower = filename.lower()
    for keyword, domain in _DOMAIN_MAP.items():
        if keyword in lower:
            return domain
    return "general"


def _detect_section_hint(chunk_text: str) -> str | None:
    # Match patterns like "Article 25", "Section 302", "Art. 4", "Sec. 17"
    pattern = r'(?i)^(article|section|art\.|sec\.)\s*(\d+[A-Z]?)'
    match = re.search(pattern, chunk_text.strip())
    if match:
        return f"{match.group(1).capitalize()} {match.group(2)}"
    return None


def _make_chunk_id(source_doc: str, position: int) -> str:
    raw = f"{source_doc}::{position}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


def tag_chunks(
    chunk_texts: list[str],
    source_doc: str,
    firm_id: str | None = None,
    access_level: str = "public",
) -> list[dict]:
    domain = _detect_domain(source_doc)
    tagged = []

    for i, text in enumerate(chunk_texts):
        tagged.append({
            "text":         text,
            "source_doc":   source_doc,
            "law_domain":   domain,
            "section_hint": _detect_section_hint(text),
            "firm_id":      firm_id,
            "access_level": access_level,
            "chunk_id":     _make_chunk_id(source_doc, i),
        })

    return tagged