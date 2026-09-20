import pytest
from datetime import date
from app.models.account import Account, AccountType
from app.models.user import User
from app.models.transaction import Transaction, TransactionDirection
from app.models.budget import Budget
from app.models.goal import Goal, GoalType
from app.models.recurring import RecurringGroup, RecurringFrequency, RecurringStatus, RecurringType
from app.services.agent.tools import execute_tool
from app.services.agent.orchestrator import _is_investment_advice_query, run_agent


def test_agent_tools_execution(db):
    user = User(id=9, email="agent@test.com", display_name="Agent User", currency="INR")
    db.add(user)
    acc = Account(id=9, user_id=9, name="Bank", type=AccountType.bank, currency="INR")
    db.add(acc)

    t = Transaction(
        user_id=9,
        account_id=9,
        date=date(2024, 7, 10),
        raw_description="Netflix Subscription",
        amount_minor=64900,
        direction=TransactionDirection.expense,
        category="Subscriptions",
    )
    b = Budget(user_id=9, category="Subscriptions", monthly_limit_minor=100000, effective_from=date(2024, 7, 1))
    g = Goal(user_id=9, name="Rainy Day", type=GoalType.emergency_fund, target_amount_minor=5000000, current_amount_minor=1000000)
    db.add_all([t, b, g])
    db.commit()

    # 1. Search transactions tool
    res_search = execute_tool("search_transactions", {"query": "Netflix"}, db, user_id=9)
    assert res_search["count"] >= 1
    assert any("Netflix" in txn["merchant"] for txn in res_search["transactions"])

    # 2. Budget status tool
    res_budget = execute_tool("get_budget_status", {"month": "2024-07"}, db, user_id=9)
    assert "budgets" in res_budget
    assert any(item["category"] == "Subscriptions" for item in res_budget["budgets"])

    # 3. Goals tool
    res_goals = execute_tool("get_goals", {}, db, user_id=9)
    assert res_goals["count"] >= 1
    assert res_goals["goals"][0]["name"] == "Rainy Day"

    # 4. Spending cut simulation
    res_sim = execute_tool("simulate_spending_cut", {"goal_name": "Rainy Day", "cut_category": "Dining", "cut_amount_rupees": 2000}, db, user_id=9)
    assert "months_saved" in res_sim
    assert "Rainy Day" in res_sim["goal_name"]


def test_investment_advice_refusal_guardrail():
    # Should trigger refusal
    assert _is_investment_advice_query("What stock should I buy today?") is True
    assert _is_investment_advice_query("Should I invest in crypto?") is True
    assert _is_investment_advice_query("Which mutual fund has best returns?") is True

    # Legitimate questions should NOT trigger refusal
    assert _is_investment_advice_query("How much did I spend on groceries last month?") is False
    assert _is_investment_advice_query("What are my active subscriptions?") is False


@pytest.mark.asyncio
async def test_run_agent_refusal_and_fallback(db):
    user = User(id=10, email="refusal@test.com", display_name="Refusal User", currency="INR")
    db.add(user)
    db.commit()

    # Test refusal output
    out = await run_agent("What stock should I buy?", db, user_id=10)
    assert "not a licensed" in out["reply"].lower()
    assert len(out["tool_calls"]) == 0

    # Test legitimate query output
    out_legit = await run_agent("What are my subscriptions?", db, user_id=10)
    assert len(out_legit["reply"]) > 10
    assert len(out_legit["tool_calls"]) >= 1


def test_chat_router_endpoints(client, db):
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, email="test@example.com", display_name="Test User", currency="INR")
        db.add(user)
        db.commit()

    # 1. Send message
    res = client.post("/api/chat", json={"message": "What subscriptions do I have?", "user_id": 1})
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert data["message_id"] is not None

    # 2. Get history
    res_hist = client.get("/api/chat/history?user_id=1")
    assert res_hist.status_code == 200
    history = res_hist.json()
    assert len(history) >= 2  # user + assistant

    # 3. Clear history
    res_clear = client.delete("/api/chat/history?user_id=1")
    assert res_clear.status_code == 200
    assert res_clear.json()["status"] == "ok"
