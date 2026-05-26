from __future__ import annotations

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    username: str
    role: str
    firm_id: str | None = None
    corpora: list[str] = Field(default_factory=list)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1200)
    top_k: int = Field(default=8, ge=1, le=12)
    expand: bool = True
    include_answer: bool = True


class SourceChunk(BaseModel):
    chunk_id: str | None = None
    source_doc: str | None = None
    section_hint: str | None = None
    law_domain: str | None = None
    access_level: str | None = None
    corpus: str | None = None
    firm_id: str | None = None
    text: str
    relevance_score: float | None = None
    rerank_score: float | None = None
    faiss_score: float | None = None
    bm25_score: float | None = None
    low_confidence: bool = False
    note: str | None = None


class SearchResponse(BaseModel):
    mode: str
    query: str
    answer: str | None = None
    confidence: str
    sources: list[SourceChunk]


class IngestResponse(BaseModel):
    ok: bool
    firm_id: str
    filename: str
    message: str

