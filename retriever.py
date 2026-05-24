"""
Module: retriever
Purpose: Full hybrid retrieval pipeline with query expansion, FAISS, BM25, access filtering, and re-ranking.
Inputs: Query string, user role, firm_id, and optional corpus routing arguments.
Outputs: Top-ranked, access-filtered chunk dicts.
Dependencies: faiss-cpu, rank-bm25, sentence-transformers, query_expander
"""

from __future__ import annotations

import os
import pickle
import json
from typing import Iterable
from functools import lru_cache

import faiss
import numpy as np

from query_expander import expand_query
from vector_backends import get_embedding_backend, get_reranker_backend


PUBLIC_INDEX_NAME = "pakistan_law_public"
FIRM_INDEX_PREFIX = "firm_"
DEFAULT_INDEX_ROOT = "indexes"
FAISS_TOP_K = 15
BM25_TOP_K = 15
RERANK_TOP_K = 10
_ACCESS_LEVEL_ORDER = {"public": 0, "associate": 1, "partner": 2}


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

	backend_path = os.path.join(base_dir, f"{index_name}_backend.json")
	embedding_backend = None
	if os.path.exists(backend_path):
		try:
			with open(backend_path, "r", encoding="utf-8") as handle:
				embedding_backend = json.load(handle).get("embedding_backend")
		except Exception:
			embedding_backend = None

	return index, chunks, bm25, embedding_backend


def _embed_query(query: str, embedding_backend: str | None = None) -> np.ndarray:
	model = get_embedding_backend("local" if embedding_backend == "local-hash" else embedding_backend)
	try:
		embedding = model.encode([query], normalize_embeddings=True)
	except TypeError:
		embedding = model.encode([query])
	return np.asarray(embedding, dtype="float32")


def _faiss_hits(query: str, index, chunks: list[dict], corpus: str, firm_id: str | None, embedding_backend: str | None, top_k: int = FAISS_TOP_K) -> list[dict]:
	query_vector = _embed_query(query, embedding_backend)
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
	index, chunks, bm25, embedding_backend = _load_corpus_assets(index_root, corpus, firm_id)
	collected: list[dict] = []

	for query in query_variants:
		collected.extend(_faiss_hits(query, index, chunks, corpus, firm_id, embedding_backend))
		collected.extend(_bm25_hits(query, bm25, chunks, corpus, firm_id))

	return _dedupe_by_chunk_id(collected)


def _search_corpus_bm25_only(query_variants: list[str], corpus: str, index_root: str, firm_id: str | None = None) -> list[dict]:
	_, chunks, bm25, _ = _load_corpus_assets(index_root, corpus, firm_id)
	collected: list[dict] = []

	for query in query_variants:
		collected.extend(_bm25_hits(query, bm25, chunks, corpus, firm_id))

	return _dedupe_by_chunk_id(collected)


def _access_level_allows(role: str, access_level: str) -> bool:
	role = role.lower()
	access_level = access_level.lower()

	if role == "public":
		return access_level == "public"
	if role == "associate":
		return _ACCESS_LEVEL_ORDER.get(access_level, 0) <= _ACCESS_LEVEL_ORDER["associate"]
	if role in {"partner", "admin"}:
		return access_level in _ACCESS_LEVEL_ORDER
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
	if role_lower in {"associate", "partner", "admin"}:
		if not firm_id:
			raise ValueError("firm_id is required for firm-aware roles")
		return ["public", "firm"]
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

	query_variants = expand_query(cleaned_query) if expand else [cleaned_query]
	if not query_variants:
		query_variants = [cleaned_query]

	accessible_corpora = get_accessible_corpora(role, firm_id)
	all_candidates: list[dict] = []

	for corpus in accessible_corpora:
		corpus_firm_id = firm_id if corpus == "firm" else None
		all_candidates.extend(_search_corpus(query_variants, corpus, index_root, corpus_firm_id))

	merged_candidates = _dedupe_by_chunk_id(all_candidates)
	filtered_candidates = _apply_access_filter(merged_candidates, role, firm_id)
	return _rerank_candidates(cleaned_query, filtered_candidates, top_k=top_k)


def retrieve_public_chunks(query: str, index_root: str = DEFAULT_INDEX_ROOT, top_k: int = RERANK_TOP_K) -> list[dict]:
	"""
	Convenience wrapper for public-only retrieval.

	Args:
		query: User query string.
		index_root: Root directory containing index folders.
		top_k: Number of reranked results to return.

	Returns:
		Ranked public chunks.
	"""

	return retrieve_chunks(query=query, role="public", firm_id=None, index_root=index_root, expand=True, top_k=top_k)


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

	query_variants = expand_query(cleaned_query) if expand else [cleaned_query]
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


def retrieve_firm_chunks(
	query: str,
	firm_id: str,
	role: str = "partner",
	index_root: str = DEFAULT_INDEX_ROOT,
	top_k: int = RERANK_TOP_K,
) -> list[dict]:
	"""
	Convenience wrapper for firm-aware retrieval.

	Args:
		query: User query string.
		firm_id: Firm identifier whose index may be searched.
		role: Role used to enforce access-level filtering.
		index_root: Root directory containing index folders.
		top_k: Number of reranked results to return.

	Returns:
		Ranked chunks from the public and matching firm corpora.
	"""

	return retrieve_chunks(query=query, role=role, firm_id=firm_id, index_root=index_root, expand=True, top_k=top_k)

