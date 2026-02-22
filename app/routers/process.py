"""Router: POST /v1/process — full async processing flow."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException

from app.schemas.jobs import JobResponse, ProcessRequest
from app.storage import local as storage
from app.storage.job_store import create_job, get_job

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["process"])


@router.post("/process", response_model=JobResponse)
async def process_full(req: ProcessRequest):
    """Start the full processing pipeline for a batch PDF.

    This creates an async job that:
    1. Extracts text from all pages
    2. Detects document boundaries
    3. Runs Pipeline A and Pipeline B on each document
    4. Reconciles A vs B results
    5. Splits the PDF into individual documents
    6. Generates the index Excel file
    7. Creates reject records for MISMATCH/NEEDS_REVIEW cases

    Returns a job_id that can be polled via GET /v1/jobs/{job_id}.
    """
    # Verify file exists
    try:
        storage.get_upload_path(req.source_file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Source file not found")

    # Create job
    job_id = create_job(req.source_file_id)

    # Enqueue task
    try:
        from redis import Redis
        from rq import Queue

        from app.config import settings

        redis_conn = Redis.from_url(settings.redis_url)
        q = Queue(connection=redis_conn)
        q.enqueue(
            "app.workers.tasks.process_full_flow",
            job_id=job_id,
            source_file_id=req.source_file_id,
            mode=req.mode,
            job_timeout="30m",
        )
        logger.info("job_enqueued", job_id=job_id, queue="default")

    except Exception as exc:
        # If Redis/RQ not available, run synchronously (dev mode)
        logger.warning(
            "rq_unavailable",
            error=str(exc),
            msg="Running synchronously (dev mode)",
        )
        import threading
        from app.workers.tasks import process_full_flow

        thread = threading.Thread(
            target=process_full_flow,
            kwargs={
                "job_id": job_id,
                "source_file_id": req.source_file_id,
                "mode": req.mode,
            },
            daemon=True,
        )
        thread.start()

    job = get_job(job_id)
    return JobResponse(**job)
