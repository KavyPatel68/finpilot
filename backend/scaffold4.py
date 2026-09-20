import os
import json

base_dir = r"c:\Users\patel\OneDrive\Desktop\ai agent\finpilot\backend"
files = {}

# TESTS
files["tests/conftest.py"] = """import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.services.llm_provider import FakeLLMProvider, get_llm_provider

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    e = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    yield e
    Base.metadata.drop_all(bind=e)

@pytest.fixture
def db(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    def override_get_llm():
        return FakeLLMProvider()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm_provider] = override_get_llm
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
"""

files["tests/test_health.py"] = """def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_delete_data_endpoint_404_for_wrong_user(client):
    # user_id=999 doesn't exist but delete should still return 200 with zeros
    response = client.delete("/api/users/999/data")
    assert response.status_code == 200
    assert response.json().get("transactions") == 0
"""

# SEED DATA
files["data/seed/ground_truth.json"] = """{
  "seed_version": "1.0",
  "random_seed": 42,
  "user_id": 1,
  "date_range": {"start": "2024-04-01", "end": "2024-09-30"},
  "planted_scenarios": {
    "salary": {
      "description": "₹85,000 income on 1st of each month",
      "amount_minor": 8500000,
      "frequency": "monthly",
      "merchant": "SALARY CREDIT",
      "months": ["2024-04", "2024-05", "2024-06", "2024-07", "2024-08", "2024-09"]
    },
    "subscription_price_hike": {
      "description": "Netflix price increased from ₹649 to ₹799 in Aug 2024",
      "merchant": "Netflix",
      "old_amount_minor": 64900,
      "new_amount_minor": 79900,
      "hike_month": "2024-08"
    },
    "duplicate_charge": {
      "description": "Netflix charged twice on 2024-06-10",
      "merchant": "Netflix",
      "date": "2024-06-10",
      "amount_minor": 64900,
      "count": 2
    },
    "spending_spike": {
      "description": "Shopping spike in July 2024 (₹35,000 vs typical ₹2,000-5,000)",
      "month": "2024-07",
      "category": "Shopping",
      "total_amount_minor": 3500000,
      "typical_range_minor": [200000, 500000]
    },
    "own_account_transfer": {
      "description": "₹10,000 transfer from savings to credit card payment, monthly",
      "amount_minor": 1000000,
      "is_transfer": true,
      "accounts": ["HDFC Savings", "HDFC Credit Card"]
    },
    "recurring_subscriptions": [
      {"merchant": "Netflix", "frequency": "monthly", "base_amount_minor": 64900},
      {"merchant": "Spotify", "frequency": "monthly", "amount_minor": 11900},
      {"merchant": "Amazon Prime", "frequency": "quarterly", "amount_minor": 149900}
    ],
    "emi": {
      "merchant": "Home Loan EMI",
      "amount_minor": 1250000,
      "frequency": "monthly",
      "day_of_month": 7
    },
    "refund": {
      "merchant": "Amazon",
      "month": "2024-08",
      "amount_minor": 120000,
      "category": "Shopping",
      "subcategory": "Refund",
      "direction": "income"
    },
    "ambiguous_merchant": {
      "raw_description": "NEFT CR-GARG ENT 12345",
      "category": "Other",
      "note": "Could be income or transfer; needs LLM or user clarification"
    }
  },
  "expected_monthly_totals": {
    "2024-07": {
      "note": "Shopping spike month",
      "shopping_min_minor": 3000000
    }
  },
  "qa_anchors": {
    "top_category_by_spend": "EMI/Loans or Shopping (July spike month)",
    "subscription_count": 3,
    "anomaly_month": "2024-07",
    "price_hike_month": "2024-08"
  }
}
"""

