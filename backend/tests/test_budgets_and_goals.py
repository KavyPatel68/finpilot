import pytest
from datetime import date
from app.models.account import Account, AccountType
from app.models.user import User
from app.models.transaction import Transaction, TransactionDirection
from app.models.budget import Budget
from app.models.goal import Goal, GoalType
from app.models.recurring import RecurringGroup, RecurringFrequency, RecurringStatus, RecurringType


def test_budgets_lifecycle_and_spend_tracking(client, db):
    user = User(id=6, email="budget@test.com", display_name="Budget User", currency="INR")
    db.add(user)
    acc = Account(id=6, user_id=6, name="Bank", type=AccountType.bank, currency="INR")
    db.add(acc)

    # 1. Create budget: Dining limit = ₹10,000 (1,000,000 minor)
    res_create = client.post(
        "/api/budgets?user_id=6",
        json={"category": "Dining", "monthly_limit_minor": 1000000}
    )
    assert res_create.status_code == 200
    b_data = res_create.json()
    assert b_data["category"] == "Dining"
    assert b_data["monthly_limit_minor"] == 1000000

    # 2. Add an expense of ₹8,500 (850,000 minor) -> 85% spend (warning)
    t = Transaction(
        user_id=6,
        account_id=6,
        date=date(2024, 8, 15),
        raw_description="Swiggy Party Order",
        amount_minor=850000,
        direction=TransactionDirection.expense,
        category="Dining",
    )
    db.add(t)
    db.commit()

    # List budgets for that month
    res_list = client.get("/api/budgets?user_id=6&month=2024-08")
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) == 1
    assert items[0]["category"] == "Dining"
    assert items[0]["spent_minor"] == 850000
    assert items[0]["remaining_minor"] == 150000
    assert items[0]["spent_pct"] == 85.0
    assert items[0]["status"] == "warning"

    # 3. Add another expense of ₹2,000 -> total ₹10,500 > ₹10,000 (exceeded)
    t2 = Transaction(
        user_id=6,
        account_id=6,
        date=date(2024, 8, 20),
        raw_description="Restaurant Dinner",
        amount_minor=200000,
        direction=TransactionDirection.expense,
        category="Dining",
    )
    db.add(t2)
    db.commit()

    res_list2 = client.get("/api/budgets?user_id=6&month=2024-08")
    items2 = res_list2.json()
    assert items2[0]["spent_minor"] == 1050000
    assert items2[0]["status"] == "exceeded"

    # 4. Delete budget
    b_id = items2[0]["id"]
    res_del = client.delete(f"/api/budgets/{b_id}?user_id=6")
    assert res_del.status_code == 200


def test_goals_lifecycle_and_scenario_simulation(client, db):
    user = User(id=7, email="goal@test.com", display_name="Goal User", currency="INR")
    db.add(user)

    # 1. Create emergency fund goal: ₹300,000 target, ₹60,000 current
    res_create = client.post(
        "/api/goals?user_id=7",
        json={
            "name": "Emergency Fund",
            "type": "emergency_fund",
            "target_amount_minor": 30000000,  # ₹300,000
            "current_amount_minor": 6000000,   # ₹60,000 (20%)
            "target_date": "2027-12-31",
            "monthly_contribution_planned_minor": 1500000,  # ₹15,000
        }
    )
    assert res_create.status_code == 200
    g_data = res_create.json()
    assert g_data["name"] == "Emergency Fund"
    goal_id = g_data["id"]

    # 2. List goals and verify progress calculations
    res_list = client.get("/api/goals?user_id=7")
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) == 1
    assert items[0]["progress_pct"] == 20.0
    assert items[0]["months_remaining"] is not None

    # 3. Simulate cutting dining spend by ₹5,000 (500,000 minor)
    res_sim = client.post(
        "/api/goals/simulate?user_id=7",
        json={
            "goal_id": goal_id,
            "cut_category": "Dining",
            "cut_amount_minor": 500000,
        }
    )
    assert res_sim.status_code == 200
    sim = res_sim.json()
    assert sim["goal_id"] == goal_id
    assert sim["months_saved"] >= 1
    assert "Emergency Fund" in sim["narrative"]
    assert "Dining" in sim["narrative"]


def test_upcoming_obligations_endpoint(client, db):
    user = User(id=8, email="oblig@test.com", display_name="Obligation User", currency="INR")
    db.add(user)

    # Add active recurring group
    rec = RecurringGroup(
        user_id=8,
        merchant="Home Loan EMI",
        avg_amount_minor=1500000,
        frequency=RecurringFrequency.monthly,
        next_expected_date=date.today(),
        last_seen=date.today(),
        status=RecurringStatus.active,
        type=RecurringType.emi,
    )
    db.add(rec)
    db.commit()

    res = client.get("/api/subscriptions/upcoming?user_id=8&days=30")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 1
    assert data["total_upcoming_minor"] >= 1500000
    assert any(it["merchant"] == "Home Loan EMI" for it in data["items"])
