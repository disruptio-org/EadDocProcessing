"""PO normalizer — strip, canonicalize, and compare PO numbers."""

from __future__ import annotations

import re


def normalize_po(raw: str | None) -> str | None:
    """Normalize a PO: remove spaces and non-digit characters.

    Returns None if the input is None or empty after normalization.
    """
    if not raw:
        return None
    cleaned = re.sub(r"[^0-9]", "", raw.strip())
    return cleaned if cleaned else None


def canonicalize_po(normalized: str | None, allow_leading_zero: bool = True) -> str | None:
    """Canonicalize a PO for equivalence comparison.

    If allow_leading_zero is True, strips leading zeros so that
    '00012345' and '12345' are considered equivalent.
    The original value is preserved elsewhere; this is for comparison only.
    """
    if not normalized:
        return None
    if allow_leading_zero:
        stripped = normalized.lstrip("0")
        return stripped if stripped else "0"
    return normalized


def are_equivalent(
    a: str | None,
    b: str | None,
    allow_leading_zero: bool = True,
) -> bool:
    """Check if two PO numbers are equivalent after normalization + canonicalization."""
    norm_a = normalize_po(a)
    norm_b = normalize_po(b)

    if norm_a is None and norm_b is None:
        return True  # both empty
    if norm_a is None or norm_b is None:
        return False

    canon_a = canonicalize_po(norm_a, allow_leading_zero)
    canon_b = canonicalize_po(norm_b, allow_leading_zero)

    return canon_a == canon_b
