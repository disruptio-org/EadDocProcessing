"""PO extraction using keywords and regex patterns.

This module contains:
- The full list of PO-introducing keywords
- Regex patterns for valid PO numbers (ordered by specificity)
- Functions to find keywords, match PO patterns, and extract POs from text
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

import structlog

from app.schemas.common import Evidence, PipelineMethod, PipelineResult

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# PO-INTRODUCING KEYWORDS (case-insensitive, accent-tolerant)
# ---------------------------------------------------------------------------

PO_KEYWORDS: list[str] = [
    "Bestellnummer",
    "CDE EDI No",
    "Client ordernumber",
    "Customer PO",
    "Delivery note",
    "Encomenda",
    "Encomenda cliente n.º",
    "ENCOMENDA N.º",
    "N comande client:",
    "N. PEDIDO/ENCOMENDA:",
    "N.PEDIDO",
    "N/REF.",
    "Nº Cmd/Best Nr",
    "Nº de commande",
    "Nº Pdo CLIENTE",
    "Nº Ped. Compra:",
    "Nº Pedido Cliente:",
    "Nº Pedido LM",
    "Nº Pedido:",
    "Nº. de Enc. CI.:",
    "Nostro Ordine",
    "Order Number:",
    "P.Clte",
    "Ped.Cliente",
    "PEDIDO CLIENTE",
    "Pedido Cliente",
    "Pedido del cliente Nº",
    "PEDIDO Nº",
    "PO no / date",
    "Project no:",
    "Ref",
    "Ref client:",
    "Réf. BL interne:",
    "REF:",
    "Referência",
    "REFERÊNCIA CLIENTE:",
    "Referencia:",
    "req",
    "Requisição",
    "S/PEDIDO:",
    "Su Encomenda",
    "Su nº de referencia",
    "Su Nº Pedido",
    "Su número de orden",
    "Su pedido",
    "Su Pedido :",
    "Su ref.: PEDIDO",
    "SU REFERENCIA",
    "Su Referencia:",
    "V. Requisição",
    "v/ Refª:",
    "V/ Requisição:",
    "V/Doc:",
    "V/REF",
    "V/REFª",
    "V/REQ.",
    "Vossa Encomenda:",
    "Vosso Pedido",
    "Vostro Ordine",
    "Votre comande nº",
    "Votre réf.:",
    "Votre référence de comande:",
    "Your reference",
    "Your reference:",
    "Pedido",
    "PEDIDO",
    "V/PEDIDO",
    "Expedição",
    "Expedicao",
    "Nº Expedição:",
    "Votre comande",
    "votre référence",
    "Réf commande",
    "Vx.Enc",
    "Nº pedido cliente:",
    "Ordeno.",
    "Order ref.:",
    "sua encomenda",
    "Ref.pedido cliente",
    "Referencia cliente",
    "Numéro de commande",
    "Numéro de pedido de",
    "Numéro de pedido",
    "N.º pedido",
    "Nummer",
    "Número de orden",
    "Réquisition",
    "V/ PEDIDO",
]


def _strip_accents(s: str) -> str:
    """Remove diacritics/accents for tolerant comparison."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize_keyword(kw: str) -> str:
    """Normalize a keyword for matching: lowercase, no accents, collapse whitespace."""
    return re.sub(r"\s+", " ", _strip_accents(kw).lower().strip())


# Pre-compute normalized keywords for fast lookup
_NORMALIZED_KEYWORDS: list[tuple[str, str]] = [
    (_normalize_keyword(kw), kw) for kw in PO_KEYWORDS
]

# Sort by length descending so longer keywords match first (avoid partial matches)
_NORMALIZED_KEYWORDS.sort(key=lambda x: len(x[0]), reverse=True)


# ---------------------------------------------------------------------------
# PO REGEX PATTERNS (ordered by specificity / longest-first)
# ---------------------------------------------------------------------------

