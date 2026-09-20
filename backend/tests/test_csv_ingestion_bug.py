import os
import io
from decimal import Decimal
import pytest
from app.models.account import Account, AccountType
from app.models.user import User
from app.models.transaction import Transaction, TransactionDirection
from app.utils.number_formats import parse_indian_number

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "finpilot_test_statement_hdfc_style.csv")

def ensure_user_and_account(db):
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, email="test@example.com", display_name="Test User", currency="INR")
        db.add(user)
        db.commit()

    acc = db.query(Account).filter(Account.id == 1).first()
    if not acc:
        acc = Account(id=1, user_id=1, name="HDFC Bank", type=AccountType.bank, currency="INR")
        db.add(acc)
        db.commit()
    return user, acc


def test_hdfc_statement_direct_ingestion(client, db):
    ensure_user_and_account(db)

    with open(FIXTURE_PATH, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/upload",
        data={"account_id": 1, "user_id": 1},
        files={"file": ("finpilot_test_statement_hdfc_style.csv", io.BytesIO(file_bytes), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "done"
    assert data["row_count"] == 168
    assert data["imported_count"] == 168
    assert data["duplicate_count"] == 0
    assert len(data["parse_errors"]) == 0
    assert data["imported_count"] + data["duplicate_count"] + len(data["parse_errors"]) == data["row_count"]

    doc_id = data["document_id"]
    txns = db.query(Transaction).filter(Transaction.document_id == doc_id).all()
    assert len(txns) == 168

    # Balance check:
    # Opening balance ₹1,85,000.00
    # Opening balance + total credits - total debits == closing balance ₹2,23,133.00
    opening_balance_minor = 18500000  # ₹1,85,000.00 in paise
    total_credits = sum(t.amount_minor for t in txns if t.direction == TransactionDirection.income)
    total_debits = sum(t.amount_minor for t in txns if t.direction == TransactionDirection.expense)
    expected_closing_balance = 22313300  # ₹2,23,133.00 in paise

    calculated_closing_balance = opening_balance_minor + total_credits - total_debits
    assert calculated_closing_balance == expected_closing_balance


def test_hdfc_statement_reupload_duplicate_detection(client, db):
    ensure_user_and_account(db)

    with open(FIXTURE_PATH, "rb") as f:
        file_bytes = f.read()

    # Second upload of the same file
    response = client.post(
        "/api/upload",
        data={"account_id": 1, "user_id": 1},
        files={"file": ("finpilot_test_statement_hdfc_style.csv", io.BytesIO(file_bytes), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["row_count"] == 168
    assert data["imported_count"] == 0
    assert data["duplicate_count"] == 168
    assert len(data["parse_errors"]) == 0
    assert data["imported_count"] + data["duplicate_count"] + len(data["parse_errors"]) == data["row_count"]


def test_sbi_style_statement_ingestion(client, db):
    ensure_user_and_account(db)

    csv_content = b"""Txn Date,Description,Ref No./Cheque No.,Debit,Credit,Balance
01/05/2024,SALARY CREDIT,REF12345,,50000.00,150000.00
02/05/2024,UPI/DR/ZOMATO,REF12346,350.00,,149650.00
03/05/2024,ELECTRICITY BILL,REF12347,1250.00,,148400.00
"""

    response = client.post(
        "/api/upload",
        data={"account_id": 1, "user_id": 1},
        files={"file": ("sbi_statement.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["row_count"] == 3
    assert data["imported_count"] == 3
    assert data["duplicate_count"] == 0
    assert len(data["parse_errors"]) == 0


def test_single_amount_with_direction(client, db):
    ensure_user_and_account(db)

    csv_content = b"""Date,Description,Amount,Type
10/05/2024,FREELANCE INVOICE,25000.00,CR
11/05/2024,GROCERY STORE,1800.00,DR
12/05/2024,COFFEE SHOP,220.00,DEBIT
"""

    response = client.post(
        "/api/upload",
        data={"account_id": 1, "user_id": 1},
        files={"file": ("single_amt_statement.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["row_count"] == 3
    assert data["imported_count"] == 3

    txns = db.query(Transaction).filter(Transaction.document_id == data["document_id"]).order_by(Transaction.id).all()
    assert len(txns) == 3
    assert txns[0].direction == TransactionDirection.income
    assert txns[0].amount_minor == 2500000
    assert txns[1].direction == TransactionDirection.expense
    assert txns[1].amount_minor == 180000
    assert txns[2].direction == TransactionDirection.expense
    assert txns[2].amount_minor == 22000


def test_messy_headers_with_spaces_and_casing(client, db):
    ensure_user_and_account(db)

    csv_content = b"""  Date  ,  NARRATION  ,  Withdrawal  Amt.  ,  DEPOSIT AMT.  ,  Closing Balance  
01/06/2024,INTEREST CREDIT,,"1,500.00","1,01,500.00"
02/06/2024,FUEL INDIAN OIL,"2,000.00",,"99,500.00"
"""

    response = client.post(
        "/api/upload",
        data={"account_id": 1, "user_id": 1},
        files={"file": ("messy_headers.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["row_count"] == 2
    assert data["imported_count"] == 2
    assert data["duplicate_count"] == 0


def test_unrecognizable_headers_triggers_needs_mapping_and_confirmation(client, db):
    ensure_user_and_account(db)

    # Completely unidentifiable headers and data that cannot be inferred automatically
    csv_content = b"""ColA,ColB,ColC,ColD
2024-07-01,Payment,500.00,1000.00
2024-07-02,Receipt,600.00,1600.00
"""

    response = client.post(
        "/api/upload",
        data={"account_id": 1, "user_id": 1},
        files={"file": ("custom_format.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_mapping"
    assert data["row_count"] == 2
    assert data["imported_count"] == 0
    assert "headers" in data
    assert "ColA" in data["headers"]
    assert "preview_rows" in data
    assert len(data["preview_rows"]) == 2

    doc_id = data["document_id"]

    # Confirm the mapping manually
    confirm_response = client.post(
        f"/api/documents/{doc_id}/confirm-mapping",
        json={
            "date_col": "ColA",
            "description_col": "ColB",
            "amount_col": "ColC",
            "balance_col": "ColD",
            "direction_col": None,
            "debit_col": None,
            "credit_col": None,
        },
    )

    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["status"] == "done"
    assert confirm_data["imported_count"] == 2
    assert confirm_data["row_count"] == 2


def test_parse_indian_number_edge_cases():
    assert parse_indian_number("1,23,456.78") == Decimal("123456.78")
    assert parse_indian_number("1,23,456") == Decimal("123456")
    assert parse_indian_number("(1,234.50)") == Decimal("-1234.50")
    assert parse_indian_number("₹ 2,23,133.00") == Decimal("223133.00")
    assert parse_indian_number("Rs. 45,000.00") == Decimal("45000.00")
    assert parse_indian_number("1,234.50 Dr") == Decimal("1234.50")
    assert parse_indian_number("1,234.50 Cr") == Decimal("1234.50")
    assert parse_indian_number("  ") is None
    assert parse_indian_number("-") is None
    assert parse_indian_number(None) is None
    assert parse_indian_number("N/A") is None
