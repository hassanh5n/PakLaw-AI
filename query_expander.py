"""
Module: query_expander
Purpose: Expands a user query into three semantically similar search queries.
Inputs: Original query string and optional Groq API configuration.
Outputs: List of 3 query strings (original + 2 expansions).
Dependencies: groq, python-dotenv
"""

from __future__ import annotations

import json
import os
import re
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


def _heuristic_expansions(query: str) -> list[str]:
	base = query.strip().rstrip("? .")
	variants = [
		base,
		f"What legal provision governs {base.lower()} in Pakistani law?",
		f"Find the relevant article, section, or rule about {base.lower()}.",
	]
	return _dedupe_preserve_order(variants)[:3]


def _parse_model_output(raw_text: str, original_query: str) -> list[str]:
	text = raw_text.strip()

	if not text:
		return _heuristic_expansions(original_query)

	json_match = re.search(r"\[[\s\S]*\]", text)
	if json_match:
		try:
			parsed = json.loads(json_match.group(0))
			if isinstance(parsed, list):
				variants = [str(item) for item in parsed if str(item).strip()]
				return _dedupe_preserve_order([original_query, *variants])[:3]
		except json.JSONDecodeError:
			pass

	lines = [line.strip("-• \t") for line in text.splitlines() if line.strip()]
	variants = [line for line in lines if line and not line.lower().startswith("json")]
	if len(variants) >= 2:
		return _dedupe_preserve_order([original_query, *variants])[:3]

	return _heuristic_expansions(original_query)


def expand_query(
	query: str,
	api_key: str | None = None,
	model: str = "llama3-8b-8192",
) -> list[str]:
	"""
	Expand a query into the original text plus two alternate phrasings.

	Args:
		query: User question or search string.
		api_key: Optional Groq API key. Falls back to the GROQ_API_KEY env var.
		model: Groq model name used for expansion.

	Returns:
		A list of exactly three query strings when possible, otherwise the best
		unique variants available.
	"""

	load_dotenv()
	cleaned_query = query.strip()
	if not cleaned_query:
		return []

	resolved_api_key = api_key or os.getenv("GROQ_API_KEY")
	if not resolved_api_key:
		return _heuristic_expansions(cleaned_query)

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
						"Return the result as a JSON array of two strings."
					),
				},
				{
					"role": "user",
					"content": cleaned_query,
				},
			],
		)
		expanded_text = response.choices[0].message.content or ""
		return _parse_model_output(expanded_text, cleaned_query)
	except Exception:
		return _heuristic_expansions(cleaned_query)