files["data/seed/rules_dict.json"] = """{
  "rules": [
    {"keywords": ["salary", "sal cr", "sal credit"], "category": "Income", "direction": "income"},
    {"keywords": ["rent", "house rent"], "category": "Housing/Rent", "direction": "expense"},
    {"keywords": ["netflix"], "category": "Subscriptions"},
    {"keywords": ["spotify"], "category": "Subscriptions"},
    {"keywords": ["amazon prime"], "category": "Subscriptions"},
    {"keywords": ["zomato", "swiggy"], "category": "Dining"},
    {"keywords": ["ola", "uber", "rapido"], "category": "Transport"},
    {"keywords": ["hpcl", "bpcl", "iocl", "indian oil", "petrol", "fuel"], "category": "Fuel"},
    {"keywords": ["bigbasket", "blinkit", "grofers", "zepto", "dmart"], "category": "Groceries"},
    {"keywords": ["amazon", "flipkart", "myntra", "ajio", "nykaa"], "category": "Shopping"},
    {"keywords": ["electricity", "bescom", "mseb", "tata power", "adani electricity"], "category": "Utilities"},
    {"keywords": ["emi", "loan", "home loan", "car loan"], "category": "EMI/Loans"},
    {"keywords": ["atm", "cash withdrawal"], "category": "Other"},
    {"keywords": ["insurance", "lic", "hdfc life", "term plan"], "category": "Insurance"},
    {"keywords": ["hospital", "clinic", "pharmacy", "apollo", "1mg", "netmeds"], "category": "Health"},
    {"keywords": ["school", "college", "university", "udemy", "coursera"], "category": "Education"},
    {"keywords": ["makemytrip", "irctc", "yatra", "goibibo", "hotel", "airbnb"], "category": "Travel"},
    {"keywords": ["transfer", "imps", "neft", "rtgs"], "category": "Transfers"},
    {"keywords": ["bank charges", "gst", "service charge", "late fee"], "category": "Fees/Charges"}
  ]
}
"""

