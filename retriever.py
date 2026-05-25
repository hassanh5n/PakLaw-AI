"""
Module: retriever
Purpose: Full hybrid retrieval pipeline with query expansion, FAISS, BM25, access filtering, and re-ranking.
Inputs: Query string, user role, firm_id, and optional corpus routing arguments.
Outputs: Top-ranked, access-filtered chunk dicts.
Dependencies: faiss-cpu, rank-bm25, sentence-transformers, query_expander
"""

from __future__ import annotations

import json
import os
import pickle
import re
from typing import Iterable
from functools import lru_cache

import faiss
import numpy as np

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

try:
	from huggingface_hub.utils import disable_progress_bars

	disable_progress_bars()
except Exception:
	pass

try:
	from transformers.utils import logging as transformers_logging

	transformers_logging.set_verbosity_error()
except Exception:
	pass


PUBLIC_INDEX_NAME = "pakistan_law_public"
FIRM_INDEX_PREFIX = "firm_"
DEFAULT_INDEX_ROOT = "indexes"
FAISS_TOP_K = 25
BM25_TOP_K = 25
RERANK_TOP_K = 12
QUERY_VARIANT_LIMIT = 6
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Relevance scoring weights and thresholds
MIN_RERANK_SCORE = 0.1
PUBLIC_MIN_RERANK_SCORE = 0.25

# Weights for composing a per-chunk relevance score from available signals.
REL_WEIGHT_RERANK = 0.6
REL_WEIGHT_FAISS = 0.25
REL_WEIGHT_BM25 = 0.15

# Final cutoffs (0..1) for dropping irrelevant hits or marking low-confidence
IRRELEVANCE_CUTOFF = 0.12
LOW_CONF_CUTOFF = 0.30

_LEGAL_STOPWORDS = {
	"a",
	"an",
	"and",
	"are",
	"as",
	"be",
	"by",
	"for",
	"from",
	"how",
	"in",
	"into",
	"is",
	"it",
	"of",
	"on",
	"or",
	"that",
	"the",
	"their",
	"to",
	"under",
	"what",
	"when",
	"which",
	"who",
	"with",
	"without",
}


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


def _normalize_query_text(query: str) -> str:
	"""Normalize a query into a cleaner lexical search string."""

	cleaned = re.sub(r"[^\w\s]", " ", query.lower())
	return " ".join(cleaned.split())


def _strip_stopwords(query: str) -> str:
	"""Drop common filler words to create a recall-friendly variant."""

	tokens = [token for token in _normalize_query_text(query).split() if token not in _LEGAL_STOPWORDS]
	return " ".join(tokens)


def expand_query(
	query: str,
	api_key: str | None = None,
	model: str = "llama-3.1-8b-instant",
) -> list[str]:
	"""Expand a query into the original text plus model-provided alternate phrasings."""

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
						"Return exactly three alternative phrasings of the user's query. "
						"Do not answer the question, do not add explanations, and keep meaning unchanged. "
						"Return only a JSON array of three strings."
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
		return _dedupe_preserve_order([cleaned_query, *variants])[:QUERY_VARIANT_LIMIT]
	except Exception:
		return [cleaned_query]


def _build_query_variants(query: str, expand: bool = True) -> list[str]:
	"""Create a small set of high-recall query variants for retrieval."""

	variants = [query.strip()]
	normalized = _normalize_query_text(query)
	if normalized and normalized not in variants:
		variants.append(normalized)

	compressed = _strip_stopwords(query)
	if compressed and compressed not in variants:
		variants.append(compressed)

	if expand:
		variants.extend(expand_query(query))

	return _dedupe_preserve_order(variants)[:QUERY_VARIANT_LIMIT]


@lru_cache(maxsize=1)
def get_embedding_backend():
	"""Load the transformer embedding model required for query embedding."""
	try:
		from sentence_transformers import SentenceTransformer
	except ImportError as exc:
		raise RuntimeError(
			"sentence-transformers is required for retrieval. Install requirements.txt before running search."
		) from exc

	try:
		return SentenceTransformer(EMBEDDING_MODEL_NAME, local_files_only=True)
	except Exception as exc:
		try:
			return SentenceTransformer(EMBEDDING_MODEL_NAME)
		except Exception as fallback_exc:
			raise RuntimeError(f"Failed to load embedding model {EMBEDDING_MODEL_NAME}: {fallback_exc}") from fallback_exc


@lru_cache(maxsize=1)
def get_reranker_backend():
	"""Load the transformer cross-encoder required for reranking."""
	try:
		from sentence_transformers import CrossEncoder
	except ImportError as exc:
		raise RuntimeError(
			"sentence-transformers is required for reranking. Install requirements.txt before running search."
		) from exc

	try:
		return CrossEncoder(RERANKER_MODEL_NAME, local_files_only=True)
	except Exception as exc:
		try:
			return CrossEncoder(RERANKER_MODEL_NAME)
		except Exception as fallback_exc:
			raise RuntimeError(f"Failed to load reranker model {RERANKER_MODEL_NAME}: {fallback_exc}") from fallback_exc


