"""
Module: prompts
Purpose: Stores the locked legal system prompt and prompt-building helpers for generation.
Inputs: Query string and retrieved chunk dictionaries.
Outputs: SYSTEM_PROMPT string and a formatted user prompt.
Dependencies: None
"""

from __future__ import annotations

SYSTEM_PROMPT = (
	"You are a legal research assistant for Pakistani law.\n"
	"You must answer using the retrieved context as your primary evidence.\n"
	"Always cite the specific article, section, or document name that supports your answer.\n"
	"If the retrieved context is incomplete but still points to a likely provision, give the most likely legal answer instead of refusing.\n"
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
	"""
	Build the user-facing prompt for the Groq chat completion.

	Args:
		query: The original user question.
		chunks: Retrieved chunk dictionaries to ground the answer.
		max_chunks: Maximum number of chunks to include in the prompt.

	Returns:
		A formatted prompt string with the question and evidence context.
	"""

	selected_chunks = chunks[:max_chunks]
	context_blocks = [
		_format_chunk(chunk, index + 1)
		for index, chunk in enumerate(selected_chunks)
	]
	context_text = "\n\n".join(context_blocks) if context_blocks else "No relevant context was retrieved."

	return (
		f"Question: {query.strip()}\n\n"
		"Use the retrieved context as primary evidence. If the context is incomplete, still provide the most likely legal answer and cite the evidence you used.\n\n"
		f"Context:\n{context_text}\n\n"
		"Write a concise legal answer and cite the supporting source doc, section hint, "
		"or bracketed context item number for every material claim."
	)

