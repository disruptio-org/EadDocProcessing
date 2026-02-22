"""PDF text extraction per page using pypdf, with OCR fallback for scanned PDFs."""

from __future__ import annotations

import structlog
from pypdf import PdfReader

from app.schemas.common import PageText

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# OCR fallback — used only when pypdf returns no text (scanned/image PDFs)
# ---------------------------------------------------------------------------

def _ocr_extract_text_by_page(pdf_path: str, total_pages: int) -> list[PageText]:
    """Extract text via OCR (pytesseract + pdf2image) for scanned PDFs."""
    from pdf2image import convert_from_path
    import pytesseract

    pages: list[PageText] = []
    for i in range(total_pages):
        try:
            images = convert_from_path(
                pdf_path, first_page=i + 1, last_page=i + 1, dpi=150,
            )
            text = pytesseract.image_to_string(images[0], lang="por+spa+eng")
        except Exception as exc:
            logger.warning("ocr_page_failed", page=i, error=str(exc))
            text = ""
        pages.append(PageText(page=i, text=text))
        logger.debug("ocr_page_extracted", page=i, chars=len(text))

    logger.info("ocr_extraction_complete", total_pages=len(pages))
    return pages


# ---------------------------------------------------------------------------
# Primary extraction
# ---------------------------------------------------------------------------

def extract_text_by_page(pdf_path: str) -> list[PageText]:
    """Extract text from each page of a PDF file.

    Uses pypdf as the primary extraction method. If ALL pages yield no text
    (scanned/image PDF), falls back to OCR via pytesseract + pdf2image.
    """
    reader = PdfReader(pdf_path)
    pages: list[PageText] = []

    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            logger.warning("page_text_extraction_failed", page=i, error=str(exc))
            text = ""
        pages.append(PageText(page=i, text=text))
        logger.debug("page_extracted", page=i, chars=len(text))

    logger.info("text_extraction_complete", total_pages=len(pages))

    # --- OCR fallback for scanned/image-only PDFs ---
    has_any_text = any(p.text.strip() for p in pages)
    if not has_any_text and len(pages) > 0:
        logger.info(
            "ocr_fallback_triggered",
            msg="All pages empty — falling back to OCR",
            total_pages=len(pages),
        )
        pages = _ocr_extract_text_by_page(pdf_path, len(pages))

    return pages


def get_page_count(pdf_path: str) -> int:
    """Return the total number of pages in a PDF."""
    reader = PdfReader(pdf_path)
    return len(reader.pages)
