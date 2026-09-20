from decimal import Decimal, ROUND_HALF_UP

MINOR_UNIT_MAP = {"INR": 100, "USD": 100, "EUR": 100, "GBP": 100}


def to_minor(amount: Decimal, currency: str = "INR") -> int:
    """Convert decimal amount to minor units (integer). Uses Decimal arithmetic."""
    factor = MINOR_UNIT_MAP.get(currency.upper(), 100)
    return int((amount * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_minor(minor: int, currency: str = "INR") -> Decimal:
    """Convert minor units back to Decimal."""
    factor = MINOR_UNIT_MAP.get(currency.upper(), 100)
    return Decimal(minor) / Decimal(factor)


def format_indian_number(amount_dec: Decimal) -> str:
    """Formats decimal to Indian comma format, e.g. 1,23,456.78."""
    is_negative = amount_dec < 0
    abs_dec = abs(amount_dec)
    parts = f"{abs_dec:.2f}".split(".")
    int_part, dec_part = parts[0], parts[1]

    if len(int_part) <= 3:
        grouped = int_part
    else:
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        # Group remaining digits in pairs of 2 from right to left
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        grouped = ",".join(groups) + "," + last_three

    res = f"{grouped}.{dec_part}"
    return f"-{res}" if is_negative else res


def format_amount(minor: int, currency: str = "INR") -> str:
    """Format as ₹1,23,456.78 for INR or $1,234.56 for others."""
    dec = from_minor(minor, currency)
    curr = currency.upper()
    if curr == "INR":
        return f"₹{format_indian_number(dec)}"
    elif curr == "USD":
        return f"${float(dec):,.2f}"
    elif curr == "EUR":
        return f"€{float(dec):,.2f}"
    elif curr == "GBP":
        return f"£{float(dec):,.2f}"
    return f"{format_indian_number(dec)} {curr}"
