"""Job state persistence — Redis-backed with JSON fallback."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import structlog

from app.config import settings
from app.schemas.common import JobStatus

logger = structlog.get_logger(__name__)

# In-memory store used as fallback when Redis is unavailable
_memory_store: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Redis helpers (best-effort)
# ---------------------------------------------------------------------------

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as redis_lib
        _redis_client = redis_lib.from_url(settings.redis_url, decode_responses=True)
        _redis_client.ping()
        logger.info("redis_connected", url=settings.redis_url)
        return _redis_client
    except Exception:
        logger.warning("redis_unavailable", msg="Falling back to in-memory job store")
        _redis_client = False  # sentinel: tried and failed
        return None


def _redis():
    r = _get_redis()
    return r if r is not False else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_job(source_file_id: str) -> str:
    """Create a new job and return its ID."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    job = {
        "job_id": job_id,
        "source_file_id": source_file_id,
        "status": JobStatus.PENDING.value,
        "progress": 0.0,
        "current_step": None,
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    _save(job_id, job, source_file_id)
    return job_id


def update_job(
    job_id: str,
    *,
    status: Optional[JobStatus] = None,
    progress: Optional[float] = None,
    current_step: Optional[str] = None,
    result: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """Update selected fields of a job."""
    job = get_job(job_id)
    if job is None:
        logger.error("job_not_found", job_id=job_id)
        return
    if status is not None:
        job["status"] = status.value
    if progress is not None:
        job["progress"] = progress
    if current_step is not None:
        job["current_step"] = current_step
    if result is not None:
        job["result"] = result
    if error is not None:
        job["error"] = error
    job["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save(job_id, job, job["source_file_id"])


def get_job(job_id: str) -> Optional[dict]:
    """Retrieve a job by ID."""
    r = _redis()
    if r:
        raw = r.get(f"job:{job_id}")
        if raw:
            return json.loads(raw)
    return _memory_store.get(job_id)


# ---------------------------------------------------------------------------
# Internal persistence
# ---------------------------------------------------------------------------

def _save(job_id: str, job: dict, source_file_id: str) -> None:
    """Persist job to Redis + in-memory + JSON file."""
    _memory_store[job_id] = job

    # Redis
    r = _redis()
    if r:
        try:
            r.set(f"job:{job_id}", json.dumps(job, default=str), ex=86400 * 7)
        except Exception:
            logger.warning("redis_save_failed", job_id=job_id)

    # JSON file
    try:
        out_dir = Path(settings.storage_base_path) / "outputs" / source_file_id
        out_dir.mkdir(parents=True, exist_ok=True)
        job_path = out_dir / "job.json"
        job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except Exception:
        logger.warning("json_save_failed", job_id=job_id)