def _normalize_text(text: str) -> str:
	return " ".join(text.lower().split())


def _tokenize_query(query: str) -> list[str]:
	return query.lower().split()


def _dedupe_by_chunk_id(items: Iterable[dict]) -> list[dict]:
	best_by_id: dict[str, dict] = {}

	for item in items:
		chunk_id = item.get("chunk_id")
		if not chunk_id:
			continue

		current = best_by_id.get(chunk_id)
		if current is None or item.get("combined_score", float("-inf")) > current.get("combined_score", float("-inf")):
			best_by_id[chunk_id] = item

	return sorted(best_by_id.values(), key=lambda record: record.get("combined_score", float("-inf")), reverse=True)


def _corpus_base_dir(index_root: str, corpus: str, firm_id: str | None = None) -> str:
	if corpus == "public":
		return os.path.join(index_root, "public")
	if corpus == "firm":
		if not firm_id:
			raise ValueError("firm_id is required for firm corpus retrieval")
		return os.path.join(index_root, "firms", firm_id)
	raise ValueError(f"Unsupported corpus: {corpus}")


def _index_name(corpus: str, firm_id: str | None = None) -> str:
	if corpus == "public":
		return PUBLIC_INDEX_NAME
	if corpus == "firm":
		if not firm_id:
			raise ValueError("firm_id is required for firm corpus retrieval")
		return f"{FIRM_INDEX_PREFIX}{firm_id}"
	raise ValueError(f"Unsupported corpus: {corpus}")


def _load_pickle(file_path: str):
	with open(file_path, "rb") as handle:
		return pickle.load(handle)


@lru_cache(maxsize=16)
def _load_corpus_assets(index_root: str, corpus: str, firm_id: str | None = None):
	base_dir = _corpus_base_dir(index_root, corpus, firm_id)
	index_name = _index_name(corpus, firm_id)

	faiss_path = os.path.join(base_dir, f"{index_name}.faiss")
	chunks_path = os.path.join(base_dir, f"{index_name}_chunks.pkl")
	bm25_path = os.path.join(base_dir, f"{index_name}_bm25.pkl")

	if not os.path.exists(faiss_path):
		raise FileNotFoundError(f"Missing FAISS index: {faiss_path}")
	if not os.path.exists(chunks_path):
		raise FileNotFoundError(f"Missing chunk metadata: {chunks_path}")
	if not os.path.exists(bm25_path):
		raise FileNotFoundError(f"Missing BM25 index: {bm25_path}")

	index = faiss.read_index(faiss_path)
	chunks = _load_pickle(chunks_path)
	bm25 = _load_pickle(bm25_path)

	return index, chunks, bm25


def _embed_query(query: str) -> np.ndarray:
	model = get_embedding_backend()
	try:
		embedding = model.encode([query], normalize_embeddings=True)
	except TypeError:
		embedding = model.encode([query])
	return np.asarray(embedding, dtype="float32")


def _faiss_hits(query: str, index, chunks: list[dict], corpus: str, firm_id: str | None, top_k: int = FAISS_TOP_K) -> list[dict]:
	query_vector = _embed_query(query)
	scores, indices = index.search(query_vector, top_k)
	hits: list[dict] = []

	for score, index_id in zip(scores[0], indices[0]):
		if index_id < 0 or index_id >= len(chunks):
			continue

		chunk = dict(chunks[index_id])
		chunk.update(
			{
				"corpus": corpus,
				"index_firm_id": firm_id,
				"faiss_score": float(score),
				"bm25_score": chunk.get("bm25_score"),
				"combined_score": float(score),
				"retrieval_method": "faiss",
			}
		)
		hits.append(chunk)

	return hits


def _bm25_hits(query: str, bm25, chunks: list[dict], corpus: str, firm_id: str | None, top_k: int = BM25_TOP_K) -> list[dict]:
	tokens = _tokenize_query(query)
	scores = np.asarray(bm25.get_scores(tokens), dtype="float32")
	if scores.size == 0:
		return []

	ranked_indices = np.argsort(scores)[::-1][:top_k]
	hits: list[dict] = []

	for index_id in ranked_indices:
		if index_id < 0 or index_id >= len(chunks):
			continue

		score = float(scores[index_id])
		chunk = dict(chunks[index_id])
		chunk.update(
			{
				"corpus": corpus,
				"index_firm_id": firm_id,
				"faiss_score": chunk.get("faiss_score"),
				"bm25_score": score,
				"combined_score": score,
				"retrieval_method": "bm25",
			}
		)
		hits.append(chunk)

	return hits


