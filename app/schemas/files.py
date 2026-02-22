"""Schemas for file upload endpoints."""

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response returned after a successful PDF upload."""
    source_file_id: str = Field(..., description="UUID of the uploaded source file")
    filename: str = Field(..., description="Original filename")
    page_count: int = Field(..., description="Total pages in the PDF")
    size_bytes: int = Field(..., description="File size in bytes")
