"""Numeric parsing helpers — strip thousand separators, normalize decimals."""
from __future__ import annotations

import re


def parse_number(value: str | int | float | None) -> float | None:
    """Parse a number string that may contain thousand separators.

    Handles both Western (1,234.56) and Indonesian (1.234,56) formats.
    Returns None if the value cannot be parsed.

    Examples:
        parse_number("1,234.56")  -> 1234.56
        parse_number("1.234,56")  -> 1234.56
        parse_number("1234")      -> 1234.0
        parse_number(None)        -> None
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None

    # Remove currency symbols and whitespace
    s = re.sub(r"[Rp\s]", "", s)

    # Detect format:
    # 1. Indonesian with decimal comma: 1.234,56 — comma with ≤2 trailing digits AND dots present
    # 2. Indonesian thousands only: 1.234 or 5.200 — dot followed by exactly 3 digits, no comma
    # 3. Western: commas as thousands, dot as decimal
    if re.search(r",\d{1,2}$", s) and "." in s:
        # Indonesian: 1.234,56 → remove dots, replace comma with dot
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        # Indonesian thousands-only: 5.200 or 1.234.567 → remove dots
        s = s.replace(".", "")
    else:
        # Western or plain: remove commas (thousands) and keep dot as decimal
        s = s.replace(",", "")

    try:
        return float(s)
    except ValueError:
        return None