def _search_corpus(query_variants: list[str], corpus: str, index_root: str, firm_id: str | None = None) -> list[dict]:
	index, chunks, bm25 = _load_corpus_assets(index_root, corpus, firm_id)
	collected: list[dict] = []

	for query in query_variants:
		collected.extend(_faiss_hits(query, index, chunks, corpus, firm_id))
		collected.extend(_bm25_hits(query, bm25, chunks, corpus, firm_id))

	return _dedupe_by_chunk_id(collected)


def _search_corpus_bm25_only(query_variants: list[str], corpus: str, index_root: str, firm_id: str | None = None) -> list[dict]:
	_, chunks, bm25 = _load_corpus_assets(index_root, corpus, firm_id)
	collected: list[dict] = []

	for query in query_variants:
		collected.extend(_bm25_hits(query, bm25, chunks, corpus, firm_id))

	return _dedupe_by_chunk_id(collected)


def _access_level_allows(role: str, access_level: str) -> bool:
	role = role.lower()
	access_level = access_level.lower()

	if role == "public":
		return access_level == "public"
	if role in {"user", "admin"}:
		return True
	return False


def _apply_access_filter(candidates: list[dict], role: str, firm_id: str | None) -> list[dict]:
	filtered: list[dict] = []
	role_lower = role.lower()

	for candidate in candidates:
		candidate_access = str(candidate.get("access_level", "public")).lower()
		candidate_firm_id = candidate.get("firm_id")

		if candidate.get("corpus") == "firm":
			if not firm_id:
				continue
			if candidate_firm_id and candidate_firm_id != firm_id:
				continue

		if not _access_level_allows(role_lower, candidate_access):
			continue

		filtered.append(candidate)

	return filtered


def _rerank_candidates(query: str, candidates: list[dict], top_k: int = RERANK_TOP_K) -> list[dict]:
	if not candidates:
		return []

	reranker = get_reranker_backend()
	pairs = [(query, candidate.get("text", "")) for candidate in candidates]
	scores = reranker.predict(pairs)

	ranked: list[dict] = []
	for candidate, score in zip(candidates, scores):
		updated = dict(candidate)
		updated["rerank_score"] = float(score)
		updated["combined_score"] = float(score)
		ranked.append(updated)

	ranked.sort(key=lambda record: record.get("rerank_score", float("-inf")), reverse=True)
	return ranked[:top_k]


def _filter_by_relevance(ranked: list[dict]) -> list[dict]:
	"""Filter reranked candidates by configured relevance thresholds.

	This prevents returning low-confidence public documents for queries
	that the reranker judges as unrelated.
	"""
	if not ranked:
		return []

	# Gather raw signals
	rerank_scores = [float(r.get("rerank_score") or 0.0) for r in ranked]
	faiss_scores = [float(r.get("faiss_score") or 0.0) for r in ranked]
	bm25_scores = [float(r.get("bm25_score") or 0.0) for r in ranked]

	# Normalize each signal to 0..1 across the ranked list to make them comparable.
	def _normalize(values: list[float]) -> list[float]:
		mx = max(values) if values else 0.0
		mn = min(values) if values else 0.0
		span = mx - mn if mx - mn > 1e-9 else 1.0
		return [(v - mn) / span for v in values]

	norm_rerank = _normalize(rerank_scores)
	norm_faiss = _normalize(faiss_scores)
	norm_bm25 = _normalize(bm25_scores)

	filtered: list[dict] = []
	for i, rec in enumerate(ranked):
		# Compose a relevance score
		rel = (
			REL_WEIGHT_RERANK * norm_rerank[i]
			+ REL_WEIGHT_FAISS * norm_faiss[i]
			+ REL_WEIGHT_BM25 * norm_bm25[i]
		)

		# Attach the computed relevance for UI and downstream logic
		rec = dict(rec)
		rec["relevance_score"] = float(max(0.0, min(rel, 1.0)))

		# Determine whether to accept, mark low-confidence, or drop
		if rec.get("corpus") == "public":
			# require slightly higher relevance to show public sources
			cutoff = PUBLIC_MIN_RERANK_SCORE * 0.9
		else:
			cutoff = MIN_RERANK_SCORE * 0.9

		# Drop truly irrelevant results
		if rec["relevance_score"] < IRRELEVANCE_CUTOFF:
			continue

		# Mark low confidence if below threshold
		if rec["relevance_score"] < LOW_CONF_CUTOFF:
			rec["low_confidence"] = True

		filtered.append(rec)

	# Sort by the computed relevance_score descending
	filtered.sort(key=lambda r: r.get("relevance_score", 0.0), reverse=True)
	return filtered


