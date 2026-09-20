import io
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionDirection
from app.models.budget import Budget
from app.models.goal import Goal, GoalType
from app.services.agent.intent_router import match_intent, route_and_execute_intent
from app.services.cache_service import (
    get_user_data_version,
    compute_cache_key,
    get_cached_response,
    store_cached_response,
    invalidate_user_qa_cache,
    calculate_cost,
    log_ai_usage,
)
from app.services.agent.orchestrator import run_agent
from app.services.llm_provider import FakeLLMProvider


@pytest.fixture
def token_test_db(db: Session):
    user = db.get(User, 88)
    if user and db.query(Transaction).filter_by(user_id=88).first():
        return user

    if not user:
        user = User(id=88, email="token_test@example.com", display_name="Token User", currency="INR")
        db.add(user)

    acc = db.get(Account, 88)
    if not acc:
        acc = Account(id=88, user_id=88, name="Test Bank", type=AccountType.bank, currency="INR")
        db.add(acc)

    # Add transactions
    txns = [
        Transaction(
            user_id=88,
            account_id=88,
            date=date(2024, 8, 1),
            raw_description="SALARY CREDIT",
            amount_minor=8500000,
            direction=TransactionDirection.income,
            category="Income",
        ),
        Transaction(
            user_id=88,
            account_id=88,
            date=date(2024, 8, 5),
            raw_description="SWIGGY BANGALORE",
            amount_minor=65000,
            direction=TransactionDirection.expense,
            category="Dining",
        ),
        Transaction(
            user_id=88,
            account_id=88,
            date=date(2024, 8, 10),
            raw_description="AMAZON SHOPPING",
            amount_minor=250000,
            direction=TransactionDirection.expense,
            category="Shopping",
        ),
    ]
    for t in txns:
        db.add(t)

    b = Budget(user_id=88, category="Dining", monthly_limit_minor=100000, effective_from=date(2024, 8, 1))
    db.add(b)
    db.commit()
    return user


def test_intent_router_20_phrasings(token_test_db, db: Session):
    """Verifies intent router on 20 distinct phrasings:

    14 high-confidence (>= 0.8) domain questions, and 6 ambiguous/out-of-scope
    queries that properly fall through (< 0.8).
    """
    high_confidence_queries = [
        # Total spending / cash flow
        ("how much did i spend in 2024-08", "total_spending"),
        ("what were my total expenses", "total_spending"),
        ("show my monthly summary for 2024-08", "total_spending"),
        # Top categories
        ("what are my top spending categories", "top_categories"),
        ("where did all my money go", "top_categories"),
        # Subscriptions
        ("what subscriptions do i have", "subscriptions"),
        ("show my active recurring bills", "subscriptions"),
        # Budget status
        ("how much budget is left", "budget_status"),
        ("am i over budget this month", "budget_status"),
        # Anomalies
        ("were there any duplicate charges", "anomalies"),
        ("did any spending spike recently", "anomalies"),
        # Goals
        ("how is my emergency fund progress", "goals"),
        ("am i on track for my savings goals", "goals"),
        # Category specific
        ("how much did i spend on dining", "category_spend"),
    ]

    for query, expected_intent in high_confidence_queries:
        intent, conf, _ = match_intent(query)
        assert intent == expected_intent, f"Query '{query}' expected {expected_intent}, got {intent}"
        assert conf >= 0.80, f"Query '{query}' expected conf >= 0.80, got {conf}"

        # Test execution produces zero-token deterministic reply
        route_res = route_and_execute_intent(query, db, user_id=88)
        assert route_res.matched is True
        assert len(route_res.reply) > 10

    ambiguous_queries = [
        "hello there",
        "can you help me with something",
        "why",
        "what is the weather like in Mumbai",
        "tell me about history",
        "help",
    ]

    for query in ambiguous_queries:
        intent, conf, _ = match_intent(query)
        assert conf < 0.80, f"Query '{query}' expected conf < 0.80, got {conf}"
        route_res = route_and_execute_intent(query, db, user_id=88)
        assert route_res.matched is False, f"Query '{query}' should not match intent with high confidence"


