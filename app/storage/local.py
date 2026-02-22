"""Local filesystem storage operations."""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.config import settings


def _base() -> Path:
    return Path(settings.storage_base_path)


def uploads_dir() -> Path:
    d = _base() / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def outputs_dir(source_file_id: str) -> Path:
    d = _base() / "outputs" / source_file_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def docs_dir(source_file_id: str) -> Path:
    d = outputs_dir(source_file_id) / "docs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def artifacts_dir(source_file_id: str) -> Path:
    d = outputs_dir(source_file_id) / "artifacts"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def save_upload(source_file_id: str, file_bytes: bytes) -> Path:
    """Save an uploaded PDF to the uploads directory."""
    path = uploads_dir() / f"{source_file_id}.pdf"
    path.write_bytes(file_bytes)
    return path


def get_upload_path(source_file_id: str) -> Path:
    """Return the path to an uploaded PDF (raises if not found)."""
    path = uploads_dir() / f"{source_file_id}.pdf"
    if not path.exists():
        raise FileNotFoundError(f"Upload not found: {source_file_id}")
    return path


def ensure_output_dirs(source_file_id: str) -> None:
    """Ensure all output subdirectories exist."""
    docs_dir(source_file_id)
    artifacts_dir(source_file_id)


def save_artifact(source_file_id: str, name: str, data: dict | list) -> Path:
    """Save a JSON artifact to the artifacts directory."""
    path = artifacts_dir(source_file_id) / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def load_artifact(source_file_id: str, name: str) -> dict | list | None:
    """Load a JSON artifact; returns None if not found."""
    path = artifacts_dir(source_file_id) / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_split_pdf(source_file_id: str, doc_id: str, pdf_bytes: bytes) -> Path:
    """Save a split document PDF."""
    path = docs_dir(source_file_id) / f"{doc_id}.pdf"
    path.write_bytes(pdf_bytes)
    return path


def get_excel_path(source_file_id: str) -> Path:
    """Return the path for the index Excel file."""
    return outputs_dir(source_file_id) / "index.xlsx"
