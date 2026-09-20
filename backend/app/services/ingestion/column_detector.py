from dataclasses import dataclass, field
from typing import Optional, Any
import pandas as pd
import re
from app.utils.date_utils import parse_date
from app.utils.number_formats import parse_indian_number

CONFIDENCE_THRESHOLD = 0.75

@dataclass
class ColumnMapping:
    date_col: Optional[str] = None
    description_col: Optional[str] = None
    debit_col: Optional[str] = None
    credit_col: Optional[str] = None
    amount_col: Optional[str] = None
    balance_col: Optional[str] = None
    direction_col: Optional[str] = None
    reference_col: Optional[str] = None
    confidence: float = 0.0
    needs_confirmation: bool = False
    warnings: list[str] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    preview_rows: list[dict] = field(default_factory=list)


def normalize_header(h: Any) -> str:
    """Normalize column header: lowercase, strip punctuation & dots, collapse spaces."""
    cleaned = re.sub(r"[^\w\s]", " ", str(h).lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def detect_columns(df: pd.DataFrame) -> ColumnMapping:
    """Heuristically map DataFrame columns to transaction fields with token matching & content fallback."""
    mapping = ColumnMapping()
    raw_headers = [str(c) for c in df.columns]
    mapping.headers = raw_headers

    # Top 5 preview rows formatted as string-dict
    try:
        preview_df = df.head(5).fillna("")
        mapping.preview_rows = preview_df.astype(str).to_dict(orient="records")
    except Exception:
        mapping.preview_rows = []

    norm_headers = {orig: normalize_header(orig) for orig in raw_headers}

    # 1. Date column
    # Strict priority: Primary transaction date headers take precedence over value date headers
    primary_date_patterns = [
        r"^date$", r"^txn date$", r"^transaction date$", r"^trans date$",
        r"^posting date$", r"^trade date$", r"^payment date$"
    ]
    secondary_date_patterns = [
        r"^value dt$", r"^value date$", r"^val date$", r"^effective date$"
    ]

    for orig, norm in norm_headers.items():
        if any(re.match(p, norm) for p in primary_date_patterns):
            mapping.date_col = orig
            mapping.confidence += 0.30
            break

    if not mapping.date_col:
        for orig, norm in norm_headers.items():
            if any(re.match(p, norm) for p in secondary_date_patterns):
                mapping.date_col = orig
                mapping.confidence += 0.20
                break

    # 2. Description column
    desc_patterns = [
        r"^narration$", r"^description$", r"^particulars$", r"^remarks$",
        r"^transaction remarks$", r"^transaction details$", r"^details$",
        r"^desc$", r"^payee$", r"^merchant$", r"^notes$"
    ]
    for orig, norm in norm_headers.items():
        if any(re.match(p, norm) for p in desc_patterns):
            mapping.description_col = orig
            mapping.confidence += 0.30
            break

    # 3. Debit column
    debit_patterns = [
        r"^withdrawal amt$", r"^withdrawal amount$", r"^withdrawal$", r"^withdrawals$",
        r"^debit amt$", r"^debit amount$", r"^debit$", r"^debits$",
        r"^dr$", r"^dr amt$", r"^dr amount$", r"^paid out$", r"^money out$"
    ]
    for orig, norm in norm_headers.items():
        if any(re.match(p, norm) for p in debit_patterns):
            mapping.debit_col = orig
            mapping.confidence += 0.20
            break

    # 4. Credit column
    credit_patterns = [
        r"^deposit amt$", r"^deposit amount$", r"^deposit$", r"^deposits$",
        r"^credit amt$", r"^credit amount$", r"^credit$", r"^credits$",
        r"^cr$", r"^cr amt$", r"^cr amount$", r"^paid in$", r"^money in$"
    ]
    for orig, norm in norm_headers.items():
        if any(re.match(p, norm) for p in credit_patterns):
            mapping.credit_col = orig
            mapping.confidence += 0.20
            break

    # 5. Amount column (single amount with Dr/Cr indicator)
    amount_patterns = [
        r"^amount$", r"^txn amount$", r"^transaction amount$", r"^trans amount$",
        r"^net amount$", r"^total amount$"
    ]
    for orig, norm in norm_headers.items():
        if any(re.match(p, norm) for p in amount_patterns):
            mapping.amount_col = orig
            if not mapping.debit_col and not mapping.credit_col:
                mapping.confidence += 0.35
            break

    # 6. Balance column
    balance_patterns = [
        r"^closing balance$", r"^balance$", r"^running balance$",
        r"^available balance$", r"^closing bal$", r"^bal$", r"^account balance$"
    ]
    for orig, norm in norm_headers.items():
        if any(re.match(p, norm) for p in balance_patterns):
            mapping.balance_col = orig
            mapping.confidence += 0.10
            break

    # 7. Direction column
    dir_patterns = [
        r"^type$", r"^dr cr$", r"^cr dr$", r"^dr/cr$", r"^cr/dr$",
        r"^transaction type$", r"^debit credit$", r"^debit/credit$", r"^indicator$"
    ]
    for orig, norm in norm_headers.items():
        if any(re.match(p, norm) for p in dir_patterns):
            mapping.direction_col = orig
            break

    # 8. Reference column
    ref_patterns = [
        r"^chq ref no$", r"^chq/ref no$", r"^ref no$", r"^cheque no$",
        r"^utr$", r"^ref$", r"^reference$", r"^chq no$", r"^ref no cheque no$",
        r"^cheque ref no$", r"^trans id$", r"^transaction id$", r"^utr no$"
    ]
    for orig, norm in norm_headers.items():
        if any(re.match(p, norm) for p in ref_patterns):
            mapping.reference_col = orig
            break

    # --- Content-based Fallback Detection ---
    used_cols = {
        mapping.date_col, mapping.description_col, mapping.debit_col,
        mapping.credit_col, mapping.amount_col, mapping.balance_col,
        mapping.direction_col, mapping.reference_col
    }

    # Fallback 1: Date detection from column content
    if not mapping.date_col:
        for col in raw_headers:
            if col in used_cols:
                continue
            non_nulls = df[col].dropna().astype(str).str.strip()
            sample = non_nulls.head(20).tolist()
            if not sample:
                continue
            valid_date_count = 0
            for val in sample:
                try:
                    if parse_date(val):
                        valid_date_count += 1
                except Exception:
                    pass
            if valid_date_count / len(sample) >= 0.70:
                mapping.date_col = col
                mapping.confidence += 0.20
                used_cols.add(col)
                mapping.warnings.append(f"Inferred date column '{col}' from content inspection.")
                break

    # Fallback 2: Description detection from content
    if not mapping.description_col:
        for col in raw_headers:
            if col in used_cols:
                continue
            non_nulls = df[col].dropna().astype(str).str.strip()
            sample = non_nulls.head(20).tolist()
            if not sample:
                continue
            # Text strings with average length > 10 and not all numbers
            non_numeric = [s for s in sample if not re.match(r"^[\d,.\s\-+]+$", s)]
            if len(non_numeric) / len(sample) >= 0.70:
                avg_len = sum(len(s) for s in sample) / len(sample)
                if avg_len >= 10:
                    mapping.description_col = col
                    mapping.confidence += 0.20
                    used_cols.add(col)
                    mapping.warnings.append(f"Inferred description column '{col}' from content inspection.")
                    break

    # Fallback 3: Amount / Debit / Credit detection from content
    has_amount_source = bool(mapping.amount_col or (mapping.debit_col or mapping.credit_col))
    if not has_amount_source:
        numeric_candidates = []
        for col in raw_headers:
            if col in used_cols:
                continue
            non_nulls = df[col].dropna().astype(str).str.strip()
            sample = [s for s in non_nulls.head(20).tolist() if s]
            if not sample:
                continue
            valid_nums = sum(1 for s in sample if parse_indian_number(s) is not None)
            if valid_nums / len(sample) >= 0.60:
                numeric_candidates.append(col)

        if len(numeric_candidates) >= 2:
            mapping.debit_col = numeric_candidates[0]
            mapping.credit_col = numeric_candidates[1]
            mapping.confidence += 0.25
            mapping.warnings.append(f"Inferred debit ('{numeric_candidates[0]}') and credit ('{numeric_candidates[1]}') from content inspection.")
        elif len(numeric_candidates) == 1:
            mapping.amount_col = numeric_candidates[0]
            mapping.confidence += 0.25
            mapping.warnings.append(f"Inferred amount column '{numeric_candidates[0]}' from content inspection.")

    # Validation: Are core columns present?
    has_amount = bool(mapping.amount_col or (mapping.debit_col and mapping.credit_col) or mapping.debit_col or mapping.credit_col)
    is_valid = bool(mapping.date_col and mapping.description_col and has_amount)

    mapping.confidence = min(1.0, round(mapping.confidence, 2))
    mapping.needs_confirmation = not is_valid or mapping.confidence < CONFIDENCE_THRESHOLD

    return mapping
