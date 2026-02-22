"""PDF splitter — split a batch PDF into individual documents by page ranges."""

from __future__ import annotations

import io
import uuid

import structlog
from pypdf import PdfReader, PdfWriter

from app.schemas.common import PageRange
from app.storage import local as storage

logger = structlog.get_logger(__name__)


class SplitDoc:
    """Represents a split document."""

    def __init__(self, doc_id: str, page_range: PageRange, path: str):
        self.doc_id = doc_id
        self.page_range = page_range
        self.path = path


def split_pdf(
    pdf_path: str,
    ranges: list[PageRange],
    source_file_id: str,
) -> list[SplitDoc]:
    """Split a PDF into individual documents based on page ranges.

    Args:
        pdf_path: Path to the source PDF.
        ranges: List of PageRange defining document boundaries.
        source_file_id: UUID of the source file (for output directory).

    Returns:
        List of SplitDoc with doc_id, range, and output path.
    """
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    results: list[SplitDoc] = []

    for page_range in ranges:
        doc_id = str(uuid.uuid4())
        writer = PdfWriter()

        start = page_range.start_page
        end = min(page_range.end_page, total_pages - 1)

        for page_idx in range(start, end + 1):
            writer.add_page(reader.pages[page_idx])

        # Write to bytes
        buffer = io.BytesIO()
        writer.write(buffer)
        pdf_bytes = buffer.getvalue()

        # Save
        out_path = storage.save_split_pdf(source_file_id, doc_id, pdf_bytes)

        results.append(SplitDoc(
            doc_id=doc_id,
            page_range=page_range,
            path=str(out_path),
        ))

        logger.info(
            "pdf_split",
            doc_id=doc_id,
            pages=f"{start}-{end}",
            size_bytes=len(pdf_bytes),
        )

    logger.info("pdf_split_complete", total_documents=len(results))
    return results
