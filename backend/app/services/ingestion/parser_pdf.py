from dataclasses import dataclass, field
from typing import Optional
import pdfplumber
import pandas as pd
from app.services.ingestion.parser_csv import ParseResult, ParseError, ParsedTransaction, parse_file
from app.services.ingestion.column_detector import detect_columns, ColumnMapping
from app.services.ingestion.narration_classifier import classify_narration
from app.utils.date_utils import parse_date
from app.utils.amount import to_minor
from app.utils.number_formats import parse_indian_number

def parse_pdf(
    file_path: str,
    password: Optional[str] = None,
    currency: str = 'INR',
    mapping: Optional[ColumnMapping] = None,
) -> ParseResult:
    result = ParseResult(currency=currency)
    all_rows = []
    
    try:
        with pdfplumber.open(file_path, password=password) as pdf:
            extracted_text_chars = 0
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        # Clean up None values
                        clean_table = [[col if col is not None else '' for col in row] for row in table]
                        all_rows.extend(clean_table)
                else:
                    text = page.extract_text()
                    if text:
                        extracted_text_chars += len(text)
                        
            if not all_rows:
                if extracted_text_chars / max(1, len(pdf.pages)) < 20:
                    result.errors.append(ParseError(row=0, raw='', reason='PDF page has no extractable text. May be scanned/image-based.'))
                    return result
                # Just fail for now if we can't extract tables but text exists
                result.errors.append(ParseError(row=0, raw='', reason='No tables found in PDF.'))
                return result

    except Exception as e:
        if 'password' in str(e).lower() or 'encrypted' in str(e).lower() or 'Access denied' in str(e):
            raise ValueError('PDF is password-protected. Please provide the password.')
        result.errors.append(ParseError(row=0, raw="", reason=f"Failed to read PDF: {e}"))
        return result

    if not all_rows:
        return result

    # Deduplicate headers
    # Assumption: first row is header
    header = all_rows[0]
    data_rows = [row for row in all_rows[1:] if row != header]

    df = pd.DataFrame(data_rows, columns=header)
    
    # Run the same logic as the CSV parser from step 3 onwards
    # we can use the parse_file logic by mocking it with df
    
    if mapping is None:
        mapping = detect_columns(df)
    result.mapping = mapping

    if not mapping.date_col or not mapping.description_col:
        result.errors.append(ParseError(row=0, raw="", reason="Could not detect required columns (date, description)"))
        return result

    for i, row in df.iterrows():
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

            amount_minor = 0
            direction = None

            if mapping.debit_col or mapping.credit_col:
                debit_val = row.get(mapping.debit_col) if mapping.debit_col else None
                credit_val = row.get(mapping.credit_col) if mapping.credit_col else None

                has_debit = not pd.isna(debit_val) and str(debit_val).strip() != ''
                has_credit = not pd.isna(credit_val) and str(credit_val).strip() != ''

                if has_debit and has_credit:
                    result.errors.append(ParseError(row=i, raw=raw_str, reason="Both debit and credit have values"))
                    continue
                elif has_debit:
                    val = parse_indian_number(str(debit_val))
                    if val is None or val == 0:
                        continue
                    amount_minor = to_minor(val, currency)
                    direction = 'expense'
                elif has_credit:
                    val = parse_indian_number(str(credit_val))
                    if val is None or val == 0:
                        continue
                    amount_minor = to_minor(val, currency)
                    direction = 'income'
                else:
                    continue

            elif mapping.amount_col:
                amt_val = str(row.get(mapping.amount_col, '')).strip()
                if not amt_val or pd.isna(row.get(mapping.amount_col)):
                    continue
                
                is_cr_suffix = 'CR' in amt_val.upper()
                is_dr_suffix = 'DR' in amt_val.upper()

                val = parse_indian_number(amt_val)
                if val is None or val == 0:
                    continue

                if mapping.direction_col:
                    dir_val = str(row.get(mapping.direction_col, '')).upper()
                    if 'DR' in dir_val or 'DEBIT' in dir_val:
                        direction = 'expense'
                    elif 'CR' in dir_val or 'CREDIT' in dir_val:
                        direction = 'income'
                    else:
                        result.errors.append(ParseError(row=i, raw=raw_str, reason=f"Unknown direction: {dir_val}"))
                        continue
                else:
                    if is_cr_suffix:
                        direction = 'income'
                    elif is_dr_suffix:
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

            bal_minor = None
            if mapping.balance_col:
                bal_val = row.get(mapping.balance_col)
                if not pd.isna(bal_val) and str(bal_val).strip() != '':
                    parsed_bal = parse_indian_number(str(bal_val))
                    if parsed_bal is not None:
                        bal_minor = to_minor(parsed_bal, currency)

            txn = ParsedTransaction(
                date=parsed_d,
                raw_description=desc_val,
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
