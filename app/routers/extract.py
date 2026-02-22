"""Router: extraction endpoints — text, boundaries, PO."""

from __future__ import annotations

from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.schemas.common import PageText, PipelineResult
from app.schemas.extraction import (
    BoundaryRequest,
    BoundaryResponse,
    PODocResult,
    POExtractionRequest,
    POExtractionResponse,
    TextExtractionRequest,
    TextExtractionResponse,
)
from app.services.boundary_detection import detect_boundaries
from app.services.pipeline_a import run_pipeline_a
from app.services.pipeline_b import run_pipeline_b
from app.services.text_extraction import extract_text_by_page
from app.storage import local as storage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/extract", tags=["extraction"])


# ---------------------------------------------------------------------------
# POST /v1/extract/text
# ---------------------------------------------------------------------------

@router.post("/text", response_model=TextExtractionResponse)
async def extract_text(req: TextExtractionRequest):
    """Extract text from each page of the uploaded PDF.

    Uses pypdf text extraction. If a page has no text (scanned/image),
    the text field will be empty — callers can use LLM fallback.
    """
    try:
        pdf_path = storage.get_upload_path(req.source_file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Source file not found")

    pages = extract_text_by_page(str(pdf_path))

    # Save artifact
    storage.save_artifact(
        req.source_file_id,
        "text_extraction",
        [p.model_dump() for p in pages],
    )

    return TextExtractionResponse(
        source_file_id=req.source_file_id,
        pages=pages,
        total_pages=len(pages),
    )


# ---------------------------------------------------------------------------
# POST /v1/extract/boundaries
# ---------------------------------------------------------------------------

@router.post("/boundaries", response_model=BoundaryResponse)
async def extract_boundaries(req: BoundaryRequest):
    """Detect document boundaries (page ranges) within a batch PDF.

    Uses heuristic first-page patterns (Página 1, Page 1, etc.).
    Falls back to treating the entire PDF as one document if no patterns found.
    """
    try:
        pdf_path = storage.get_upload_path(req.source_file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Source file not found")

    pages = extract_text_by_page(str(pdf_path))
    ranges = detect_boundaries(pages)

    # Save artifact
    storage.save_artifact(
        req.source_file_id,
        "boundaries",
        [r.model_dump() for r in ranges],
    )

    return BoundaryResponse(
        source_file_id=req.source_file_id,
        ranges=ranges,
        total_documents=len(ranges),
    )


# ---------------------------------------------------------------------------
# POST /v1/extract/po
# ---------------------------------------------------------------------------

@router.post("/po", response_model=POExtractionResponse)
async def extract_po(
    req: POExtractionRequest,
    pipeline: Literal["A", "B"] = Query(default="A", description="Pipeline to use: A or B"),
):
    """Extract PO numbers from document pages using the specified pipeline.

    - Pipeline A: LLM-first (flexible, robust)
    - Pipeline B: Regex-first + LLM fallback (conservative)
    """
    try:
        pdf_path = storage.get_upload_path(req.source_file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Source file not found")

    all_pages = extract_text_by_page(str(pdf_path))
    results: list[PODocResult] = []

    for page_range in req.ranges:
        # Get pages for this document range
        doc_pages = [
            p for p in all_pages
            if page_range.start_page <= p.page <= page_range.end_page
        ]

        if pipeline == "A":
            result = run_pipeline_a(doc_pages)
        else:
            result = run_pipeline_b(doc_pages)

        results.append(PODocResult(range=page_range, result=result))

    # Save artifact
    artifact_name = f"extract_{pipeline}"
    storage.save_artifact(
        req.source_file_id,
        artifact_name,
        [r.model_dump() for r in results],
    )

    return POExtractionResponse(
        source_file_id=req.source_file_id,
        pipeline=pipeline,
        documents=results,
    )
