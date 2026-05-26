from __future__ import annotations

from functools import partial

from anyio import to_thread
from fastapi import APIRouter, Depends

from auth import get_current_user, require_roles
from config import INDEX_ROOT
from models.schemas import SearchRequest, SearchResponse, SourceChunk

from access_control import UserRecord

router = APIRouter(prefix="/search", tags=["search"])


def _confidence_for(chunks: list[dict]) -> str:
    if not chunks:
        return "low"
    if any(chunk.get("low_confidence") for chunk in chunks):
        return "low"
    best_score = max(float(chunk.get("relevance_score") or 0.0) for chunk in chunks)
    if best_score >= 0.68:
        return "high"
    if best_score >= 0.35:
        return "medium"
    return "low"


async def _run_search(
    *,
    mode: str,
    payload: SearchRequest,
    role: str,
    firm_id: str | None,
    corpora: list[str],
) -> SearchResponse:
    from generator import generate_answer
    from retriever import retrieve_chunks

    retriever_call = partial(
        retrieve_chunks,
        payload.query,
        role=role,
        firm_id=firm_id,
        index_root=str(INDEX_ROOT),
        expand=payload.expand,
        top_k=payload.top_k,
        corpora=corpora,
    )
    chunks = await to_thread.run_sync(retriever_call)

    answer = None
    if payload.include_answer:
        answer_call = partial(generate_answer, payload.query, chunks)
        answer = await to_thread.run_sync(answer_call)

    return SearchResponse(
        mode=mode,
        query=payload.query,
        answer=answer,
        confidence=_confidence_for(chunks),
        sources=[SourceChunk(**chunk) for chunk in chunks],
    )


@router.post("/public", response_model=SearchResponse)
async def public_search(payload: SearchRequest) -> SearchResponse:
    return await _run_search(
        mode="public",
        payload=payload,
        role="public",
        firm_id=None,
        corpora=["public"],
    )


@router.post("/firm", response_model=SearchResponse)
async def firm_search(
    payload: SearchRequest,
    user: UserRecord = Depends(require_roles("user", "admin")),
) -> SearchResponse:
    return await _run_search(
        mode="firm",
        payload=payload,
        role=user.role,
        firm_id=user.firm_id,
        corpora=["firm"],
    )


@router.post("/combined", response_model=SearchResponse)
async def combined_search(
    payload: SearchRequest,
    user: UserRecord = Depends(get_current_user),
) -> SearchResponse:
    corpora = ["public", "firm"] if user.firm_id and user.role in {"user", "admin"} else ["public"]
    return await _run_search(
        mode="combined",
        payload=payload,
        role=user.role,
        firm_id=user.firm_id,
        corpora=corpora,
    )
