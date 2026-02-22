"""Pipeline B — Hybrid (regex-first) PO extraction with conservative LLM fallback.

Strategy:
1. Run regex-based extraction first (keywords + PO patterns).
2. If strong match found (high confidence), skip LLM → return REGEX result.
3. If weak/no match, fall back to LLM with a conservative prompt.
"""

from __future__ import annotations

import structlog

from app.config import settings
from app.schemas.common import Evidence, PageText, PipelineMethod, PipelineResult
from app.services.openai_client import call_openai_structured
from app.services.po_extraction import extract_po_regex, filter_result_by_supplier

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# PROMPT B — Conservative, strict evidence
# ---------------------------------------------------------------------------

PROMPT_B = """You are a conservative document analysis assistant extracting Purchase Order (PO) numbers from business documents.

TASK: Analyse the provided document text and extract PO numbers ONLY if you have strong evidence.

STRICT RULES:
1. Only accept a PO number if it appears directly adjacent to (same line or immediately next line) a PO-introducing keyword such as: Pedido, Encomenda, Requisição, Order, PO, Referência, Ref, Bestellnummer, Nº Pedido, V/REF, V/PEDIDO, Your reference, Votre référence, Su Pedido, or similar.
2. The PO must be a numeric string matching one of these formats:
   - 8 digits starting with 5, 8, 2, or 0
   - 4-8 digits starting with 4
   - 5-6 digits starting with 2
3. DO NOT accept numbers that are merely nearby but not clearly associated with a PO keyword.
4. DO NOT accept document numbers, invoice numbers, or other identifiers that are not POs.
5. If the evidence is ambiguous or the number could be something other than a PO, return null and set confidence to a low value (< 0.5).
6. Extract ALL PO numbers you find (there may be more than 2). Populate po_primary with the strongest-evidence PO, po_secondary with the second if present, and po_numbers with the complete list.
7. Provide evidence snippets showing the keyword and PO together.
8. Set confidence:
   - 0.9-1.0: PO immediately follows a keyword, no ambiguity
   - 0.7-0.89: PO near a keyword with clear context
   - 0.3-0.69: uncertain, possibly a PO but weak evidence
   - 0.0-0.29: no PO found
9. NEVER invent PO numbers. When in doubt, return null.
10. If you see multiple candidate numbers but cannot determine which is the PO, return null with confidence 0.3 and explain in evidence.

Return your analysis as structured JSON."""

# Threshold: if regex confidence >= this, skip LLM
REGEX_STRONG_THRESHOLD = 0.75


def run_pipeline_b(
    pages_text: list[PageText],
    page_offset: int = 0,
) -> PipelineResult:
    """Run Pipeline B (hybrid regex-first + LLM fallback).

    Args:
        pages_text: List of PageText for this document.
        page_offset: The 0-based page number offset (for evidence).

    Returns:
        PipelineResult with method=REGEX, HYBRID, or LLM.
    """
    logger.info("pipeline_b_start", pages=len(pages_text))

    # Step 1: try regex extraction
    page_tuples = [(pt.page, pt.text) for pt in pages_text]
    regex_result = extract_po_regex(page_tuples)

    logger.info(
        "pipeline_b_regex_result",
        po_primary=regex_result.po_primary,
        confidence=regex_result.confidence,
        keywords=len(regex_result.found_keywords),
    )

    # Step 2: decide if regex is strong enough
    if regex_result.po_primary and regex_result.confidence >= REGEX_STRONG_THRESHOLD:
        logger.info("pipeline_b_regex_strong", msg="Skipping LLM, regex result is confident")
        return regex_result

    # Step 3: fallback to LLM with conservative prompt
    logger.info("pipeline_b_llm_fallback", msg="Regex insufficient, calling LLM")

    doc_parts: list[str] = []
    for pt in pages_text:
        doc_parts.append(f"--- PAGE {pt.page} ---\n{pt.text}")
    full_text = "\n\n".join(doc_parts)

    if len(full_text) > 60000:
        full_text = full_text[:60000] + "\n\n[... text truncated ...]"

    raw = call_openai_structured(
        system_prompt=PROMPT_B,
        user_content=full_text,
        model=settings.pipeline_b_fallback_model,
    )

    evidence = []
    for ev in raw.get("evidence", []):
        evidence.append(Evidence(page=ev.get("page", 0), snippet=ev.get("snippet", "")))

    llm_result = PipelineResult(
        po_primary=raw.get("po_primary"),
        po_secondary=raw.get("po_secondary"),
        po_numbers=raw.get("po_numbers", []),
        supplier=raw.get("supplier"),
        confidence=float(raw.get("confidence", 0.0)),
        method=PipelineMethod.LLM,
        found_keywords=raw.get("found_keywords", []),
        evidence=evidence,
    )

    # If regex had SOME result, merge (hybrid)
    if regex_result.po_primary and not llm_result.po_primary:
        # Regex found something, LLM didn't → use regex but lower confidence
        logger.info("pipeline_b_hybrid", msg="Using regex result (LLM found nothing)")
        # Merge po_numbers from both
        merged_po_numbers = list(dict.fromkeys(
            regex_result.po_numbers + llm_result.po_numbers
        ))
        return PipelineResult(
            po_primary=regex_result.po_primary,
            po_secondary=regex_result.po_secondary,
            po_numbers=merged_po_numbers,
            supplier=llm_result.supplier or regex_result.supplier,
            confidence=min(regex_result.confidence, 0.6),
            method=PipelineMethod.HYBRID,
            found_keywords=list(
                dict.fromkeys(regex_result.found_keywords + llm_result.found_keywords)
            ),
            evidence=regex_result.evidence + llm_result.evidence,
        )

    if llm_result.po_primary:
        # If both found something, prefer LLM but mark as hybrid
        if regex_result.po_primary:
            llm_result.method = PipelineMethod.HYBRID
            llm_result.found_keywords = list(
                dict.fromkeys(llm_result.found_keywords + regex_result.found_keywords)
            )
            llm_result.evidence = llm_result.evidence + regex_result.evidence
            # Merge po_numbers from both, LLM first
            llm_result.po_numbers = list(dict.fromkeys(
                llm_result.po_numbers + regex_result.po_numbers
            ))

    logger.info(
        "pipeline_b_complete",
        po_primary=llm_result.po_primary,
        confidence=llm_result.confidence,
        method=llm_result.method,
    )
    return filter_result_by_supplier(llm_result, pages_text)
