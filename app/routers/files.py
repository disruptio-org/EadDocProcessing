"""Router: POST /v1/files — upload a PDF batch file."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File

from app.schemas.files import FileUploadResponse
from app.services.text_extraction import get_page_count
from app.storage import local as storage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["files"])


@router.post("/files", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a batch PDF file for processing.

    Returns the source_file_id (UUID), original filename, page count, and file size.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    source_file_id = str(uuid.uuid4())

    # Save to filesystem
    saved_path = storage.save_upload(source_file_id, content)
    storage.ensure_output_dirs(source_file_id)

    # Get page count
    try:
        page_count = get_page_count(str(saved_path))
    except Exception as exc:
        logger.error("pdf_read_error", error=str(exc))
        raise HTTPException(status_code=400, detail=f"Invalid PDF: {exc}")

    logger.info(
        "file_uploaded",
        source_file_id=source_file_id,
        filename=file.filename,
        size_bytes=len(content),
        page_count=page_count,
    )

    return FileUploadResponse(
        source_file_id=source_file_id,
        filename=file.filename,
        page_count=page_count,
        size_bytes=len(content),
    )
