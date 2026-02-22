"""Reconciliation engine — compares Pipeline A vs Pipeline B results."""

from __future__ import annotations

import structlog

from app.config import settings
from app.reconcile.po_normalizer import are_equivalent, normalize_po
from app.schemas.common import (
    FinalStatus,
    MatchStatus,
    NextAction,
    PipelineResult,
)

logger = structlog.get_logger(__name__)


class ReconcileResult:
    """Outcome of reconciling two pipeline results."""

    def __init__(
        self,
        match_status: MatchStatus,
        decided_po_primary: str | None,
        decided_po_secondary: str | None,
        decided_po_numbers: list[str],
        status: FinalStatus,
        next_action: NextAction,
        reject_reason: str | None = None,
    ):
        self.match_status = match_status
        self.decided_po_primary = decided_po_primary
        self.decided_po_secondary = decided_po_secondary
        self.decided_po_numbers = decided_po_numbers
        self.status = status
        self.next_action = next_action
        self.reject_reason = reject_reason


def reconcile(
    result_a: PipelineResult,
    result_b: PipelineResult,
    min_confidence: float | None = None,
    allow_leading_zero: bool | None = None,
) -> ReconcileResult:
    """Reconcile outputs from Pipeline A and Pipeline B.

    Logic:
    - MATCH_OK if primary POs match (or sets intersect).
    - MISMATCH if both have valid POs but they don't match.
    - NEEDS_REVIEW if one is empty and the other has values, both empty,
      or confidence is below threshold.
    """
    if min_confidence is None:
        min_confidence = settings.min_confidence
    if allow_leading_zero is None:
        allow_leading_zero = settings.allow_leading_zero_equiv

    a_primary = normalize_po(result_a.po_primary)
    a_secondary = normalize_po(result_a.po_secondary)
    b_primary = normalize_po(result_b.po_primary)
    b_secondary = normalize_po(result_b.po_secondary)

    a_set = {v for v in [a_primary, a_secondary] if v}
    b_set = {v for v in [b_primary, b_secondary] if v}

    # Build full PO sets from po_numbers lists (richer comparison)
    a_all_normalized = [normalize_po(p) for p in result_a.po_numbers if normalize_po(p)]
    b_all_normalized = [normalize_po(p) for p in result_b.po_numbers if normalize_po(p)]
    if a_all_normalized:
        a_set = set(a_all_normalized)
    if b_all_normalized:
        b_set = set(b_all_normalized)

    # Check confidence threshold
    low_confidence = (
        result_a.confidence < min_confidence and result_b.confidence < min_confidence
    )

    logger.info(
        "reconcile_start",
        a_primary=a_primary,
        a_secondary=a_secondary,
        b_primary=b_primary,
        b_secondary=b_secondary,
        conf_a=result_a.confidence,
        conf_b=result_b.confidence,
    )

    # Case 1: both empty
    if not a_set and not b_set:
        return ReconcileResult(
            match_status=MatchStatus.NEEDS_REVIEW,
            decided_po_primary=None,
            decided_po_secondary=None,
            decided_po_numbers=[],
            status=FinalStatus.NOT_OK,
            next_action=NextAction.SEND_TO_REVIEW,
            reject_reason="Both pipelines returned no PO",
        )

    # Case 2: one empty, other has values
    if (a_set and not b_set) or (b_set and not a_set):
        source = result_a if a_set else result_b
        decided_primary = normalize_po(source.po_primary)
        decided_secondary = normalize_po(source.po_secondary)
        source_po_numbers = source.po_numbers if source.po_numbers else [
            p for p in [source.po_primary, source.po_secondary] if p
        ]

        # If confidence is high enough, might be OK
        if source.confidence >= min_confidence:
            return ReconcileResult(
                match_status=MatchStatus.NEEDS_REVIEW,
                decided_po_primary=source.po_primary,  # keep original format
                decided_po_secondary=source.po_secondary,
                decided_po_numbers=source_po_numbers,
                status=FinalStatus.NOT_OK,
                next_action=NextAction.SEND_TO_REVIEW,
                reject_reason="Only one pipeline found PO",
            )
        else:
            return ReconcileResult(
                match_status=MatchStatus.NEEDS_REVIEW,
                decided_po_primary=source.po_primary,
                decided_po_secondary=source.po_secondary,
                decided_po_numbers=source_po_numbers,
                status=FinalStatus.NOT_OK,
                next_action=NextAction.SEND_TO_REVIEW,
                reject_reason="Only one pipeline found PO with low confidence",
            )

    # Case 3: both have values — check for match
    # Normalize both full sets for comparison
    a_norm_set = {normalize_po(p) for p in a_set}
    b_norm_set = {normalize_po(p) for p in b_set}

    # Also check with leading-zero equivalence
    sets_equal = a_norm_set == b_norm_set
    if not sets_equal and allow_leading_zero:
        # Try pairwise equivalence: every item in A has an equivalent in B and vice versa
        def _all_matched(src: set, tgt: set) -> bool:
            for s in src:
                if not any(are_equivalent(s, t, True) for t in tgt):
                    return False
            return True
        sets_equal = _all_matched(a_norm_set, b_norm_set) and _all_matched(b_norm_set, a_norm_set)

    # Check set intersection (for partial overlap)
    set_intersects = False
    for a_val in a_set:
        for b_val in b_set:
            if are_equivalent(a_val, b_val, allow_leading_zero):
                set_intersects = True
                break

    if sets_equal:
        # FULL MATCH — both pipelines agree 100% on all PO numbers
        if low_confidence:
            return ReconcileResult(
                match_status=MatchStatus.NEEDS_REVIEW,
                decided_po_primary=result_a.po_primary,
                decided_po_secondary=result_a.po_secondary or result_b.po_secondary,
                decided_po_numbers=list(dict.fromkeys(
                    result_a.po_numbers + result_b.po_numbers
                )),
                status=FinalStatus.NOT_OK,
                next_action=NextAction.SEND_TO_REVIEW,
                reject_reason="POs match but both have low confidence",
            )

        # Pick the decided POs (prefer A's primary since it matched)
        all_pos: list[str] = []
        for po in [result_a.po_primary, result_b.po_primary,
                    result_a.po_secondary, result_b.po_secondary]:
            if po and normalize_po(po) not in {normalize_po(p) for p in all_pos}:
                all_pos.append(po)

        decided_primary = all_pos[0] if all_pos else None
        decided_secondary = all_pos[1] if len(all_pos) > 1 else None

        # Build full decided_po_numbers from both pipelines
        decided_po_numbers = list(dict.fromkeys(
            result_a.po_numbers + result_b.po_numbers
        ))
        if not decided_po_numbers:
            decided_po_numbers = all_pos

        return ReconcileResult(
            match_status=MatchStatus.MATCH_OK,
            decided_po_primary=decided_primary,
            decided_po_secondary=decided_secondary,
            decided_po_numbers=decided_po_numbers,
            status=FinalStatus.OK,
            next_action=NextAction.AUTO_OK,
        )

    elif set_intersects:
        # PARTIAL MATCH — some POs overlap but sets are not identical
        decided_primary = result_a.po_primary or result_b.po_primary
        decided_secondary = result_a.po_secondary or result_b.po_secondary
        decided_po_numbers = list(dict.fromkeys(
            result_a.po_numbers + result_b.po_numbers
        ))
        if not decided_po_numbers:
            decided_po_numbers = [p for p in [decided_primary, decided_secondary] if p]

        return ReconcileResult(
            match_status=MatchStatus.NEEDS_REVIEW,
            decided_po_primary=decided_primary,
            decided_po_secondary=decided_secondary,
            decided_po_numbers=decided_po_numbers,
            status=FinalStatus.NOT_OK,
            next_action=NextAction.SEND_TO_REVIEW,
            reject_reason="Partial PO match — pipelines agree on some POs but not all",
        )

    else:
        # MISMATCH — both have POs but none match
        return ReconcileResult(
            match_status=MatchStatus.MISMATCH,
            decided_po_primary=None,
            decided_po_secondary=None,
            decided_po_numbers=[],
            status=FinalStatus.NOT_OK,
            next_action=NextAction.SEND_TO_REVIEW,
            reject_reason=f"Pipeline A={result_a.po_primary}, Pipeline B={result_b.po_primary}: no match",
        )