files["data/seed/synthetic_data.py"] = """import random
import os
import json
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionDirection, CategorySource
from app.services.categorization.taxonomy import CATEGORIES

def seed_data():
    random.seed(42)
    db = SessionLocal()
    init_db()

    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, email="test@example.com", display_name="Demo User", currency="INR")
        db.add(user)
        db.commit()

    savings = db.query(Account).filter(Account.name == "HDFC Savings").first()
    if not savings:
        savings = Account(user_id=1, name="HDFC Savings", type=AccountType.bank, currency="INR")
        db.add(savings)
        
    cc = db.query(Account).filter(Account.name == "HDFC Credit Card").first()
    if not cc:
        cc = Account(user_id=1, name="HDFC Credit Card", type=AccountType.card, currency="INR")
        db.add(cc)
    
    db.commit()
    
    start_date = date(2024, 4, 1)
    months = [start_date + relativedelta(months=i) for i in range(6)]
    
    transactions_to_add = []
    
    def add_txn(acc_id, d, desc, amount_minor, direction, cat, subcat=None, is_transfer=False):
        transactions_to_add.append(
            Transaction(
                user_id=1, account_id=acc_id, date=d, raw_description=desc,
                amount_minor=amount_minor, direction=direction, category=cat,
                subcategory=subcat, category_source=CategorySource.rule,
                is_transfer=is_transfer
            )
        )

    for i, m in enumerate(months):
        # Salary
        add_txn(savings.id, date(m.year, m.month, 1), "NEFT CR-SALARY CREDIT", 8500000, TransactionDirection.income, "Income")
        # Rent
        add_txn(savings.id, date(m.year, m.month, 5), "IMPS/123456789/Rent Payment", 2200000, TransactionDirection.expense, "Housing/Rent")
        # EMI
        add_txn(savings.id, date(m.year, m.month, 7), "Home Loan EMI", 1250000, TransactionDirection.expense, "EMI/Loans")
        
        # Netflix
        netflix_amt = 79900 if m >= date(2024, 8, 1) else 64900
        add_txn(cc.id, date(m.year, m.month, 10), "Netflix", netflix_amt, TransactionDirection.expense, "Subscriptions")
        if m == date(2024, 6, 1): # duplicate in June
            add_txn(cc.id, date(2024, 6, 10), "Netflix", 64900, TransactionDirection.expense, "Subscriptions")
            
        # Spotify
        add_txn(cc.id, date(m.year, m.month, 15), "Spotify", 11900, TransactionDirection.expense, "Subscriptions")
        
        # Prime
        if i in [0, 3]: # Apr, Jul
            add_txn(cc.id, date(m.year, m.month, 18), "Amazon Prime", 149900, TransactionDirection.expense, "Subscriptions")
            
        # Electricity
        add_txn(cc.id, date(m.year, m.month, 20), "BESCOM Electricity", random.randint(1800, 3500) * 100, TransactionDirection.expense, "Utilities")
        
        # Groceries
        for _ in range(3):
            add_txn(cc.id, date(m.year, m.month, random.randint(1, 28)), random.choice(["Blinkit", "BigBasket", "Zepto"]), random.randint(200, 2500) * 100, TransactionDirection.expense, "Groceries")
            
        # Dining
        for _ in range(4):
            add_txn(cc.id, date(m.year, m.month, random.randint(1, 28)), random.choice(["Zomato", "Swiggy", "UPI/DR/12345/Swiggy"]), random.randint(150, 2000) * 100, TransactionDirection.expense, "Dining")

        # Transport
        for _ in range(6):
            add_txn(cc.id, date(m.year, m.month, random.randint(1, 28)), random.choice(["Ola", "Uber"]), random.randint(80, 600) * 100, TransactionDirection.expense, "Transport")

        # Fuel
        add_txn(cc.id, date(m.year, m.month, random.randint(1, 28)), "HPCL Petrol Pump", random.randint(3000, 5000) * 100, TransactionDirection.expense, "Fuel")
        
        # ATM
        add_txn(savings.id, date(m.year, m.month, random.randint(1, 28)), "ATM Cash Withdrawal", random.randint(5000, 10000) * 100, TransactionDirection.expense, "Other")
        
        # Transfer
        d_trans = date(m.year, m.month, 25)
        add_txn(savings.id, d_trans, "Transfer to CC", 1000000, TransactionDirection.expense, "Transfers", is_transfer=True)
        add_txn(cc.id, d_trans, "Payment Received", 1000000, TransactionDirection.income, "Transfers", is_transfer=True)

        # Ambiguous
        if m == date(2024, 5, 1):
            add_txn(savings.id, date(m.year, m.month, 12), "NEFT CR-GARG ENT 12345", 500000, TransactionDirection.income, "Other")
            
        # Refund
        if m == date(2024, 8, 1):
            add_txn(cc.id, date(m.year, m.month, 22), "Amazon Refund", 120000, TransactionDirection.income, "Shopping", subcat="Refund")

        # Shopping
        if m == date(2024, 7, 1): # spike
            add_txn(cc.id, date(m.year, m.month, 14), "Amazon", 2500000, TransactionDirection.expense, "Shopping")
            add_txn(cc.id, date(m.year, m.month, 16), "Myntra", 1000000, TransactionDirection.expense, "Shopping")
        else:
            add_txn(cc.id, date(m.year, m.month, random.randint(1, 28)), "Amazon", random.randint(2000, 5000) * 100, TransactionDirection.expense, "Shopping")

    # Messy rows
    add_txn(savings.id, date(2024, 4, 10), "UPI/CR/98765/SALARY", 150000, TransactionDirection.income, "Income")
    add_txn(savings.id, date(2024, 4, 15), "Paid 1,500.00 to vendor", 150000, TransactionDirection.expense, "Other")

    for t in transactions_to_add:
        db.add(t)

    db.commit()
    print(f"Seeded {len(transactions_to_add)} transactions across {len(months)} months for user_id=1")
    db.close()

if __name__ == "__main__":
    seed_data()
"""

for path, content in files.items():
    with open(os.path.join(base_dir, path), "w", encoding="utf-8") as f:
        f.write(content)
