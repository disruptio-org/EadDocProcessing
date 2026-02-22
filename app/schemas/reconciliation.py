"""Schemas for reconciliation endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import (
    FinalStatus,
    MatchStatus,
    NextAction,
    PageRange,
    PipelineResult,
)


class ReconcileDocInput(BaseModel):
    """Input for reconciling one document's A and B results."""
    range: PageRange
    result_a: PipelineResult
    result_b: PipelineResult


class ReconcileRequest(BaseModel):
    source_file_id: str
    documents: list[ReconcileDocInput]


class ReconcileDocResult(BaseModel):
    """Reconciliation output for a single document."""
    range: PageRange
    match_status: MatchStatus
    decided_po_primary: Optional[str] = None
    decided_po_secondary: Optional[str] = None
    decided_po_numbers: list[str] = []
    status: FinalStatus
    next_action: NextAction
    reject_reason: Optional[str] = None
    result_a: PipelineResult
    result_b: PipelineResult


class ReconcileResponse(BaseModel):
    source_file_id: str
    documents: list[ReconcileDocResult]
    total_ok: int
    total_not_ok: int
