"""Router: GET /v1/jobs/{job_id} — query job status and results."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException

from app.schemas.jobs import JobResponse
from app.storage.job_store import get_job

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get the status, progress, and results of a processing job.

    Poll this endpoint to check if the job has completed.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(**job)
