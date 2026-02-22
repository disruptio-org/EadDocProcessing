"""Tests for keyword matching in PO extraction."""

import pytest

from app.services.po_extraction import (
    find_keywords_in_text,
    extract_po_near_keywords,
    PO_KEYWORDS,
    _normalize_keyword,
)


class TestKeywordMatching:
    """Test keyword detection with accent and case tolerance."""

    def test_exact_match(self):
        """Exact keyword match (case-insensitive)."""
        found = find_keywords_in_text("Nº Pedido: 50001234")
        kw_names = [kw for kw, _pos in found]
        assert any("Pedido" in kw for kw in kw_names)

    def test_case_insensitive(self):
        """Keywords match regardless of case."""
        found = find_keywords_in_text("PEDIDO CLIENTE: 50001234")
        kw_names = [kw for kw, _pos in found]
        assert len(kw_names) > 0

    def test_accent_tolerance(self):
        """Keywords with accents match accent-less text."""
        # "Referência" should match "Referencia" (no accent)
        text_no_accent = "Referencia: 50001234"
        found = find_keywords_in_text(text_no_accent)
        kw_names = [kw for kw, _pos in found]
        # Should find "Referência" or "Referencia:" variant
        assert len(kw_names) > 0

    def test_accent_tolerance_reverse(self):
        """Text with accents matches accent-less keywords."""
        text_with_accent = "Requisição: 50001234"
        found = find_keywords_in_text(text_with_accent)
        kw_names = [kw for kw, _pos in found]
        assert any("Requis" in kw for kw in kw_names)

    def test_multiple_keywords(self):
        """Multiple keywords in same text."""
        text = "Pedido: 50001111\nV/REF: 80002222"
        found = find_keywords_in_text(text)
        kw_names = [kw for kw, _pos in found]
        assert len(kw_names) >= 2

    def test_keyword_near_po(self):
        """Extract POs near keywords."""
        text = "Nº Pedido: 50001234\nData: 2024-01-15"
        pos, kws, evidence = extract_po_near_keywords(text, page_num=0)
        assert "50001234" in pos
        assert len(evidence) > 0

    def test_keyword_po_next_line(self):
        """PO on the next line after keyword."""
        text = "V/PEDIDO:\n50001234"
        pos, kws, evidence = extract_po_near_keywords(text, page_num=1)
        assert "50001234" in pos

    def test_no_keyword_no_result(self):
        """No keyword → no PO extracted."""
        text = "This is a random text with number 50001234"
        pos, kws, evidence = extract_po_near_keywords(text, page_num=0)
        assert len(kws) == 0

    def test_keyword_without_po(self):
        """Keyword present but no valid PO nearby."""
        text = "Nº Pedido: ABCDEF"
        pos, kws, evidence = extract_po_near_keywords(text, page_num=0)
        assert len(pos) == 0
        assert len(kws) > 0  # keyword was found

    def test_german_keyword(self):
        """German keyword 'Bestellnummer' is detected."""
        text = "Bestellnummer: 50001234"
        pos, kws, evidence = extract_po_near_keywords(text, page_num=0)
        assert "50001234" in pos
        assert any("Bestellnummer" in kw for kw in kws)

    def test_french_keyword(self):
        """French keyword 'Numéro de commande' is detected."""
        text = "Numéro de commande: 80005678"
        pos, kws, evidence = extract_po_near_keywords(text, page_num=0)
        assert "80005678" in pos

    def test_spanish_keyword(self):
        """Spanish keyword 'Su número de orden' is detected."""
        text = "Su número de orden: 50001234"
        pos, kws, evidence = extract_po_near_keywords(text, page_num=0)
        assert "50001234" in pos

    def test_normalize_keyword_consistency(self):
        """Normalized keywords are lowercase, no accents, trimmed."""
        assert _normalize_keyword("Réf. BL interne:") == "ref. bl interne:"
        assert _normalize_keyword("  PEDIDO  ") == "pedido"
        assert _normalize_keyword("Nº Pedido:") == "n\u00ba pedido:" or "no pedido:" in _normalize_keyword("Nº Pedido:")

    def test_all_keywords_present(self):
        """Verify all keywords are in the list."""
        assert len(PO_KEYWORDS) >= 80  # we have ~85 keywords