def test_data_version_and_qa_cache_invalidation(token_test_db, db: Session):
    user_id = 88
    # 1. Initial version
    v1 = get_user_data_version(db, user_id)
    assert len(v1) == 16

    # 2. Store item in cache
    key = compute_cache_key("qa", "custom deep question", user_id=user_id, data_version=v1)
    store_cached_response(
        db=db,
        key_hash=key,
        user_id=user_id,
        task_type="qa",
        prompt_str="custom deep question",
        response_json={"reply": "Cached financial answer"},
        estimated_tokens_saved=300,
    )

    cached_item = get_cached_response(db, key)
    assert cached_item is not None
    assert cached_item["reply"] == "Cached financial answer"

    # 3. Insert transaction -> version changes
    new_t = Transaction(
        user_id=user_id,
        account_id=user_id,
        date=date(2024, 8, 20),
        raw_description="NEW EXPENSE",
        amount_minor=10000,
        direction=TransactionDirection.expense,
        category="Other",
    )
    db.add(new_t)
    db.commit()

    v2 = get_user_data_version(db, user_id)
    assert v1 != v2, "Data version must change after transaction insert"

    # 4. Invalidation clears user Q&A cache
    del_count = invalidate_user_qa_cache(db, user_id=user_id)
    assert del_count >= 1
    assert get_cached_response(db, key) is None


def test_cost_calculation_and_token_meter(token_test_db, client: TestClient, db: Session):
    # Model pricing calculation
    cost_usd, cost_inr = calculate_cost(
        model="claude-haiku-4-5-20251001",
        input_tokens=10000,
        output_tokens=2000,
        cached_read_tokens=5000,
    )
    assert cost_usd > 0.0
    assert cost_inr > 0.0
    # In config, USD_TO_INR is 84.0
    assert cost_inr == round(cost_usd * 84.0, 4)

    # Log usage
    log_ai_usage(
        db=db,
        user_id=88,
        task_type="qa",
        model="claude-haiku-4-5-20251001",
        input_tokens=150,
        output_tokens=75,
        tokens_saved=100,
        is_cache_hit=False,
    )

    # Verify AI usage API
    res = client.get("/api/ai/usage?user_id=88")
    assert res.status_code == 200
    data = res.json()
    assert data["is_estimated"] is True
    assert data["tokens_used_today"] >= 225
    assert data["tokens_saved_by_cache"] >= 100
    assert data["llm_mode"] in ["off", "cheap", "full"]

    # Test mode change endpoint
    res_mode = client.post("/api/ai/mode", json={"mode": "cheap"})
    assert res_mode.status_code == 200
    assert res_mode.json()["llm_mode"] == "cheap"


@pytest.mark.asyncio
async def test_full_flow_with_llm_mode_off_and_no_api_key(client: TestClient, db: Session):
    """Verifies that with LLM_MODE=off and no API key, the full workflow runs without errors:

    upload -> categorization -> intent router -> chat -> reports -> PDF.
    """
    settings.LLM_MODE = "off"
    settings.ANTHROPIC_API_KEY = ""

    user_id = 89
    user = User(id=user_id, email="off_mode@test.com", display_name="Off User", currency="INR")
    db.add(user)
    acc = Account(id=user_id, user_id=user_id, name="Cash", type=AccountType.bank, currency="INR")
    db.add(acc)
    db.commit()

    # 1. Upload statement
    csv = "Date,Narration,Amount,Type\n2024-08-01,SALARY CREDIT,50000,Credit\n2024-08-02,SWIGGY,500,Debit\n"
    res_up = client.post(
        "/api/upload",
        data={"user_id": user_id, "account_id": user_id},
        files={"file": ("stmt.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert res_up.status_code == 200
    assert res_up.json()["imported_count"] == 2

    # 2. Chat with intent router in offline mode
    res_chat = client.post(
        f"/api/chat?user_id={user_id}",
        json={"message": "how much did i spend in 2024-08", "user_id": user_id},
    )
    assert res_chat.status_code == 200
    assert "Financial Summary" in res_chat.json()["reply"]

    # 3. Unmatched query in offline mode produces polite guidance without crash
    res_unmatched = client.post(
        f"/api/chat?user_id={user_id}",
        json={"message": "explain quantum physics", "user_id": user_id},
    )
    assert res_unmatched.status_code == 200
    assert "offline mode" in res_unmatched.json()["reply"].lower()

    # 4. Monthly report and PDF in offline mode
    res_rep = client.get(f"/api/reports/2024-08?user_id={user_id}")
    assert res_rep.status_code == 200

    res_pdf = client.get(f"/api/reports/2024-08/pdf?user_id={user_id}")
    assert res_pdf.status_code == 200
    assert res_pdf.content.startswith(b"%PDF-")

    # Reset mode
    settings.LLM_MODE = "cheap"
