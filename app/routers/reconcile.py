"""Router: POST /v1/reconcile/po — reconcile Pipeline A vs B results."""

from __future__ import annotations

import structlog
from fastapi import APIRouter

from app.reconcile.engine import reconcile
from app.schemas.common import FinalStatus
from app.schemas.reconciliation import (
    ReconcileDocResult,
    ReconcileRequest,
    ReconcileResponse,
)
from app.storage import local as storage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/reconcile", tags=["reconciliation"])


@router.post("/po", response_model=ReconcileResponse)
async def reconcile_po(req: ReconcileRequest):
    """Reconcile PO extraction results from Pipeline A and Pipeline B.

    Compares each document's A vs B results and determines:
    - MATCH_OK: POs agree → status OK, next_action AUTO_OK
    - MISMATCH: POs disagree → status NOT_OK, next_action SEND_TO_REVIEW
    - NEEDS_REVIEW: missing data or low confidence → status NOT_OK
    """
    results: list[ReconcileDocResult] = []
    total_ok = 0
    total_not_ok = 0

    for doc in req.documents:
        outcome = reconcile(doc.result_a, doc.result_b)

        result = ReconcileDocResult(
            range=doc.range,
            match_status=outcome.match_status,
            decided_po_primary=outcome.decided_po_primary,
            decided_po_secondary=outcome.decided_po_secondary,
            decided_po_numbers=outcome.decided_po_numbers,
            status=outcome.status,
            next_action=outcome.next_action,
            reject_reason=outcome.reject_reason,
            result_a=doc.result_a,
            result_b=doc.result_b,
        )
        results.append(result)

        if outcome.status == FinalStatus.OK:
            total_ok += 1
        else:
            total_not_ok += 1

    # Save artifact
    storage.save_artifact(
        req.source_file_id,
        "reconcile",
        [r.model_dump() for r in results],
    )

    return ReconcileResponse(
        source_file_id=req.source_file_id,
        documents=results,
        total_ok=total_ok,
        total_not_ok=total_not_ok,
    )
