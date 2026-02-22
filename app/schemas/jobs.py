"""Schemas for job management endpoints."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.common import JobStatus


class JobResponse(BaseModel):
    """Response for job status queries."""
    job_id: str = Field(..., description="Job UUID")
    source_file_id: str
    status: JobStatus
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Progress 0.0 - 1.0")
    current_step: Optional[str] = Field(None, description="Current processing step")
    result: Optional[dict[str, Any]] = Field(None, description="Final result when completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: str
    updated_at: str


class ProcessRequest(BaseModel):
    """Request body for the full processing flow."""
    source_file_id: str
    mode: str = Field(default="dual", description="Processing mode: dual (default)")
