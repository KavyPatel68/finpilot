import re
from typing import Any, List, Set, Tuple


def _extract_numbers_from_structure(data: Any) -> Set[float]:
    """Recursively extracts all numerical values from dictionaries, lists, or primitives."""
    numbers: Set[float] = set()
    if isinstance(data, (int, float)):
        numbers.add(float(data))
    elif isinstance(data, dict):
        for v in data.values():
            numbers.update(_extract_numbers_from_structure(v))
    elif isinstance(data, list):
        for item in data:
            numbers.update(_extract_numbers_from_structure(item))
    elif isinstance(data, str):
        # Look for amounts or percentages in strings like "₹1,234.50", "45%"
        cleaned = data.replace(",", "")
        matches = re.findall(r"[-+]?\d*\.?\d+", cleaned)
        for m in matches:
            try:
                numbers.add(float(m))
            except ValueError:
                pass
    return numbers


def extract_claims(text: str) -> List[Tuple[str, float]]:
    """Extracts monetary figures (₹, Rs) and percentage claims from an LLM response string."""
    claims: List[Tuple[str, float]] = []

    # 1. Matches ₹, INR, Rs., Rs followed by number (e.g. ₹1,200.50, Rs 500)
    rupee_pattern = re.compile(r"(?:₹|Rs\.?|INR)\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)", re.IGNORECASE)
    for match in rupee_pattern.finditer(text):
        num_str = match.group(1).replace(",", "")
        try:
            val = float(num_str)
            claims.append((match.group(0), val))
        except ValueError:
            pass

    # 2. Matches percentage figures like 15.5% or 40%
    pct_pattern = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*%")
    for match in pct_pattern.finditer(text):
        try:
            val = float(match.group(1))
            claims.append((match.group(0), val))
        except ValueError:
            pass

    return claims


def verify_answer(text: str, tool_results: List[Any]) -> Tuple[bool, str, List[str]]:
    """Verifies that all ₹ figures and % claims in `text` appear in `tool_results`.

    Returns:
        (is_valid, verified_text_or_fallback, ungrounded_claims)
    """
    if not tool_results:
        # If no tool was called, check if there are specific monetary claims
        claims = extract_claims(text)
        if claims:
            return False, "Unable to verify financial figures without source tool data.", [c[0] for c in claims]
        return True, text, []

    tool_numbers = set()
    for res in tool_results:
        tool_numbers.update(_extract_numbers_from_structure(res))

    claims = extract_claims(text)
    ungrounded: List[str] = []

    for raw_str, val in claims:
        # Check if val or minor units (val * 100) or rounded val matches any tool number within 1%
        matched = False
        for tn in tool_numbers:
            # Direct match or within 1% tolerance
            if tn != 0 and abs(val - tn) / max(abs(val), abs(tn), 1.0) <= 0.015:
                matched = True
                break
            # Minor units check (e.g., amount_minor = 120000 -> val = 1200)
            if tn != 0 and abs(val * 100 - tn) / max(abs(val * 100), abs(tn), 1.0) <= 0.015:
                matched = True
                break
            # Percentage decimal check (e.g., 0.155 vs 15.5%)
            if tn != 0 and abs(val / 100.0 - tn) <= 0.015:
                matched = True
                break
            # Integer equality
            if int(round(val)) == int(round(tn)):
                matched = True
                break

        if not matched:
            # Disregard common generic numbers (e.g. 30 days, 10 items, 1 month)
            if val in (1.0, 7.0, 10.0, 12.0, 30.0, 31.0, 365.0, 100.0):
                continue
            ungrounded.append(raw_str)

    if ungrounded:
        # Generate grounded fallback
        fallback = (
            "Here is the verified data from your financial records:\n"
            + _format_grounded_fallback(tool_results)
        )
        return False, fallback, ungrounded

    return True, text, []


def _format_grounded_fallback(tool_results: List[Any]) -> str:
    """Produces a clean deterministic summary from tool results when LLM answer contains unverified numbers."""
    lines = []
    for res in tool_results:
        if not isinstance(res, dict):
            continue
        if "categories" in res:
            for cat in res["categories"][:5]:
                name = cat.get("category", "Other")
                amt = cat.get("amount_formatted") or f"₹{cat.get('amount_minor', 0) / 100:,.2f}"
                lines.append(f"- **{name}**: {amt}")
        elif "merchants" in res:
            for m in res["merchants"][:5]:
                name = m.get("merchant", "Unknown")
                amt = m.get("amount_formatted") or f"₹{m.get('amount_minor', 0) / 100:,.2f}"
                lines.append(f"- **{name}**: {amt}")
        elif "total_income" in res or "total_expense" in res:
            inc = res.get("total_income_formatted", "₹0.00")
            exp = res.get("total_expense_formatted", "₹0.00")
            lines.append(f"- **Total Income**: {inc}")
            lines.append(f"- **Total Expense**: {exp}")
            if "net_savings_formatted" in res:
                lines.append(f"- **Net Savings**: {res['net_savings_formatted']}")
        elif "subscriptions" in res:
            for s in res["subscriptions"][:5]:
                m = s.get("merchant", "Service")
                amt = s.get("amount_formatted", "")
                freq = s.get("frequency", "monthly")
                lines.append(f"- **{m}**: {amt} ({freq})")
        elif "budget_status" in res:
            for b in res["budget_status"][:5]:
                cat = b.get("category", "")
                spent = b.get("spent_formatted", "")
                limit = b.get("limit_formatted", "")
                status = b.get("status", "")
                lines.append(f"- **{cat}**: {spent} of {limit} ({status})")

    if not lines:
        return "Source records retrieved successfully, but no direct breakdown was available to display."
    return "\n".join(lines)
