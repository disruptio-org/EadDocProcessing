"""Tests for PO regex pattern matching."""

import pytest

from app.services.po_extraction import match_po_patterns, PO_PATTERNS


class TestPOPatterns:
    """Test all 9 PO regex patterns."""

    # Pattern 1: 5XXXXXXX (8 digits starting with 5)
    def test_pattern_5_prefix_8_digits(self):
        assert "50001234" in match_po_patterns("PO: 50001234")
        assert "59999999" in match_po_patterns("Ref 59999999 end")

    def test_pattern_5_prefix_rejects_short(self):
        result = match_po_patterns("5000123")  # 7 digits
        assert "5000123" not in result

    def test_pattern_5_prefix_rejects_long(self):
        result = match_po_patterns("500012345")  # 9 digits
        assert "500012345" not in result

    # Pattern 2: 8XXXXXXX (8 digits starting with 8)
    def test_pattern_8_prefix_8_digits(self):
        assert "80001234" in match_po_patterns("Order 80001234")
        assert "89999999" in match_po_patterns("89999999")

    # Pattern 8: 2XXXXXXX (8 digits starting with 2)
    def test_pattern_2_prefix_8_digits(self):
        assert "20001234" in match_po_patterns("Pedido 20001234")

    # Pattern 9: 0XXXXXXX (8 digits starting with 0)
    def test_pattern_0_prefix_8_digits(self):
        assert "00012345" in match_po_patterns("Ref 00012345")

    # Pattern 5: 00XXXXXX (8 digits starting with 00)
    def test_pattern_00_prefix_8_digits(self):
        assert "00123456" in match_po_patterns("PO 00123456")

    # Pattern 6: 000XXXXX (8 digits starting with 000)
    def test_pattern_000_prefix_8_digits(self):
        assert "00012345" in match_po_patterns("Nr 00012345")

    # Pattern 7: 0000XXXX (8 digits starting with 0000)
    def test_pattern_0000_prefix_8_digits(self):
        assert "00001234" in match_po_patterns("Enc 00001234")

    # Pattern 4: 4XXX to 4XXXXXXX (4 + 3-7 digits)
    def test_pattern_4_prefix_4_to_8_digits(self):
        assert "41234" in match_po_patterns("Order 41234 done")  # 4 + 3 = 5 digits min
        # The pattern is 4\d{3,7} so: 4 digits min (4xxx), 8 digits max (4xxxxxxx)

    def test_pattern_4_prefix_various_lengths(self):
        assert "4123" in match_po_patterns("Ref 4123 end")        # 4 + 3
        assert "41234567" in match_po_patterns("PO 41234567 end")  # 4 + 7

    # Pattern 3: 2XXXX to 2XXXXX (2 + 4-5 digits)
    def test_pattern_2_prefix_5_to_6_digits(self):
        assert "21234" in match_po_patterns("Encomenda 21234")     # 2 + 4 but 5 digits

    def test_pattern_2_prefix_6_digits(self):
        assert "212345" in match_po_patterns("V/REF 212345 ok")   # 2 + 5

    # Extraction limits
    def test_max_two_pos(self):
        text = "PO 50001111 and 50002222 and 50003333"
        result = match_po_patterns(text)
        assert len(result) <= 2

    # Deduplication
    def test_deduplication(self):
        text = "Ref 50001234 another mention 50001234"
        result = match_po_patterns(text)
        assert result.count("50001234") == 1

    # No match
    def test_no_match(self):
        assert match_po_patterns("No PO here at all") == []
        assert match_po_patterns("Number 12345 is not a PO") == []

    # Edge: PO appears in different contexts
    def test_po_in_complex_text(self):
        text = """
        FACTURA Nº 12345
        Data: 2024-01-15
        V/Pedido: 50098765
        Total: 1234.56€
        """
        result = match_po_patterns(text)
        assert "50098765" in result

    def test_multiple_valid_pos(self):
        text = "Pedido 50001111 Ref 80002222"
        result = match_po_patterns(text)
        assert "50001111" in result
        assert "80002222" in result
