"""
Module: vector_backends
Purpose: Provide offline-safe embedding and reranking backends with graceful fallbacks.
Inputs: Text chunks, query text, and text pairs for reranking.
Outputs: SentenceTransformer/CrossEncoder backends when available, otherwise deterministic local fallbacks.
Dependencies: numpy, sentence-transformers when available, standard library.
"""

from __future__ import annotations

import hashlib
import os
import re
import zlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

import numpy as np


EMBEDDING_DIM = 384
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass
class HashingEmbeddingBackend:
	"""Deterministic local fallback that maps tokens into a fixed vector space."""

	backend_name: str = "local-hash"
	dimension: int = EMBEDDING_DIM

	def _embed_one(self, text: str) -> np.ndarray:
		vector = np.zeros(self.dimension, dtype="float32")
		tokens = _TOKEN_RE.findall(text.lower())
		if not tokens:
			return vector

		for token in tokens:
			hash_value = zlib.crc32(token.encode("utf-8")) & 0xFFFFFFFF
			index = hash_value % self.dimension
			sign = -1.0 if hash_value & 1 else 1.0
			vector[index] += sign

		norm = float(np.linalg.norm(vector))
		if norm > 0.0:
			vector /= norm
		return vector

	def encode(
		self,
		texts: Iterable[str],
		batch_size: int | None = None,
		show_progress_bar: bool | None = None,
		normalize_embeddings: bool = True,
	):
		vectors = [self._embed_one(text or "") for text in texts]
		if not vectors:
			return np.zeros((0, self.dimension), dtype="float32")
		matrix = np.asarray(vectors, dtype="float32")
		if normalize_embeddings:
			norms = np.linalg.norm(matrix, axis=1, keepdims=True)
			norms[norms == 0.0] = 1.0
			matrix = matrix / norms
		return matrix


@dataclass
class HeuristicReranker:
	"""Simple local reranker used when the transformer cross-encoder cannot load."""

	backend_name: str = "local-heuristic"

	def predict(self, pairs: Iterable[tuple[str, str]]):
		scores: list[float] = []
		for query, text in pairs:
			query_tokens = set(_TOKEN_RE.findall((query or "").lower()))
			text_tokens = set(_TOKEN_RE.findall((text or "").lower()))
			if not query_tokens or not text_tokens:
				scores.append(0.0)
				continue
			shared = len(query_tokens & text_tokens)
			union = len(query_tokens | text_tokens)
			scores.append(shared / union if union else 0.0)
		return np.asarray(scores, dtype="float32")


def _normalize_mode(mode: str | None, env_name: str, fallback: str = "auto") -> str:
	value = (mode or os.getenv(env_name, fallback)).strip().lower()
	if value in {"local", "hash", "hashing", "fallback"}:
		return "local"
	if value in {"transformer", "miniLM", "minilm", "semantic", "cross-encoder", "crossencoder"}:
		return "transformer"
	return "auto"


@lru_cache(maxsize=4)
def get_embedding_backend(mode: str | None = None):
	"""Return the requested embedding backend, defaulting to transformer-first auto selection."""

	normalized_mode = _normalize_mode(mode, "PAKLAW_EMBEDDING_BACKEND")
	if normalized_mode == "local":
		return HashingEmbeddingBackend()

	if normalized_mode == "transformer":
		os.environ.setdefault("HF_HUB_OFFLINE", "1")
		os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
		from sentence_transformers import SentenceTransformer

		return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

	try:
		os.environ.setdefault("HF_HUB_OFFLINE", "1")
		os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
		from sentence_transformers import SentenceTransformer

		return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
	except Exception:
		return HashingEmbeddingBackend()


@lru_cache(maxsize=4)
def get_reranker_backend(mode: str | None = None):
	"""Return the requested reranking backend, defaulting to transformer-first auto selection."""

	normalized_mode = _normalize_mode(mode, "PAKLAW_RERANK_BACKEND")
	if normalized_mode == "local":
		return HeuristicReranker()

	if normalized_mode == "transformer":
		os.environ.setdefault("HF_HUB_OFFLINE", "1")
		os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
		from sentence_transformers import CrossEncoder

		return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

	try:
		os.environ.setdefault("HF_HUB_OFFLINE", "1")
		os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
		from sentence_transformers import CrossEncoder

		return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
	except Exception:
		return HeuristicReranker()
