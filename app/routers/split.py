"""Router: POST /v1/split — split a batch PDF into individual documents."""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.common import PageRange
from app.services.pdf_splitter import split_pdf
from app.storage import local as storage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["split"])


class SplitRequest(BaseModel):
    source_file_id: str
    ranges: list[PageRange]


class SplitDocResponse(BaseModel):
    doc_id: str
    page_start: int
    page_end: int
    path: str


class SplitResponse(BaseModel):
    source_file_id: str
    documents: list[SplitDocResponse]
    total: int


@router.post("/split", response_model=SplitResponse)
async def split_batch_pdf(req: SplitRequest):
    """Split a batch PDF into individual document PDFs by page ranges.

    Each resulting PDF is saved with a unique doc_id (UUID).
    """
    try:
        pdf_path = storage.get_upload_path(req.source_file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Source file not found")

    split_docs = split_pdf(
        pdf_path=str(pdf_path),
        ranges=req.ranges,
        source_file_id=req.source_file_id,
    )

    docs = [
        SplitDocResponse(
            doc_id=sd.doc_id,
            page_start=sd.page_range.start_page,
            page_end=sd.page_range.end_page,
            path=sd.path,
        )
        for sd in split_docs
    ]

    # Save artifact
    storage.save_artifact(
        req.source_file_id,
        "split",
        [d.model_dump() for d in docs],
    )

    return SplitResponse(
        source_file_id=req.source_file_id,
        documents=docs,
        total=len(docs),
    )


@router.get("/split/{source_file_id}/download")
async def download_split_pdfs(source_file_id: str):
    """Download all split PDFs as a single zip archive."""
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    # Use the split artifact to get the correct page-range order
    split_data = storage.load_artifact(source_file_id, "split")
    if not split_data:
        raise HTTPException(status_code=404, detail="No split data found. Run split first.")

    docs_path = storage.docs_dir(source_file_id)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, doc_entry in enumerate(split_data, start=1):
            pdf_file = docs_path / f"{doc_entry['doc_id']}.pdf"
            if pdf_file.exists():
                arcname = f"{source_file_id}_doc{i:03d}.pdf"
                zf.write(pdf_file, arcname)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=split_docs_{source_file_id[:8]}.zip"
        },
    )


@router.get("/split/{source_file_id}/doc/{doc_index}")
async def get_split_pdf(source_file_id: str, doc_index: int):
    """Serve a single split PDF by its 1-based index (page-range order)."""
    from fastapi.responses import FileResponse

    # Use the split artifact to get the correct doc_id for this index
    split_data = storage.load_artifact(source_file_id, "split")
    if not split_data:
        raise HTTPException(status_code=404, detail="No split data found. Run split first.")

    if doc_index < 1 or doc_index > len(split_data):
        raise HTTPException(status_code=404, detail=f"Doc {doc_index} not found")

    doc_entry = split_data[doc_index - 1]
    pdf_path = storage.docs_dir(source_file_id) / f"{doc_entry['doc_id']}.pdf"

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file not found for doc {doc_index}")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )
