"""Shared schema types used across the application."""

from __future__ import annotations

import enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MatchStatus(str, enum.Enum):
    MATCH_OK = "MATCH_OK"
    MISMATCH = "MISMATCH"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class FinalStatus(str, enum.Enum):
    OK = "OK"
    NOT_OK = "NOT_OK"


class NextAction(str, enum.Enum):
    AUTO_OK = "AUTO_OK"
    SEND_TO_REVIEW = "SEND_TO_REVIEW"
    RUN_ARBITER = "RUN_ARBITER"
    REVISTO = "REVISTO"


class PipelineMethod(str, enum.Enum):
    LLM = "LLM"
    REGEX = "REGEX"
    HYBRID = "HYBRID"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class Evidence(BaseModel):
    """A snippet of text evidence for a PO extraction."""
    page: int = Field(..., description="0-based page number")
    snippet: str = Field(..., description="Text snippet containing the evidence")


class PageRange(BaseModel):
    """A range of pages representing a single document within the batch PDF."""
    start_page: int = Field(..., description="0-based start page (inclusive)")
    end_page: int = Field(..., description="0-based end page (inclusive)")


class PipelineResult(BaseModel):
    """Normalised result from a single extraction pipeline (A or B)."""
    po_primary: Optional[str] = Field(None, description="Primary PO number")
    po_secondary: Optional[str] = Field(None, description="Secondary PO number (optional)")
    po_numbers: list[str] = Field(default_factory=list, description="All PO numbers found (may be >2)")
    supplier: Optional[str] = Field(None, description="Supplier name if detected")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    method: PipelineMethod = Field(..., description="Method used for extraction")
    found_keywords: list[str] = Field(default_factory=list, description="Keywords matched")
    evidence: list[Evidence] = Field(default_factory=list, description="Evidence snippets")


class PageText(BaseModel):
    """Text content of a single PDF page."""
    page: int = Field(..., description="0-based page number")
    text: str = Field(..., description="Extracted text content")


class DocumentRecord(BaseModel):
    """Full record for one identified document within a batch PDF."""
    source_file_id: str
    doc_id: str
    page_start: int
    page_end: int
    # Pipeline A results
    supplier_a: Optional[str] = None
    po_primary_a: Optional[str] = None
    po_secondary_a: Optional[str] = None
    po_numbers_a: list[str] = Field(default_factory=list)
    confidence_a: float = 0.0
    method_a: Optional[str] = None
    # Pipeline B results
    supplier_b: Optional[str] = None
    po_primary_b: Optional[str] = None
    po_secondary_b: Optional[str] = None
    po_numbers_b: list[str] = Field(default_factory=list)
    confidence_b: float = 0.0
    method_b: Optional[str] = None
    # Reconciliation
    match_status: Optional[MatchStatus] = None
    decided_po_primary: Optional[str] = None
    decided_po_secondary: Optional[str] = None
    decided_po_numbers: list[str] = Field(default_factory=list)
    status: Optional[FinalStatus] = None
    next_action: Optional[NextAction] = None
    reject_reason: Optional[str] = None
