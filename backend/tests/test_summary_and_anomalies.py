import pytest
from datetime import date
from app.models.account import Account, AccountType
from app.models.user import User
from app.models.transaction import Transaction, TransactionDirection
from app.services.analytics.monthly_summary import generate_monthly_summary
from app.services.analytics.anomaly_detector import detect_anomalies


def test_monthly_summary_calculation(db):
    user = User(id=4, email="summary@test.com", display_name="Summary User", currency="INR")
    db.add(user)
    acc = Account(id=4, user_id=4, name="Savings", type=AccountType.bank, currency="INR")
    db.add(acc)

    # 1 income and 2 expenses
    t_inc = Transaction(
        user_id=4,
        account_id=4,
        date=date(2024, 5, 1),
        raw_description="Salary Credit",
        amount_minor=10000000,  # ₹100,000
        direction=TransactionDirection.income,
        category="Income",
    )
    t_exp1 = Transaction(
        user_id=4,
        account_id=4,
        date=date(2024, 5, 5),
        raw_description="Rent Payment",
        amount_minor=2500000,  # ₹25,000
        direction=TransactionDirection.expense,
        category="Housing/Rent",
    )
    t_exp2 = Transaction(
        user_id=4,
        account_id=4,
        date=date(2024, 5, 12),
        raw_description="Grocery Supermarket",
        amount_minor=1500000,  # ₹15,000
        direction=TransactionDirection.expense,
        category="Groceries",
    )
    db.add_all([t_inc, t_exp1, t_exp2])
    db.commit()

    summary = generate_monthly_summary(db, month_str="2024-05", user_id=4)

    assert summary.payload["income_minor"] == 10000000
    assert summary.payload["expense_minor"] == 4000000
    assert summary.payload["net_savings_minor"] == 6000000
    assert summary.payload["savings_rate_pct"] == 60.0
    assert len(summary.payload["top_categories"]) == 2
    assert summary.payload["top_categories"][0]["category"] == "Housing/Rent"
    assert "In May 2024" in (summary.generated_text or "")


def test_duplicate_charge_and_spike_detection(db):
    user = User(id=5, email="anomaly@test.com", display_name="Anomaly User", currency="INR")
    db.add(user)
    acc = Account(id=5, user_id=5, name="Card", type=AccountType.card, currency="INR")
    db.add(acc)

    # 1. Duplicate charge on same day (e.g. Netflix twice)
    d1 = Transaction(
        user_id=5,
        account_id=5,
        date=date(2024, 6, 10),
        raw_description="Netflix",
        amount_minor=64900,
        direction=TransactionDirection.expense,
        category="Subscriptions",
    )
    d2 = Transaction(
        user_id=5,
        account_id=5,
        date=date(2024, 6, 10),
        raw_description="Netflix REF#DUP123",
        amount_minor=64900,
        direction=TransactionDirection.expense,
        category="Subscriptions",
    )

    # 2. Spending baseline and spike:
    # Month 1 (May): Shopping = ₹2,000
    s_base = Transaction(
        user_id=5,
        account_id=5,
        date=date(2024, 5, 15),
        raw_description="Amazon Shopping",
        amount_minor=200000,
        direction=TransactionDirection.expense,
        category="Shopping",
    )
    # Month 2 (June): Shopping = ₹30,000 (15x spike)
    s_spike = Transaction(
        user_id=5,
        account_id=5,
        date=date(2024, 6, 18),
        raw_description="Amazon Shopping Big Sale",
        amount_minor=3000000,
        direction=TransactionDirection.expense,
        category="Shopping",
    )

    db.add_all([d1, d2, s_base, s_spike])
    db.commit()

    insights = detect_anomalies(db, user_id=5)

    dup_insight = next((i for i in insights if i.type == "duplicate_charge"), None)
    assert dup_insight is not None
    assert "Netflix" in dup_insight.text
    assert d1.is_anomaly is True
    assert d2.is_anomaly is True

    spike_insight = next((i for i in insights if i.type == "spending_spike"), None)
    assert spike_insight is not None
    assert "Shopping" in spike_insight.text


def test_summary_and_insights_routers(client, db):
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, email="test@example.com", display_name="Test User", currency="INR")
        db.add(user)
        db.commit()

    # 1. Summary Months
    res_months = client.get("/api/summary/months?user_id=1")
    assert res_months.status_code == 200
    assert isinstance(res_months.json(), list)

    # 2. Summary GET
    res_summary = client.get("/api/summary?user_id=1")
    assert res_summary.status_code == 200
    assert "payload" in res_summary.json()

    # 3. Insights GET
    res_insights = client.get("/api/insights?user_id=1")
    assert res_insights.status_code == 200
    assert isinstance(res_insights.json(), list)
