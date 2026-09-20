import io
import pytest
from app.models.account import Account, AccountType
from app.models.user import User
from app.models.transaction import Transaction
from app.models.document import Document


def test_upload_csv_endpoint(client, db):
    # Ensure default user and account exist in test db
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, email="test@example.com", display_name="Test User", currency="INR")
        db.add(user)
        db.commit()

    acc = db.query(Account).filter(Account.id == 1).first()
    if not acc:
        acc = Account(id=1, user_id=1, name="Test Bank", type=AccountType.bank, currency="INR")
        db.add(acc)
        db.commit()

    csv_content = b"""Date,Description,Debit,Credit,Balance
01/05/2024,SALARY CREDIT,,75000.00,100000.00
02/05/2024,UPI/DR/123456/Swiggy,450.00,,99550.00
03/05/2024,Rent Payment,20000.00,,79550.00
"""

    response = client.post(
        "/api/upload",
        data={"account_id": 1, "user_id": 1},
        files={"file": ("statement.csv", io.BytesIO(csv_content), "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["row_count"] == 3
    assert data["imported_count"] == 3
    assert data["duplicate_count"] == 0
    assert len(data["parse_errors"]) == 0

    # Verify transactions in DB
    txns = db.query(Transaction).filter(Transaction.user_id == 1, Transaction.document_id == data["document_id"]).all()
    assert len(txns) == 3

    # Upload same file again to test duplicate detection
    response_dup = client.post(
        "/api/upload",
        data={"account_id": 1, "user_id": 1},
        files={"file": ("statement.csv", io.BytesIO(csv_content), "text/csv")}
    )
    assert response_dup.status_code == 200
    dup_data = response_dup.json()
    assert dup_data["status"] == "done"
    assert dup_data["imported_count"] == 0
    assert dup_data["duplicate_count"] == 3
