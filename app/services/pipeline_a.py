"""Pipeline A — LLM-first PO extraction.

Strategy: Send the full document text to the LLM with a flexible prompt.
The LLM is instructed to find PO numbers based on keywords and context,
even in complex layouts (tables, columns, misaligned text).
"""

from __future__ import annotations

import structlog

from app.schemas.common import Evidence, PageText, PipelineMethod, PipelineResult
from app.services.openai_client import call_openai_structured

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# PROMPT A — Flexible, robust
# ---------------------------------------------------------------------------

PROMPT_A = """You are a document analysis assistant specialising in extracting Purchase Order (PO) numbers from business documents (invoices, delivery notes, packing lists, order confirmations).

TASK: Analyse the provided document text and extract PO numbers.

RULES:
1. Look for PO-introducing keywords such as: Pedido, Encomenda, Requisição, Order, PO, Referência, Ref, Bestellnummer, Nº Pedido, V/REF, V/PEDIDO, Your reference, Votre référence, Su Pedido, and similar terms in Portuguese, English, French, German, Spanish, or Italian.
2. The PO number typically appears AFTER or NEAR these keywords (same line, next line, same column, or adjacent cell in a table).
3. Valid PO patterns are numeric strings that match one of these formats:
   - 8 digits starting with 5, 8, 2, or 0 (e.g. 50001234, 80001234, 20001234, 00001234)
   - 4-8 digits starting with 4 (e.g. 41234, 412345678)
   - 5-6 digits starting with 2 (e.g. 21234, 212345)
4. Extract at most 2 PO numbers (primary and secondary). The primary should be the most prominent or first-found PO.
5. Also try to identify the supplier/vendor name from the document header or signature area.
6. Provide evidence: for each PO found, include the page number (0-based) and a short text snippet showing the PO in context.
7. Set confidence between 0.0 and 1.0:
   - 0.9-1.0: PO clearly found next to a keyword, unambiguous
   - 0.7-0.89: PO found with reasonable context, minor ambiguity
   - 0.5-0.69: PO found but weak evidence or far from keyword
   - 0.0-0.49: no PO found or very uncertain
8. DO NOT invent PO numbers. If you cannot find a valid PO, return null for po_primary and po_secondary with confidence 0.0.
9. Handle complex layouts: POs may appear in table cells, multi-column layouts, or with varying spacing.

Return your analysis as structured JSON."""


def run_pipeline_a(
    pages_text: list[PageText],
    page_offset: int = 0,
) -> PipelineResult:
    """Run Pipeline A (LLM-first) on a set of pages.

    Args:
        pages_text: List of PageText for this document.
        page_offset: The 0-based page number offset (for evidence).

    Returns:
        PipelineResult with method=LLM.
    """
    # Build the document text with page markers
    doc_parts: list[str] = []
    for pt in pages_text:
        doc_parts.append(f"--- PAGE {pt.page} ---\n{pt.text}")
    full_text = "\n\n".join(doc_parts)

    # Truncate to avoid excessive token usage (roughly 60k chars ≈ 15k tokens)
    if len(full_text) > 60000:
        full_text = full_text[:60000] + "\n\n[... text truncated ...]"

    logger.info("pipeline_a_start", pages=len(pages_text), text_len=len(full_text))

    raw = call_openai_structured(
        system_prompt=PROMPT_A,
        user_content=full_text,
    )

    # Parse evidence
    evidence = []
    for ev in raw.get("evidence", []):
        evidence.append(Evidence(page=ev.get("page", 0), snippet=ev.get("snippet", "")))

    result = PipelineResult(
        po_primary=raw.get("po_primary"),
        po_secondary=raw.get("po_secondary"),
        supplier=raw.get("supplier"),
        confidence=float(raw.get("confidence", 0.0)),
        method=PipelineMethod.LLM,
        found_keywords=raw.get("found_keywords", []),
        evidence=evidence,
    )

    logger.info(
        "pipeline_a_complete",
        po_primary=result.po_primary,
        confidence=result.confidence,
    )
    return result
