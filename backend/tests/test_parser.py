import io
import tempfile
import pytest
from datetime import date
from decimal import Decimal
from app.services.ingestion.parser_csv import parse_file
from app.services.ingestion.column_detector import detect_columns
import pandas as pd

def parse_file_from_string(content: str, file_type: str = 'csv'):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(content)
        temp_path = f.name
    return parse_file(temp_path, file_type=file_type)

def test_basic_csv_debit_credit_columns():
    csv = """Date,Description,Debit,Credit,Balance
01/04/2024,SALARY CREDIT,,85000.00,185000.00
05/04/2024,Rent Payment,22000.00,,163000.00
10/04/2024,Netflix,649.00,,162351.00"""
    result = parse_file_from_string(csv, file_type='csv')
    assert len(result.transactions) == 3
    assert result.transactions[0].direction == 'income'
    assert result.transactions[0].amount_minor == 8500000
    assert result.transactions[1].direction == 'expense'
    assert result.transactions[1].amount_minor == 2200000
    assert len(result.errors) == 0

def test_single_amount_column_signed():
    csv = """Date,Narration,Amount
01/04/2024,Salary Credit,85000.00
05/04/2024,Rent,-22000.00"""
    result = parse_file_from_string(csv)
    assert result.transactions[0].direction == 'income'
    assert result.transactions[1].direction == 'expense'

def test_indian_number_format():
    csv = 'Date,Description,Debit,Credit\n01/04/2024,Salary,,"1,23,456.78"'
    result = parse_file_from_string(csv)
    assert len(result.transactions) > 0
    assert result.transactions[0].amount_minor == 12345678

def test_various_date_formats():
    from app.utils.date_utils import parse_date
    assert parse_date('01/04/2024') == date(2024, 4, 1)
    assert parse_date('1-Apr-2024') == date(2024, 4, 1)
    assert parse_date('Apr 01, 2024') == date(2024, 4, 1)
    assert parse_date('2024-04-01') == date(2024, 4, 1)

def test_bad_rows_are_errors_not_crashes():
    csv = """Date,Description,Debit,Credit
NOT_A_DATE,Some payment,500.00,
01/04/2024,Valid payment,500.00,"""
    result = parse_file_from_string(csv)
    assert len(result.transactions) == 1
    assert len(result.errors) == 1
    # row 0 is header, row 1 is NOT_A_DATE but it gets 0-indexed in iterrows
    # wait iterrows indices are 0 and 1, so the error might be row 0
    assert result.errors[0].row == 0

def test_upi_narration_parsing():
    from app.services.ingestion.narration_classifier import classify_narration
    info = classify_narration('UPI/DR/123456789/Swiggy')
    assert info.payment_method == 'UPI'
    assert 'SWIGGY' in (info.merchant_hint.upper() if info.merchant_hint else '')

def test_neft_is_likely_transfer():
    from app.services.ingestion.narration_classifier import classify_narration
    info = classify_narration('NEFT-INWARD-REF12345-GARG ENT')
    assert info.payment_method == 'NEFT'
    assert info.is_likely_transfer == True

def test_column_detector_debit_credit():
    df = pd.DataFrame({'Date': ['01/04/2024'], 'Description': ['Test'], 'Debit': [100.0], 'Credit': [None], 'Balance': [500.0]})
    mapping = detect_columns(df)
    assert mapping.debit_col == 'Debit'
    assert mapping.credit_col == 'Credit'
    assert mapping.date_col == 'Date'
