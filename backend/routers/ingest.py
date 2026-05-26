from __future__ import annotations

import os
import re
from contextlib import contextmanager

from anyio import to_thread
from fastapi import APIRouter, Depends, File, Form, UploadFile

from auth import require_roles
from config import DATA_ROOT, ROOT_DIR
from models.schemas import IngestResponse

from access_control import UserRecord

router = APIRouter(prefix="/ingest", tags=["ingest"])


@contextmanager
def _working_directory(path):
    original = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename).strip("._")
    return cleaned or "uploaded.pdf"


def _ingest(saved_path: str, firm_id: str, access_level: str) -> None:
    from ingest_private import ingest_firm_pdf

    with _working_directory(ROOT_DIR):
        ingest_firm_pdf(saved_path, firm_id=firm_id, access_level=access_level)


@router.post("/firm", response_model=IngestResponse)
async def ingest_firm(
    file: UploadFile = File(...),
    firm_id: str = Form(..., min_length=1, max_length=80),
    access_level: str = Form("firm"),
    user: UserRecord = Depends(require_roles("admin")),
) -> IngestResponse:
    target_firm = firm_id.strip() or user.firm_id or "firm_alpha"
    filename = _safe_filename(file.filename or "uploaded.pdf")
    firm_dir = DATA_ROOT / "firms" / target_firm
    firm_dir.mkdir(parents=True, exist_ok=True)
    saved_path = firm_dir / filename

    contents = await file.read()
    saved_path.write_bytes(contents)
    await to_thread.run_sync(_ingest, str(saved_path), target_firm, access_level)

    return IngestResponse(
        ok=True,
        firm_id=target_firm,
        filename=filename,
        message="PDF ingested and firm index rebuilt.",
    )