# Each tuple: (pattern, description)
# NOTE: We use (?<!\d) and (?!\d) instead of \b because \b fails when
# digits are directly adjacent to letters (e.g., "53681855Numéro") — both
# digits and letters are \w, so \b doesn't fire between them.
PO_PATTERNS: list[tuple[re.Pattern, str]] = [
    # (1) Starts with 5 + 7 digits = 8 digits total
    (re.compile(r"(?<!\d)5\d{7}(?!\d)"), "5XXXXXXX"),
    # (2) Starts with 8 + 7 digits = 8 digits total
    (re.compile(r"(?<!\d)8\d{7}(?!\d)"), "8XXXXXXX"),
    # (8) Starts with 2 + 7 digits = 8 digits total
    (re.compile(r"(?<!\d)2\d{7}(?!\d)"), "2XXXXXXX (8-digit)"),
    # (9) Starts with 0 + 7 digits = 8 digits total
    (re.compile(r"(?<!\d)0\d{7}(?!\d)"), "0XXXXXXX"),
    # (5) Starts with 00 + 6 digits = 8 digits total
    (re.compile(r"(?<!\d)00\d{6}(?!\d)"), "00XXXXXX"),
    # (6) Starts with 000 + 5 digits = 8 digits total
    (re.compile(r"(?<!\d)000\d{5}(?!\d)"), "000XXXXX"),
    # (7) Starts with 0000 + 4 digits = 8 digits total
    (re.compile(r"(?<!\d)0000\d{4}(?!\d)"), "0000XXXX"),
    # (4) Starts with 4 + 3-7 digits
    (re.compile(r"(?<!\d)4\d{3,7}(?!\d)"), "4XXX-4XXXXXXX"),
    # (3) Starts with 2 + 4-5 digits
    (re.compile(r"(?<!\d)2\d{4,5}(?!\d)"), "2XXXX-2XXXXX"),
]

# ---------------------------------------------------------------------------
# NEGATIVE CONTEXT — labels that introduce NON-PO numbers (client IDs, etc.)
# ---------------------------------------------------------------------------
# If a number is preceded by any of these labels (within 30 chars), skip it.

NEGATIVE_CONTEXT_PATTERNS: list[re.Pattern] = [
    re.compile(r"Cliente[:\s]*$", re.IGNORECASE),
    re.compile(r"Client[:\s]*$", re.IGNORECASE),
    re.compile(r"Customer[:\s]*$", re.IGNORECASE),
    re.compile(r"Kunden(?:nummer)?[:\s]*$", re.IGNORECASE),
    re.compile(r"GLN[:\s]*$", re.IGNORECASE),
    re.compile(r"N[°º]?\s*GLN[:\s]*$", re.IGNORECASE),
    re.compile(r"NIF[:\s]*$", re.IGNORECASE),
    re.compile(r"IBAN\s", re.IGNORECASE),
    re.compile(r"SWIFT[:\s]*$", re.IGNORECASE),
    re.compile(r"[Cc]uenta[:\s]*$", re.IGNORECASE),
    re.compile(r"[Cc][oó]digo\s+banc[aá]rio[:\s]*$", re.IGNORECASE),
    re.compile(r"HRB\s*$", re.IGNORECASE),
    re.compile(r"VAT\s+number[:\s]*$", re.IGNORECASE),
    re.compile(r"Albar[aá]n\s+P[aá]g(?:ina)?\s*$", re.IGNORECASE),
]


def _is_negative_context(text: str, match_start: int, lookback: int = 40) -> bool:
    """Check if a matched number is preceded by a non-PO label."""
    prefix = text[max(0, match_start - lookback):match_start].rstrip()
    for pattern in NEGATIVE_CONTEXT_PATTERNS:
        if pattern.search(prefix):
            return True
    return False


def find_keywords_in_text(text: str) -> list[tuple[str, int]]:
    """Find all PO-introducing keywords in text.

    Returns list of (original_keyword, position_in_text).
    """
    normalized_text = _normalize_keyword(text)
    found: list[tuple[str, int]] = []
    seen_positions: set[int] = set()

    for norm_kw, original_kw in _NORMALIZED_KEYWORDS:
        start = 0
        while True:
            pos = normalized_text.find(norm_kw, start)
            if pos == -1:
                break
            # Avoid overlapping matches
            if pos not in seen_positions:
                found.append((original_kw, pos))
                seen_positions.add(pos)
            start = pos + 1

    return found


