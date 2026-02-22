"""Document boundary detection — identifies where one document ends and another begins."""

from __future__ import annotations

import re

import structlog

from app.schemas.common import PageRange, PageText

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Heuristic patterns for "first page" detection
# ---------------------------------------------------------------------------
# These patterns match typical pagination markers that indicate a first page.
# Supports: Portuguese, English, German, French, Spanish.

FIRST_PAGE_PATTERNS: list[re.Pattern] = [
    # ---------------------------------------------------------------------------
    # Albarán / Delivery note patterns (common in Spanish/PT invoices)
    # "Albarán Página 1XXXXXXX" — page 1 with albarán number concatenated
    re.compile(r"Albar[aá]n\s+P[aá]g(?:ina)?\s*1\d{5,}", re.IGNORECASE),
    # ---------------------------------------------------------------------------
    # "Página 1 de N", "Pagina 1 de N", "Pág. 1 de N"
    re.compile(r"P[aá]g(?:ina)?\.?\s*[:\-]?\s*1\s+de\s+\d+", re.IGNORECASE),
    # "Página 1" or "Pagina 1" (standalone — NOT followed by more digits)
    re.compile(r"P[aá]g(?:ina)?\.?\s*[:\-]?\s*1(?:\s|$|[^0-9])", re.IGNORECASE),
    # "Page 1 of N", "Page 1"
    re.compile(r"Page\s+1\s+of\s+\d+", re.IGNORECASE),
    re.compile(r"Page\s*[:\-]?\s*1(?:\s|$|[^0-9])", re.IGNORECASE),
    # "Seite 1 von N", "Seite 1"
    re.compile(r"Seite\s+1\s+von\s+\d+", re.IGNORECASE),
    re.compile(r"Seite\s*[:\-]?\s*1(?:\s|$|[^0-9])", re.IGNORECASE),
    # "1 / N" or "1/N" at end of line (common pagination)
    re.compile(r"(?:^|\s)1\s*/\s*\d+(?:\s|$)", re.MULTILINE),
    # "Folha 1 de N" (Portuguese)
    re.compile(r"Folha\s+1\s+de\s+\d+", re.IGNORECASE),
    # "Feuille 1 / N" or "Feuille 1 sur N" (French)
    re.compile(r"Feuille\s+1\s+(?:sur|/)\s*\d+", re.IGNORECASE),
    # "Hoja 1 de N" (Spanish)
    re.compile(r"Hoja\s+1\s+de\s+\d+", re.IGNORECASE),
    # ---------------------------------------------------------------------------
    # Document-type headers (each occurrence = a new document)
    # "GUIA DE REMESSA" — Portuguese delivery/dispatch note header
    re.compile(r"GUIA\s+DE\s+REMESSA", re.IGNORECASE),
]

# Patterns that indicate a CONTINUATION page (NOT a first page).
# Used as a negative filter to avoid marking continuation pages as boundaries.
CONTINUATION_PAGE_PATTERNS: list[re.Pattern] = [
    # "Albarán 2Página 2 desde" -> continuation (page 2+)
    re.compile(r"Albar[aá]n\s+\d+\s*P[aá]g(?:ina)?\s*[2-9]\d*\s+desde", re.IGNORECASE),
    # "Página 2 de N", "Page 2 of N", etc.
    re.compile(r"P[aá]g(?:ina)?\.?\s*[:\-]?\s*[2-9]\d*\s+de\s+\d+", re.IGNORECASE),
    re.compile(r"Page\s+[2-9]\d*\s+of\s+\d+", re.IGNORECASE),
]


def _is_continuation_page(text: str) -> bool:
    """Check if a page is a continuation (page 2+) — should NOT be treated as first page."""
    for pattern in CONTINUATION_PAGE_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _is_first_page_heuristic(text: str) -> bool:
    """Check if a page's text matches first-page pagination patterns.

    Also checks that the page is NOT a continuation page to avoid false positives.
    """
    # If this is clearly a continuation page, it is NOT a first page
    if _is_continuation_page(text):
        return False

    for pattern in FIRST_PAGE_PATTERNS:
        if pattern.search(text):
            return True
    return False


def detect_boundaries(pages_text: list[PageText]) -> list[PageRange]:
    """Detect document boundaries given per-page text.

    Strategy:
    1. Check each page for first-page patterns (heuristic).
    2. Pages with a match start a new document.
    3. If no patterns are found on ANY page, treat the entire PDF as one document.

    Returns a list of PageRange (0-based, inclusive).
    """
    if not pages_text:
        return []

    # Phase 1: identify first-page indices using heuristics
    first_page_indices: list[int] = []
    for pt in pages_text:
        if _is_first_page_heuristic(pt.text):
            first_page_indices.append(pt.page)

    logger.info(
        "boundary_detection",
        total_pages=len(pages_text),
        first_pages_found=len(first_page_indices),
        indices=first_page_indices,
    )

    # If NO first-page markers found, treat entire PDF as one document
    if not first_page_indices:
        logger.info("no_boundary_markers", msg="Treating entire PDF as single document")
        return [
            PageRange(
                start_page=0,
                end_page=len(pages_text) - 1,
            )
        ]

    # The very first page of the PDF is always a document start,
    # even if it does NOT match a first-page pattern.
    if first_page_indices[0] != 0:
        first_page_indices.insert(0, 0)

    # Phase 2: build ranges
    ranges: list[PageRange] = []
    for i, start in enumerate(first_page_indices):
        if i + 1 < len(first_page_indices):
            end = first_page_indices[i + 1] - 1
        else:
            end = len(pages_text) - 1
        ranges.append(PageRange(start_page=start, end_page=end))

    logger.info("boundaries_detected", documents=len(ranges))
    return ranges