def get_accessible_corpora(role: str, firm_id: str | None = None) -> list[str]:
	"""
	Return the corpora a user role may search.

	Args:
		role: User role string.
		firm_id: Optional firm identifier used to unlock firm index access.

	Returns:
		Ordered list of corpora to search.
	"""

	role_lower = role.lower()
	if role_lower == "public":
		return ["public"]
	if role_lower in {"user", "admin"}:
		return ["public", "firm"] if firm_id else ["public"]
	return ["public"]


def retrieve_chunks(
	query: str,
	role: str = "public",
	firm_id: str | None = None,
	index_root: str = DEFAULT_INDEX_ROOT,
	expand: bool = True,
	top_k: int = RERANK_TOP_K,
) -> list[dict]:
	"""
	Run the full hybrid retrieval pipeline for a query.

	Args:
		query: User query string.
		role: Access role for filtering.
		firm_id: Firm identifier for firm-scoped retrieval.
		index_root: Root directory containing index folders.
		expand: Whether to run query expansion before searching.
		top_k: Number of reranked results to return.

	Returns:
		Ranked chunk dictionaries with retrieval metadata.
	"""

	cleaned_query = query.strip()
	if not cleaned_query:
		return []

	query_variants = _build_query_variants(cleaned_query, expand=expand)
	if not query_variants:
		query_variants = [cleaned_query]

	accessible_corpora = get_accessible_corpora(role, firm_id)
	all_candidates: list[dict] = []

	for corpus in accessible_corpora:
		corpus_firm_id = firm_id if corpus == "firm" else None
		all_candidates.extend(_search_corpus(query_variants, corpus, index_root, corpus_firm_id))

	merged_candidates = _dedupe_by_chunk_id(all_candidates)
	filtered_candidates = _apply_access_filter(merged_candidates, role, firm_id)

	# Rerank and then filter by configured relevance thresholds to avoid returning
	# low-confidence public documents for irrelevant queries.
	reranked = _rerank_candidates(cleaned_query, filtered_candidates, top_k=max(top_k, RERANK_TOP_K))
	relevant = _filter_by_relevance(reranked)

	# If enough relevant results passed thresholds, return them.
	if relevant:
		return relevant[:top_k]

	# If the user can access firm results, try firm-only candidates first.
	if role.lower() in {"user", "admin"} and firm_id:
		firm_candidates = [c for c in filtered_candidates if c.get("corpus") == "firm"]
		if firm_candidates:
			firer = _rerank_candidates(cleaned_query, firm_candidates, top_k=top_k)
			firm_relevant = _filter_by_relevance(firer)
			if firm_relevant:
				return firm_relevant[:top_k]
			# Fall back to firm reranked hits but mark as low confidence
			low_conf_firm: list[dict] = []
			for rec in firer[:top_k]:
				copy = dict(rec)
				copy["low_confidence"] = True
				copy["note"] = "Low-confidence firm match (below relevance thresholds)"
				low_conf_firm.append(copy)
			return low_conf_firm

	# As a last resort, return top reranked candidates but mark them low-confidence
	low_conf: list[dict] = []
	for rec in reranked[:top_k]:
		copy = dict(rec)
		copy["low_confidence"] = True
		copy["note"] = "Low-confidence match (below relevance thresholds)"
		low_conf.append(copy)
	return low_conf


def retrieve_bm25_only(
	query: str,
	role: str = "public",
	firm_id: str | None = None,
	index_root: str = DEFAULT_INDEX_ROOT,
	expand: bool = True,
	top_k: int = RERANK_TOP_K,
) -> list[dict]:
	"""
	Run the BM25-only baseline without FAISS or reranking.

	Args:
		query: User query string.
		role: Access role for filtering.
		firm_id: Firm identifier for firm-scoped retrieval.
		index_root: Root directory containing index folders.
		expand: Whether to run query expansion before searching.
		top_k: Number of results to return.

	Returns:
		BM25-ranked chunk dictionaries with retrieval metadata.
	"""

	cleaned_query = query.strip()
	if not cleaned_query:
		return []

	query_variants = _build_query_variants(cleaned_query, expand=expand)
	if not query_variants:
		query_variants = [cleaned_query]

	accessible_corpora = get_accessible_corpora(role, firm_id)
	all_candidates: list[dict] = []

	for corpus in accessible_corpora:
		corpus_firm_id = firm_id if corpus == "firm" else None
		all_candidates.extend(_search_corpus_bm25_only(query_variants, corpus, index_root, corpus_firm_id))

	merged_candidates = _dedupe_by_chunk_id(all_candidates)
	filtered_candidates = _apply_access_filter(merged_candidates, role, firm_id)
	return filtered_candidates[:top_k]