def match_po_patterns(text: str) -> list[str]:
    """Find all valid PO numbers in a text string.

    Filters out numbers preceded by negative-context labels (e.g., "Cliente:").
    Returns a deduplicated, ordered list (max 2 values).
    """
    candidates: list[str] = []
    seen: set[str] = set()

    for pattern, _desc in PO_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group()
            if value not in seen:
                # Skip numbers in negative context (client IDs, GLN, etc.)
                if _is_negative_context(text, match.start()):
                    continue
                seen.add(value)
                candidates.append(value)
                if len(candidates) >= 10:  # gather more, then trim
                    break

    # Deduplicate and return at most 2
    return candidates[:2]


def extract_po_near_keywords(
    text: str,
    page_num: int,
    context_chars: int = 200,
) -> tuple[list[str], list[str], list[Evidence]]:
    """Extract PO numbers found near keywords in a given text.

    Returns (po_candidates, found_keywords, evidence).
    """
    keywords_found = find_keywords_in_text(text)
    if not keywords_found:
        return [], [], []

    all_pos: list[str] = []
    kw_names: list[str] = []
    evidence: list[Evidence] = []
    seen_pos: set[str] = set()

    for kw_original, kw_pos in keywords_found:
        kw_names.append(kw_original)

        # The keyword position is in the NORMALIZED text, so we search
        # broadly around the keyword in the ORIGINAL text.
        # Look both BEFORE and AFTER the keyword (PO may precede keyword).
        search_start = max(0, kw_pos - context_chars)
        search_end = min(len(text), kw_pos + len(kw_original) + context_chars)
        context = text[search_start:search_end]

        # Also look at the line(s) around the keyword
        remaining = text[max(0, kw_pos - context_chars):]
        lines = remaining.split("\n")
        near_text = "\n".join(lines[:5])  # up to 5 nearby lines

        combined_search = context + " " + near_text
        pos = match_po_patterns(combined_search)

        for po in pos:
            if po not in seen_pos:
                seen_pos.add(po)
                all_pos.append(po)
                snippet = near_text[:150].strip()
                evidence.append(Evidence(page=page_num, snippet=snippet))

    # Deduplicate keyword names
    kw_names = list(dict.fromkeys(kw_names))

    return all_pos[:2], kw_names, evidence


def extract_po_regex(
    pages_text: list[tuple[int, str]],
) -> PipelineResult:
    """Run regex-based PO extraction across multiple pages.

    Args:
        pages_text: list of (page_number, text) tuples for the document.

    Returns:
        PipelineResult with method=REGEX.
    """
    all_pos: list[str] = []
    all_keywords: list[str] = []
    all_evidence: list[Evidence] = []
    seen_pos: set[str] = set()

    for page_num, text in pages_text:
        pos, kws, evs = extract_po_near_keywords(text, page_num)
        for po in pos:
            if po not in seen_pos:
                seen_pos.add(po)
                all_pos.append(po)
        all_keywords.extend(kws)
        all_evidence.extend(evs)

    # Deduplicate
    all_keywords = list(dict.fromkeys(all_keywords))
    all_pos = all_pos[:2]

    # Confidence heuristic
    if len(all_pos) >= 1 and len(all_keywords) >= 1:
        confidence = 0.85
    elif len(all_pos) >= 1:
        confidence = 0.5  # PO found but no keyword nearby → lower confidence
    else:
        confidence = 0.0

    return PipelineResult(
        po_primary=all_pos[0] if len(all_pos) >= 1 else None,
        po_secondary=all_pos[1] if len(all_pos) >= 2 else None,
        supplier=None,
        confidence=confidence,
        method=PipelineMethod.REGEX,
        found_keywords=all_keywords,
        evidence=all_evidence,
    )
