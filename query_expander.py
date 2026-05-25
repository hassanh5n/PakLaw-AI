"""
Module: query_expander
Purpose: Expands a user query into semantically similar search queries.
Inputs: Original query string and optional Groq API configuration.
Outputs: Original query plus parsed model expansions, or the original query alone.
Dependencies: groq, python-dotenv
"""

from __future__ import annotations

import json
import os
from typing import Iterable

from dotenv import load_dotenv


def _dedupe_preserve_order(items: Iterable[str]) -> list[str]:
	seen: set[str] = set()
	deduped: list[str] = []

	for item in items:
		candidate = item.strip()
		if not candidate:
			continue
		key = candidate.casefold()
		if key in seen:
			continue
		seen.add(key)
		deduped.append(candidate)

	return deduped


def expand_query(
	query: str,
	api_key: str | None = None,
	model: str = "llama-3.1-8b-instant",
) -> list[str]:
	"""
	Expand a query into the original text plus model-provided alternate phrasings.

	Args:
		query: User question or search string.
		api_key: Optional Groq API key. Falls back to the GROQ_API_KEY env var.
		model: Groq model name used for expansion.

	Returns:
		A deduplicated list beginning with the original query. If expansion fails,
		returns the original query as a single-item list.
	"""

	load_dotenv()
	cleaned_query = query.strip()
	if not cleaned_query:
		return []

	resolved_api_key = api_key or os.getenv("GROQ_API_KEY")
	if not resolved_api_key:
		return [cleaned_query]

	try:
		from groq import Groq

		client = Groq(api_key=resolved_api_key)
		response = client.chat.completions.create(
			model=model,
			temperature=0.2,
			messages=[
				{
					"role": "system",
					"content": (
						"You rewrite legal research queries for Pakistani law search. "
						"Return exactly two alternative phrasings of the user's query. "
						"Do not answer the question, do not add explanations, and keep meaning unchanged. "
						"Return only a JSON array of two strings."
					),
				},
				{"role": "user", "content": cleaned_query},
			],
		)
		raw_text = response.choices[0].message.content or ""
		parsed = json.loads(raw_text)
		if not isinstance(parsed, list):
			return [cleaned_query]
		variants = [str(item) for item in parsed if str(item).strip()]
		return _dedupe_preserve_order([cleaned_query, *variants])[:3]
	except Exception:
		return [cleaned_query]
