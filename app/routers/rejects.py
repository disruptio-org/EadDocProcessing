"""Router: /v1/rejects — manage reject / review queue records."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.schemas.rejects import (
    RejectCreate,
    RejectListResponse,
    RejectRecord,
    RejectResolve,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["rejects"])

# Simple file-based reject store
_REJECTS_DIR: Path | None = None


def _rejects_dir() -> Path:
    d = Path(settings.storage_base_path) / "rejects"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_rejects(source_file_id: str | None = None) -> list[RejectRecord]:
    """Load all reject records, optionally filtered by source_file_id."""
    rejects: list[RejectRecord] = []
    d = _rejects_dir()
    for file in d.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            record = RejectRecord(**data)
            if source_file_id is None or record.source_file_id == source_file_id:
                rejects.append(record)
        except Exception as exc:
            logger.warning("reject_load_error", file=str(file), error=str(exc))
    return rejects


def _save_reject(record: RejectRecord) -> None:
    """Persist a reject record to a JSON file."""
    d = _rejects_dir()
    path = d / f"{record.reject_id}.json"
    path.write_text(
        json.dumps(record.model_dump(), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/rejects", response_model=RejectRecord)
async def create_reject(req: RejectCreate):
    """Create a new reject / review case.

    Called automatically during processing when MISMATCH or NEEDS_REVIEW.
    Can also be called manually to flag a document.
    """
    now = datetime.now(timezone.utc).isoformat()
    record = RejectRecord(
        reject_id=str(uuid.uuid4()),
        source_file_id=req.source_file_id,
        doc_id=req.doc_id,
        page_start=req.page_start,
        page_end=req.page_end,
        result_a=req.result_a,
        result_b=req.result_b,
        match_status=req.match_status,
        reject_reason=req.reject_reason,
        resolved=False,
        resolved_po=None,
        created_at=now,
        updated_at=now,
    )
    _save_reject(record)

    logger.info(
        "reject_created",
        reject_id=record.reject_id,
        doc_id=req.doc_id,
        match_status=req.match_status,
    )
    return record


@router.post("/rejects/resolve", response_model=RejectRecord)
async def resolve_reject(req: RejectResolve):
    """Resolve a reject by providing the correct PO number (manual review)."""
    d = _rejects_dir()
    path = d / f"{req.reject_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Reject not found")

    data = json.loads(path.read_text(encoding="utf-8"))
    record = RejectRecord(**data)
    record.resolved = True
    record.resolved_po = req.resolved_po
    record.updated_at = datetime.now(timezone.utc).isoformat()
    _save_reject(record)

    logger.info("reject_resolved", reject_id=req.reject_id, resolved_po=req.resolved_po)
    return record


@router.get("/rejects", response_model=RejectListResponse)
async def list_rejects(
    source_file_id: Optional[str] = Query(default=None, description="Filter by source file"),
):
    """List reject/review cases, optionally filtered by source_file_id."""
    rejects = _load_rejects(source_file_id)
    return RejectListResponse(
        source_file_id=source_file_id,
        rejects=rejects,
        total=len(rejects),
    )
