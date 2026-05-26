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


DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
MIN_RETRIEVED_CHUNKS_FOR_CONFIDENT_ANSWER = 3

SYSTEM_PROMPT = (
	"You are a legal research assistant for Pakistani law.\n"
	"You must answer using the retrieved context as your primary evidence.\n"
	"Always cite the specific article, section, document name, or chunk number that supports your answer.\n"
	"If the retrieved context is incomplete, say so briefly and answer from the best available evidence instead of refusing.\n"
	"Never fabricate citations.\n"
	"Keep answers clear enough for a non-lawyer to understand."
)


def _format_chunk(chunk: dict, index: int) -> str:
	text = str(chunk.get("text", "")).strip()
	source_doc = chunk.get("source_doc", "unknown document")
	section_hint = chunk.get("section_hint") or "N/A"
	law_domain = chunk.get("law_domain", "unknown")
	access_level = chunk.get("access_level", "unknown")
	firm_id = chunk.get("firm_id") or "public"

	return (
		f"[{index}] Source: {source_doc}\n"
		f"Section hint: {section_hint}\n"
		f"Law domain: {law_domain}\n"
		f"Access level: {access_level}\n"
		f"Firm: {firm_id}\n"
		f"Text: {text}"
	)


def build_user_prompt(query: str, chunks: list[dict], max_chunks: int = 10) -> str:
	"""Build the user-facing prompt for the Groq chat completion."""

	selected_chunks = chunks[:max_chunks]
	context_blocks = [_format_chunk(chunk, index + 1) for index, chunk in enumerate(selected_chunks)]
	context_text = "\n\n".join(context_blocks) if context_blocks else "No relevant context was retrieved."
	evidence_note = ""
	if len(selected_chunks) and len(selected_chunks) < MIN_RETRIEVED_CHUNKS_FOR_CONFIDENT_ANSWER:
		evidence_note = (
			f"Evidence note: only {len(selected_chunks)} retrieved chunk(s) were available, so the answer may be incomplete.\n\n"
		)

	return (
		f"{evidence_note}"
		f"Question: {query.strip()}\n\n"
		"Use the retrieved context as primary evidence. If the context is incomplete, still provide the most likely legal answer and cite the evidence you used.\n\n"
		f"Context:\n{context_text}\n\n"
		"Write a concise legal answer and cite the supporting source doc, section hint, "
		"or bracketed context item number for every material claim. If evidence is thin, say that plainly."
	)


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

	no_context = False
	if not chunks:
		# Instead of failing, allow the LLM to produce a cautious, non-assertive answer
		# that clearly states no authoritative sources were found in the indexed corpus.
		no_context = True

	# Prefer explicit API key, otherwise use env
	load_dotenv()
	resolved_api_key = api_key or os.getenv("GROQ_API_KEY")
	if not resolved_api_key:
		# If no API key is configured, allow a graceful fallback message instead of hard error.
		resolved_api_key = None

	try:
		from groq import Groq
	except Exception as exc:
		raise RuntimeError(f"Failed to import Groq client: {exc}") from exc

	resolved_model = model or DEFAULT_GROQ_MODEL
	client = None
	response = None
	if resolved_api_key:
		client = Groq(api_key=resolved_api_key)
		try:
			# If no context was retrieved, instruct the model to produce a cautious, best-effort
			# answer and explicitly state uncertainty and next steps.
			user_prompt = build_user_prompt(query, chunks)
			if no_context:
				user_prompt = (
					"No relevant documents were found in the indexed corpus. "
					"Do not invent citations. Provide a cautious, high-level legal explanation of the likely issues, "
					"state the uncertainty, and suggest concrete next steps (e.g., consult a lawyer, search specific statutes).\n\n"
					+ user_prompt
				)

			response = client.chat.completions.create(
				model=resolved_model,
				temperature=0.15 if no_context else 0.1,
				messages=[
					{"role": "system", "content": SYSTEM_PROMPT},
					{"role": "user", "content": user_prompt},
				],
			)
		except Exception as exc:
			raise RuntimeError(f"Failed to generate answer with Groq model {resolved_model}: {exc}") from exc

	# If no API key / client is available, fall back to a safe non-assertive message.
	if response is None:
		if no_context:
			return (
				"I could not find any directly relevant documents in the indexed corpus to answer your question. "
				"I can offer general information based on common legal principles, but this is not a substitute for professional legal advice. "
				"If you need an authoritative answer, consider searching specific statutes or consulting a qualified lawyer."
			)
		else:
			raise RuntimeError("GROQ_API_KEY is not configured. Set it in the environment or pass api_key.")

	answer = (response.choices[0].message.content or "").strip()
	if not answer:
		raise RuntimeError(f"Groq model {resolved_model} returned an empty answer.")

	if 0 < len(chunks) < MIN_RETRIEVED_CHUNKS_FOR_CONFIDENT_ANSWER:
		answer = (
			f"Evidence is limited: the answer below is based on {len(chunks)} retrieved chunk(s). "
			"Use it as a best-effort answer and verify the cited sources.\n\n"
			+ answer
		)

	return answer

