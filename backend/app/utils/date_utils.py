from datetime import date, datetime
from typing import Tuple

def parse_date(s: str) -> date:
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", 
        "%d %b %Y", "%b %d %Y", "%d/%m/%y",
        "%d-%b-%Y", "%d-%b-%y", "%b %d, %Y"
    ]
    s = s.strip()
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not parse date {s}")

def month_str(d: date) -> str:
    return d.strftime("%Y-%m")

def resolve_relative_period(expr: str, anchor: date) -> Tuple[date, date]:
    # simplified stub for resolve_relative_period
    return anchor, anchor
