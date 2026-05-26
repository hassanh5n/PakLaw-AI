from __future__ import annotations

from contextlib import asynccontextmanager
from anyio import to_thread
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import EAGER_MODEL_LOAD, FRONTEND_ORIGINS, INDEX_ROOT, USERS_DB_PATH
from routers import auth, ingest, search

from access_control import ensure_default_users

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_default_users(db_path=str(USERS_DB_PATH))
    if EAGER_MODEL_LOAD:
        from retriever import get_embedding_backend, get_reranker_backend

        await to_thread.run_sync(get_embedding_backend)
        await to_thread.run_sync(get_reranker_backend)
    yield


app = FastAPI(
    title="PakLaw AI API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(search.router)
app.include_router(ingest.router)


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "ok": True,
        "index_root": str(INDEX_ROOT),
    }
