import io
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionDirection
from app.models.budget import Budget
from app.models.goal import Goal, GoalType
from app.models.recurring import RecurringGroup, RecurringFrequency, RecurringStatus, RecurringType
from app.services.report.insights_engine import generate_monthly_report, DISCLAIMER_TEXT
from app.services.report.pdf_exporter import build_monthly_pdf


@pytest.fixture
def seeded_report_data(db: Session):
    """Seed minimal test data for report generation."""
    user = db.get(User, 77)
    if user and db.query(Transaction).filter_by(user_id=77).first():
        return user

    if not user:
        user = User(id=77, email="report_test@example.com", display_name="Report User", currency="INR")
        db.add(user)

    account = db.get(Account, 77)
    if not account:
        account = Account(
            id=77,
            user_id=77,
            name="HDFC Salary A/c",
            type=AccountType.bank,
            currency="INR",
            account_number_masked="1234",
        )
        db.add(account)

    # Transactions for 2024-08
    txns = [
        Transaction(
            user_id=77,
            account_id=77,
            date=date(2024, 8, 1),
            raw_description="SALARY CREDIT INFOSYS",
            merchant_normalized="Infosys",
            amount_minor=10000000,  # ₹1,00,000
            direction=TransactionDirection.income,
            category="Income",
        ),
        Transaction(
            user_id=77,
            account_id=77,
            date=date(2024, 8, 5),
            raw_description="SWIGGY BANGALORE",
            merchant_normalized="Swiggy",
            amount_minor=120000,  # ₹1,200
            direction=TransactionDirection.expense,
            category="Dining",
        ),
        Transaction(
            user_id=77,
            account_id=77,
            date=date(2024, 8, 6),
            raw_description="AMAZON INDIA",
            merchant_normalized="Amazon",
            amount_minor=450000,  # ₹4,500
            direction=TransactionDirection.expense,
            category="Shopping",
        ),
        Transaction(
            user_id=77,
            account_id=77,
            date=date(2024, 8, 10),
            raw_description="NETFLIX SUBSCRIPTION",
            merchant_normalized="Netflix",
            amount_minor=79900,  # ₹799
            direction=TransactionDirection.expense,
            category="Subscriptions",
            is_recurring=True,
        ),
    ]
    for t in txns:
        db.add(t)

    # Budget
    b = Budget(
        user_id=77,
        category="Dining",
        monthly_limit_minor=100000,  # ₹1,000 limit (spent ₹1,200 => exceeded)
        effective_from=date(2024, 1, 1),
    )
    db.add(b)

    # Goal
    g = Goal(
        user_id=77,
        name="Emergency Reserve",
        type=GoalType.emergency_fund,
        target_amount_minor=30000000,
        current_amount_minor=15000000,
        target_date=date(2025, 8, 1),
        monthly_contribution_planned_minor=1250000,
        is_active=True,
    )
    db.add(g)

    # Recurring Group
    rg = RecurringGroup(
        user_id=77,
        merchant="Netflix",
        avg_amount_minor=79900,
        frequency=RecurringFrequency.monthly,
        last_seen=date(2024, 8, 10),
        status=RecurringStatus.active,
        type=RecurringType.subscription,
    )
    db.add(rg)

    db.commit()
    return user


def test_generate_monthly_report(db: Session, seeded_report_data):
    report = generate_monthly_report(db, month_str="2024-08", user_id=77)

    assert report.month == "2024-08"
    assert report.month_name == "August 2024"
    assert report.cash_flow.income_minor == 10000000
    assert report.cash_flow.expense_minor == 649900
    assert report.cash_flow.net_savings_minor == 10000000 - 649900
    assert report.cash_flow.savings_rate_pct > 90.0
    assert report.disclaimer == DISCLAIMER_TEXT

    # Check categories
    cat_names = [c.category for c in report.top_categories]
    assert "Dining" in cat_names
    assert "Shopping" in cat_names
    assert "Subscriptions" in cat_names

    # Check budget status (Dining was ₹1,000 limit, spent ₹1,200 -> exceeded)
    dining_b = next((b for b in report.budgets if b.category == "Dining"), None)
    assert dining_b is not None
    assert dining_b.status == "exceeded"
    assert dining_b.spent_minor == 120000

    # Check actionable items generated
    assert len(report.action_items) > 0
    # Over-budget action item should be present
    budget_action = next((a for a in report.action_items if a.category == "budget"), None)
    assert budget_action is not None
    assert "Dining" in budget_action.title or "Dining" in budget_action.description


def test_build_monthly_pdf(db: Session, seeded_report_data):
    report = generate_monthly_report(db, month_str="2024-08", user_id=77)
    pdf_bytes = build_monthly_pdf(report)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


def test_reports_api_endpoints(client: TestClient, db: Session, seeded_report_data):
    # 1. Months endpoint
    res_months = client.get("/api/reports/months?user_id=77")
    assert res_months.status_code == 200
    data_months = res_months.json()
    assert "months" in data_months
    assert len(data_months["months"]) >= 1
    month_entry = next((m for m in data_months["months"] if m["month"] == "2024-08"), None)
    assert month_entry is not None
    assert month_entry["month_name"] == "August 2024"

    # 2. JSON Report endpoint
    res_report = client.get("/api/reports/2024-08?user_id=77")
    assert res_report.status_code == 200
    rep_json = res_report.json()
    assert rep_json["month"] == "2024-08"
    assert rep_json["cash_flow"]["income_minor"] == 10000000
    assert len(rep_json["top_categories"]) > 0
    assert len(rep_json["action_items"]) > 0
    assert "disclaimer" in rep_json

    # 3. PDF Download endpoint
    res_pdf = client.get("/api/reports/2024-08/pdf?user_id=77")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert "attachment; filename=FinPilot_Report_2024-08.pdf" in res_pdf.headers["content-disposition"]
    assert res_pdf.content.startswith(b"%PDF-")

    # 4. Bad request for invalid month
    res_bad = client.get("/api/reports/invalid-date?user_id=77")
    assert res_bad.status_code == 400

    # 5. Not found for month without transactions
    res_nf = client.get("/api/reports/2020-01?user_id=77")
    assert res_nf.status_code == 404
