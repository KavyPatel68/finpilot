from decimal import Decimal, InvalidOperation
from typing import Optional, Any
import re

def parse_indian_number(s: Any) -> Optional[Decimal]:
    """
    Parse numbers in various Indian & banking statement formats:
    - '1,23,456.78' -> Decimal('123456.78')
    - '(1,234.50)' -> Decimal('-1234.50')
    - '₹1,23,456.00' or 'Rs. 1,234' -> Decimal('123456.00') / Decimal('1234')
    - '1,234.50 Dr' / '1,234.50 Cr' -> Decimal('1234.50')
    - None, '', '-', 'N/A' -> None
    """
    if s is None:
        return None
    s_str = str(s).strip()
    if not s_str or s_str.lower() in ("nan", "none", "null", "-", "--", "n/a"):
        return None

    # Check for negative in parentheses: e.g. (1,234.50)
    is_negative = False
    if re.search(r"^\s*\(.+\)\s*$", s_str):
        is_negative = True
        s_str = re.sub(r"[\(\)]", "", s_str)
    elif s_str.startswith("-") or "- " in s_str:
        is_negative = True

    # Strip currency symbols, suffixes, and commas
    s_clean = re.sub(r"(?i)\b(inr|rs|cr|dr)\b", "", s_str)
    s_clean = s_clean.replace("₹", "").replace(",", "").replace("-", "").strip()

    # Extract digits and optional decimal part
    match = re.search(r"\d+(?:\.\d+)?", s_clean)
    if not match:
        return None

    try:
        val = Decimal(match.group(0))
        return -val if is_negative else val
    except (InvalidOperation, ValueError):
        return None
