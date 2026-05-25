"""
Module: generator
Purpose: Builds the grounded Groq prompt and generates cited answers from retrieved chunks.
Inputs: Original query string and a list of ranked chunk dictionaries.
Outputs: Answer string with citations.
Dependencies: groq, prompts, python-dotenv
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from prompts import SYSTEM_PROMPT, build_user_prompt


DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


def generate_answer(
	query: str,
	chunks: list[dict],
	api_key: str | None = None,
	model: str | None = None,
) -> str:
	"""
	Generate a grounded answer for the supplied query.

	Args:
		query: User question string.
		chunks: Ranked retrieval results to ground the answer.
		api_key: Optional Groq API key. Falls back to the GROQ_API_KEY env var.
		model: Groq model name used for generation.

	Returns:
		A legal answer string with citations.
	"""

	if not chunks:
		raise RuntimeError("No retrieved chunks are available for generation.")

	# Prefer explicit API key, otherwise use env
	load_dotenv()
	resolved_api_key = api_key or os.getenv("GROQ_API_KEY")
	if not resolved_api_key:
		raise RuntimeError("GROQ_API_KEY is not configured. Set it in the environment or pass api_key.")

	try:
		from groq import Groq
	except Exception as exc:
		raise RuntimeError(f"Failed to import Groq client: {exc}") from exc

	resolved_model = model or DEFAULT_GROQ_MODEL
	client = Groq(api_key=resolved_api_key)

	try:
		response = client.chat.completions.create(
			model=resolved_model,
			temperature=0.1,
			messages=[
				{"role": "system", "content": SYSTEM_PROMPT},
				{"role": "user", "content": build_user_prompt(query, chunks)},
			],
		)
	except Exception as exc:
		raise RuntimeError(f"Failed to generate answer with Groq model {resolved_model}: {exc}") from exc

	answer = (response.choices[0].message.content or "").strip()
	if not answer:
		raise RuntimeError(f"Groq model {resolved_model} returned an empty answer.")
	return answer

