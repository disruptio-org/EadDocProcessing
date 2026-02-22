"""Router: PATCH /v1/documents — update document fields (PO override)."""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.common import NextAction
from app.services.excel_export import generate_index_excel
from app.schemas.common import DocumentRecord
from app.storage import local as storage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/documents", tags=["documents"])


class DocumentUpdateRequest(BaseModel):
    decided_po_primary: Optional[str] = None


class DocumentUpdateResponse(BaseModel):
    doc_index: int
    decided_po_primary: Optional[str]
    next_action: str
    excel_regenerated: bool


@router.patch("/{source_file_id}/{doc_index}", response_model=DocumentUpdateResponse)
async def update_document(source_file_id: str, doc_index: int, req: DocumentUpdateRequest):
    """Update a document's decided PO and set next_action to REVISTO.

    Also regenerates the Excel export with the updated data.
    """
    # Load the reconcile artifact
    reconcile_data = storage.load_artifact(source_file_id, "reconcile")
    if reconcile_data is None:
        raise HTTPException(status_code=404, detail="Reconcile artifact not found.")

    if doc_index < 0 or doc_index >= len(reconcile_data):
        raise HTTPException(status_code=404, detail=f"Document index {doc_index} out of range.")

    # Update the document
    doc = reconcile_data[doc_index]
    if req.decided_po_primary is not None:
        doc["decided_po_primary"] = req.decided_po_primary
    doc["next_action"] = NextAction.REVISTO.value

    # Save updated artifact
    storage.save_artifact(source_file_id, "reconcile", reconcile_data)

    # Regenerate Excel export
    excel_regenerated = False
    try:
        excel_docs = []
        for i, d in enumerate(reconcile_data):
            result_a = d.get("result_a") or {}
            result_b = d.get("result_b") or {}
            doc_range = d.get("range") or {}

            excel_docs.append(DocumentRecord(
                source_file_id=source_file_id,
                doc_id=f"{source_file_id}_doc{str(i + 1).zfill(3)}",
                page_start=doc_range.get("start_page", 0),
                page_end=doc_range.get("end_page", 0),
                supplier_a=result_a.get("supplier"),
                po_primary_a=result_a.get("po_primary"),
                po_secondary_a=result_a.get("po_secondary"),
                confidence_a=result_a.get("confidence", 0),
                method_a=result_a.get("method"),
                supplier_b=result_b.get("supplier"),
                po_primary_b=result_b.get("po_primary"),
                po_secondary_b=result_b.get("po_secondary"),
                confidence_b=result_b.get("confidence", 0),
                method_b=result_b.get("method"),
                match_status=d.get("match_status"),
                decided_po_primary=d.get("decided_po_primary"),
                decided_po_secondary=d.get("decided_po_secondary"),
                status=d.get("status"),
                next_action=d.get("next_action"),
                reject_reason=d.get("reject_reason"),
            ))

        generate_index_excel(
            source_file_id=source_file_id,
            documents=excel_docs,
        )
        excel_regenerated = True
    except Exception as e:
        logger.error("excel_regen_failed", error=str(e))

    logger.info(
        "document_updated",
        source_file_id=source_file_id,
        doc_index=doc_index,
        decided_po_primary=doc.get("decided_po_primary"),
        next_action=doc.get("next_action"),
    )

    return DocumentUpdateResponse(
        doc_index=doc_index,
        decided_po_primary=doc.get("decided_po_primary"),
        next_action=doc.get("next_action"),
        excel_regenerated=excel_regenerated,
    )
