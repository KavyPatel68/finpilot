from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
import pandas as pd
from datetime import date

from app.services.ingestion.column_detector import ColumnMapping, detect_columns
from app.services.ingestion.narration_classifier import classify_narration
from app.utils.amount import to_minor
from app.utils.date_utils import parse_date
from app.utils.number_formats import parse_indian_number

@dataclass
class ParsedTransaction:
    date: date
    raw_description: str
    amount_minor: int          # always positive
    direction: str             # 'income' | 'expense'
    merchant_hint: Optional[str] = None
    payment_method: Optional[str] = None
    balance_minor: Optional[int] = None
    source_row: int = 0

@dataclass
class ParseError:
    row: int
    raw: str
    reason: str

@dataclass
class ParseResult:
    transactions: list[ParsedTransaction] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)
    mapping: Optional[ColumnMapping] = None
    currency: str = 'INR'
    total_rows: int = 0
    headers: list[str] = field(default_factory=list)
    preview_rows: list[dict] = field(default_factory=list)

def parse_file(
    file_path_or_buffer,
    mapping: Optional[ColumnMapping] = None,
    currency: str = 'INR',
    file_type: str = 'csv',
) -> ParseResult:
    result = ParseResult(currency=currency)
    
    try:
        if file_type == 'xlsx':
            df = pd.read_excel(file_path_or_buffer)
        else:
            try:
                df = pd.read_csv(file_path_or_buffer, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path_or_buffer, encoding='latin-1')
    except Exception as e:
        result.errors.append(ParseError(row=0, raw="", reason=f"Failed to read file: {e}"))
        return result

    # Check for unnamed/unrecognized headers (like Unnamed: 0, Unnamed: 1)
    if all(str(col).startswith('Unnamed') for col in df.columns):
        try:
            if file_type == 'xlsx':
                df = pd.read_excel(file_path_or_buffer, header=1)
            else:
                try:
                    df = pd.read_csv(file_path_or_buffer, encoding='utf-8', header=1)
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path_or_buffer, encoding='latin-1', header=1)
        except Exception:
            pass

    df = df.dropna(how='all').dropna(axis=1, how='all')
    result.total_rows = len(df)
    result.headers = [str(c) for c in df.columns]

    try:
        preview_df = df.head(5).fillna("")
        result.preview_rows = preview_df.astype(str).to_dict(orient="records")
    except Exception:
        result.preview_rows = []

    if mapping is None:
        mapping = detect_columns(df)
    result.mapping = mapping
    if not mapping.headers:
        mapping.headers = result.headers
    if not mapping.preview_rows:
        mapping.preview_rows = result.preview_rows

    has_amount = bool(mapping.amount_col or (mapping.debit_col or mapping.credit_col))
    if not mapping.date_col or not mapping.description_col or not has_amount:
        mapping.needs_confirmation = True
        result.errors.append(ParseError(row=0, raw="", reason="Could not detect required columns (date, description, or amount/debit/credit)"))
        return result

    for i, row in df.iterrows():
        # multi-header skip
        if any(str(val).startswith('Unnamed:') for val in row.values):
            continue

        raw_str = str(row.to_dict())
        
        try:
            d_val = row.get(mapping.date_col)
            if pd.isna(d_val) or str(d_val).strip() == '':
                continue
            parsed_d = parse_date(str(d_val))
            if not parsed_d:
                result.errors.append(ParseError(row=i, raw=raw_str, reason=f"Invalid date: {d_val}"))
                continue

            desc_val = str(row.get(mapping.description_col, '')).strip()
            ref_val = None
            if mapping.reference_col:
                raw_ref = row.get(mapping.reference_col)
                if raw_ref is not None and not pd.isna(raw_ref):
                    ref_str = str(raw_ref).strip()
                    if ref_str and ref_str.lower() not in ('nan', 'none', '-', ''):
                        ref_val = ref_str

            amount_minor = 0
            direction = None

            if mapping.debit_col or mapping.credit_col:
                debit_val = row.get(mapping.debit_col) if mapping.debit_col else None
                credit_val = row.get(mapping.credit_col) if mapping.credit_col else None

                d_num = parse_indian_number(debit_val)
                c_num = parse_indian_number(credit_val)

                has_debit = d_num is not None and d_num != 0
                has_credit = c_num is not None and c_num != 0

                if has_debit and has_credit:
                    result.errors.append(ParseError(row=i, raw=raw_str, reason="Both debit and credit have values"))
                    continue
                elif has_debit:
                    amount_minor = to_minor(abs(d_num), currency)
                    direction = 'expense' if d_num > 0 else 'income'
                elif has_credit:
                    amount_minor = to_minor(abs(c_num), currency)
                    direction = 'income' if c_num > 0 else 'expense'
                else:
                    continue

            elif mapping.amount_col:
                amt_val = row.get(mapping.amount_col)
                if amt_val is None or pd.isna(amt_val) or str(amt_val).strip() == '':
                    continue

                raw_amt_str = str(amt_val).strip()
                val = parse_indian_number(raw_amt_str)
                if val is None or val == Decimal(0):
                    continue

                if mapping.direction_col:
                    dir_val = str(row.get(mapping.direction_col, '')).strip().upper()
                    if any(x in dir_val for x in ['DR', 'DEBIT', 'EXPENSE', '-']):
                        direction = 'expense'
                    elif any(x in dir_val for x in ['CR', 'CREDIT', 'INCOME', '+']):
                        direction = 'income'
                    else:
                        result.errors.append(ParseError(row=i, raw=raw_str, reason=f"Unknown direction: {dir_val}"))
                        continue
                else:
                    amt_upper = raw_amt_str.upper()
                    if 'CR' in amt_upper:
                        direction = 'income'
                    elif 'DR' in amt_upper:
                        direction = 'expense'
                    elif val < 0:
                        direction = 'expense'
                    else:
                        direction = 'income'

                amount_minor = to_minor(abs(val), currency)

            else:
                result.errors.append(ParseError(row=i, raw=raw_str, reason="Amount column(s) not mapped"))
                continue

            narration_info = classify_narration(desc_val)
            full_description = f"{desc_val} Ref:{ref_val}" if (ref_val and ref_val not in desc_val) else desc_val

            bal_minor = None
            if mapping.balance_col:
                bal_val = row.get(mapping.balance_col)
                if bal_val is not None and not pd.isna(bal_val) and str(bal_val).strip() != '':
                    parsed_bal = parse_indian_number(str(bal_val))
                    if parsed_bal is not None:
                        bal_minor = to_minor(parsed_bal, currency)

            txn = ParsedTransaction(
                date=parsed_d,
                raw_description=full_description,
                amount_minor=amount_minor,
                direction=direction,
                merchant_hint=narration_info.merchant_hint,
                payment_method=narration_info.payment_method,
                balance_minor=bal_minor,
                source_row=i
            )
            result.transactions.append(txn)
        except Exception as e:
            result.errors.append(ParseError(row=i, raw=raw_str, reason=str(e)))

    return result
