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

	# Build candidate model list: explicit param > env GROQ_MODEL (comma-separated) > sensible defaults
	env_model = os.getenv("GROQ_MODEL")
	if model:
		candidates = [model]
	elif env_model:
		candidates = [m.strip() for m in env_model.split(",") if m.strip()]
	else:
		candidates = [
			"llama-3.1-8b-instant",
			"llama-3.3-70b-versatile",
			"openai/gpt-oss-20b",
			"openai/gpt-oss-120b",
		]

	last_exc = None
	try:
		from groq import Groq
	except Exception as exc:
		last_exc = exc
		Groq = None

	if Groq is not None:
		client = Groq(api_key=resolved_api_key)
		for candidate in candidates:
			try:
				response = client.chat.completions.create(
					model=candidate,
					temperature=0.1,
					messages=[
						{"role": "system", "content": SYSTEM_PROMPT},
						{"role": "user", "content": build_user_prompt(query, chunks)},
					],
				)
				answer = response.choices[0].message.content or ""
				answer = answer.strip()
				if answer:
					return answer
			except Exception as exc:
				last_exc = exc

	if last_exc is not None:
		raise RuntimeError(f"Failed to generate answer with Groq: {last_exc}") from last_exc
	raise RuntimeError("Failed to generate answer with Groq: no supported model produced a response.")

