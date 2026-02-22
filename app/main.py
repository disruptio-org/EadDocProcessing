"""FastAPI application entry point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings

# Frontend directory
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# ---------------------------------------------------------------------------
# Structured logging configuration
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="DocProcessing API",
    description=(
        "Backend for processing batch PDFs containing multiple concatenated documents. "
        "Features dual-pipeline PO extraction (Pipeline A: LLM-first, Pipeline B: hybrid regex+LLM), "
        "reconciliation, PDF splitting, and Excel indexation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mount routers
# ---------------------------------------------------------------------------

from app.routers.files import router as files_router
from app.routers.extract import router as extract_router
from app.routers.reconcile import router as reconcile_router
from app.routers.split import router as split_router
from app.routers.export import router as export_router
from app.routers.process import router as process_router
from app.routers.jobs import router as jobs_router
from app.routers.rejects import router as rejects_router
from app.routers.documents import router as documents_router

app.include_router(files_router)
app.include_router(extract_router)
app.include_router(reconcile_router)
app.include_router(split_router)
app.include_router(export_router)
app.include_router(process_router)
app.include_router(jobs_router)
app.include_router(rejects_router)
app.include_router(documents_router)


# ---------------------------------------------------------------------------
# Static files (frontend)
# ---------------------------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "DocProcessing API",
        "version": "1.0.0",
    }


@app.get("/", tags=["system"])
async def root():
    """Root — serve the frontend UI."""
    index_html = FRONTEND_DIR / "index.html"
    if index_html.exists():
        return FileResponse(str(index_html), media_type="text/html")
    return {
        "message": "DocProcessing API",
        "docs": "/docs",
        "health": "/health",
    }
