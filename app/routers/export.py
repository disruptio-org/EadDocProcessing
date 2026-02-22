"""Router: POST /v1/export/excel — generate the index Excel file."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.schemas.common import DocumentRecord
from app.services.excel_export import generate_index_excel

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/export", tags=["export"])


class ExcelExportRequest(BaseModel):
    source_file_id: str
    documents: list[DocumentRecord]


class ExcelExportResponse(BaseModel):
    source_file_id: str
    path: str
    rows: int


@router.post("/excel", response_model=ExcelExportResponse)
async def export_excel(req: ExcelExportRequest):
    """Generate an index.xlsx file with full document indexation.

    Includes all columns: source_file_id, doc_id, page ranges,
    Pipeline A/B results, match_status, decided POs, status, next_action.
    """
    excel_path = generate_index_excel(
        source_file_id=req.source_file_id,
        documents=req.documents,
    )

    return ExcelExportResponse(
        source_file_id=req.source_file_id,
        path=str(excel_path),
        rows=len(req.documents),
    )


@router.get("/excel/{source_file_id}")
async def download_excel(source_file_id: str):
    """Download the generated index.xlsx for a source file."""
    from app.storage import local as storage

    excel_path = storage.get_excel_path(source_file_id)
    if not excel_path.exists():
        raise HTTPException(status_code=404, detail="Excel file not found. Run export first.")

    return FileResponse(
        path=str(excel_path),
        filename=f"index_{source_file_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
