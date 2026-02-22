"""Schemas for text/boundary/PO extraction endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import PageRange, PageText, PipelineResult


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

class TextExtractionRequest(BaseModel):
    source_file_id: str


class TextExtractionResponse(BaseModel):
    source_file_id: str
    pages: list[PageText]
    total_pages: int


# ---------------------------------------------------------------------------
# Boundary detection
# ---------------------------------------------------------------------------

class BoundaryRequest(BaseModel):
    source_file_id: str


class BoundaryResponse(BaseModel):
    source_file_id: str
    ranges: list[PageRange]
    total_documents: int


# ---------------------------------------------------------------------------
# PO extraction
# ---------------------------------------------------------------------------

class POExtractionRequest(BaseModel):
    source_file_id: str
    ranges: list[PageRange] = Field(..., description="Document ranges to extract POs from")


class PODocResult(BaseModel):
    range: PageRange
    result: PipelineResult


class POExtractionResponse(BaseModel):
    source_file_id: str
    pipeline: str = Field(..., description="Pipeline used: A or B")
    documents: list[PODocResult]
