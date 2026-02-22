"""Tests for reconciliation engine."""

import pytest

from app.reconcile.engine import reconcile, ReconcileResult
from app.reconcile.po_normalizer import normalize_po, canonicalize_po, are_equivalent
from app.schemas.common import (
    Evidence,
    FinalStatus,
    MatchStatus,
    NextAction,
    PipelineMethod,
    PipelineResult,
)


def _make_result(
    po_primary: str | None = None,
    po_secondary: str | None = None,
    confidence: float = 0.9,
    method: PipelineMethod = PipelineMethod.LLM,
) -> PipelineResult:
    """Helper to create a PipelineResult."""
    return PipelineResult(
        po_primary=po_primary,
        po_secondary=po_secondary,
        supplier=None,
        confidence=confidence,
        method=method,
        found_keywords=[],
        evidence=[],
    )


class TestPONormalizer:
    def test_normalize_strips_spaces(self):
        assert normalize_po("5000 1234") == "50001234"

    def test_normalize_strips_non_digits(self):
        assert normalize_po("PO-5000/1234") == "50001234"

    def test_normalize_none(self):
        assert normalize_po(None) is None
        assert normalize_po("") is None

    def test_canonicalize_strips_leading_zeros(self):
        assert canonicalize_po("00012345", allow_leading_zero=True) == "12345"

    def test_canonicalize_no_strip(self):
        assert canonicalize_po("00012345", allow_leading_zero=False) == "00012345"

    def test_canonicalize_all_zeros(self):
        assert canonicalize_po("0000", allow_leading_zero=True) == "0"

    def test_are_equivalent_with_leading_zeros(self):
        assert are_equivalent("00050001234", "50001234", allow_leading_zero=True) is True

    def test_are_equivalent_without_leading_zeros(self):
        assert are_equivalent("00050001234", "50001234", allow_leading_zero=False) is False

    def test_are_equivalent_both_none(self):
        assert are_equivalent(None, None) is True

    def test_are_equivalent_one_none(self):
        assert are_equivalent("50001234", None) is False


class TestReconcileEngine:
    def test_match_ok_same_primary(self):
        """Both pipelines find the same primary PO."""
        a = _make_result(po_primary="50001234", confidence=0.9)
        b = _make_result(po_primary="50001234", confidence=0.85)

        result = reconcile(a, b)
        assert result.match_status == MatchStatus.MATCH_OK
        assert result.status == FinalStatus.OK
        assert result.next_action == NextAction.AUTO_OK
        assert result.decided_po_primary == "50001234"

    def test_mismatch_different_primaries(self):
        """Both pipelines find different POs."""
        a = _make_result(po_primary="50001111", confidence=0.9)
        b = _make_result(po_primary="80002222", confidence=0.9)

        result = reconcile(a, b)
        assert result.match_status == MatchStatus.MISMATCH
        assert result.status == FinalStatus.NOT_OK
        assert result.next_action == NextAction.SEND_TO_REVIEW

    def test_needs_review_both_empty(self):
        """Neither pipeline finds a PO."""
        a = _make_result(confidence=0.0)
        b = _make_result(confidence=0.0)

        result = reconcile(a, b)
        assert result.match_status == MatchStatus.NEEDS_REVIEW
        assert result.status == FinalStatus.NOT_OK

    def test_needs_review_one_empty(self):
        """One pipeline finds a PO, the other doesn't."""
        a = _make_result(po_primary="50001234", confidence=0.9)
        b = _make_result(confidence=0.0)

        result = reconcile(a, b)
        assert result.match_status == MatchStatus.NEEDS_REVIEW
        assert result.status == FinalStatus.NOT_OK
        assert result.decided_po_primary == "50001234"

    def test_match_ok_with_leading_zero_equivalence(self):
        """POs match after leading zero stripping."""
        a = _make_result(po_primary="00050001234", confidence=0.9)
        b = _make_result(po_primary="50001234", confidence=0.85)

        result = reconcile(a, b, allow_leading_zero=True)
        assert result.match_status == MatchStatus.MATCH_OK
        assert result.status == FinalStatus.OK

    def test_low_confidence_triggers_review(self):
        """Both match but confidence is too low."""
        a = _make_result(po_primary="50001234", confidence=0.3)
        b = _make_result(po_primary="50001234", confidence=0.4)

        result = reconcile(a, b, min_confidence=0.6)
        assert result.match_status == MatchStatus.NEEDS_REVIEW
        assert result.status == FinalStatus.NOT_OK

    def test_match_with_secondary_pos(self):
        """Both have primary + secondary, primaries match."""
        a = _make_result(po_primary="50001234", po_secondary="80005678", confidence=0.9)
        b = _make_result(po_primary="50001234", po_secondary="80005678", confidence=0.9)

        result = reconcile(a, b)
        assert result.match_status == MatchStatus.MATCH_OK
        assert result.status == FinalStatus.OK
        assert result.decided_po_primary == "50001234"
        assert result.decided_po_secondary == "80005678"
