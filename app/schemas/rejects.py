"""Schemas for reject / review queue endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import Evidence, PipelineResult


class RejectRecord(BaseModel):
    """A single reject/review case."""
    reject_id: str
    source_file_id: str
    doc_id: str
    page_start: int
    page_end: int
    result_a: PipelineResult
    result_b: PipelineResult
    match_status: str
    reject_reason: Optional[str] = None
    resolved: bool = False
    resolved_po: Optional[str] = None
    created_at: str
    updated_at: str


class RejectCreate(BaseModel):
    """Request body to create or update a reject record."""
    source_file_id: str
    doc_id: str
    page_start: int
    page_end: int
    result_a: PipelineResult
    result_b: PipelineResult
    match_status: str
    reject_reason: Optional[str] = None


class RejectResolve(BaseModel):
    """Request body to resolve a reject (manual review)."""
    reject_id: str
    resolved_po: str


class RejectListResponse(BaseModel):
    """Response listing reject records."""
    source_file_id: Optional[str] = None
    rejects: list[RejectRecord]
    total: int
