import pytest
import json
from datetime import date
from app.models.account import Account, AccountType
from app.models.user import User
from app.models.transaction import Transaction, TransactionDirection, CategorySource
from app.services.categorization.rule_engine import match_rule, add_user_rule
from app.services.categorization.llm_categorizer import categorize_batch_with_llm
from app.services.categorization.categorizer import categorize_transactions
from app.services.llm_provider import BaseLLMProvider, LLMResponse, LLMMessage


class MockFastLLMProvider(BaseLLMProvider):
    async def complete(self, messages, model=None, system=None, max_tokens=1024):
        # Return valid JSON for LLM categorizer
        canned = [
            {
                "id": 101,
                "category": "Dining",
                "subcategory": "Coffee",
                "confidence": 0.9,
                "merchant_clean": "Blue Tokai",
            }
        ]
        return LLMResponse(
            content=json.dumps(canned),
            model="mock-fast-model",
            usage={"input": 50, "output": 50},
        )

    async def complete_with_tools(self, messages, tools, model=None, system=None, max_tokens=4096):
        return LLMResponse(content="[]", model="mock-model", usage={"input": 0, "output": 0})


def test_rule_engine_default_matches():
    # Test built-in keyword rules
    match_netflix = match_rule("Netflix Subscription")
    assert match_netflix is not None
    assert match_netflix[0] == "Subscriptions"

    match_swiggy = match_rule("UPI/DR/123/Swiggy Order")
    assert match_swiggy is not None
    assert match_swiggy[0] == "Dining"

    match_salary = match_rule("NEFT CR-SALARY CREDIT")
    assert match_salary is not None
    assert match_salary[0] == "Income"


def test_user_rule_precedence_and_creation():
    user_id = 99
    # Add a custom rule for an unknown merchant
    add_user_rule(user_id=user_id, keyword="Garg Enterprises", category="Utilities")

    # Match against user rule
    match = match_rule("NEFT-GARG ENTERPRISES-PAYMENT", user_id=user_id)
    assert match is not None
    assert match[0] == "Utilities"


@pytest.mark.asyncio
async def test_llm_categorizer_batch():
    mock_llm = MockFastLLMProvider()
    items = [{"id": 101, "narration": "Blue Tokai Coffee Roasters", "amount_minor": 35000, "direction": "expense"}]

    results = await categorize_batch_with_llm(items, mock_llm)
    assert 101 in results
    assert results[101].category == "Dining"
    assert results[101].merchant_clean == "Blue Tokai"
    assert results[101].confidence == 0.9


@pytest.mark.asyncio
async def test_unified_categorizer(db):
    user = User(id=2, email="cat@test.com", display_name="Cat User", currency="INR")
    db.add(user)
    acc = Account(id=2, user_id=2, name="Cat Bank", type=AccountType.bank, currency="INR")
    db.add(acc)

    t1 = Transaction(
        id=201,
        user_id=2,
        account_id=2,
        date=date(2024, 6, 1),
        raw_description="Netflix.com",
        amount_minor=64900,
        direction=TransactionDirection.expense,
        category="Other",
    )
    t2 = Transaction(
        id=202,
        user_id=2,
        account_id=2,
        date=date(2024, 6, 2),
        raw_description="XYZ Coffee Cafe",
        amount_minor=25000,
        direction=TransactionDirection.expense,
        category="Other",
    )
    db.add_all([t1, t2])
    db.commit()

    mock_llm = MockFastLLMProvider()
    await categorize_transactions([t1, t2], db, llm_provider=mock_llm, user_id=2)

    # t1 matched rule engine -> Subscriptions
    assert t1.category == "Subscriptions"
    assert t1.category_source == CategorySource.rule
    assert t1.confidence == 1.0


def test_transactions_router_list_and_category_update(client, db):
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

    txn = Transaction(
        user_id=1,
        account_id=1,
        date=date(2024, 5, 10),
        raw_description="Unknown Merchant 123",
        merchant_normalized="Unknown Merchant",
        amount_minor=50000,
        direction=TransactionDirection.expense,
        category="Other",
        category_source=CategorySource.rule,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    # 1. Test listing
    res = client.get("/api/transactions?user_id=1")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(item["id"] == txn.id for item in data["items"])

    # 2. Test user category update
    update_res = client.patch(
        f"/api/transactions/{txn.id}?user_id=1",
        json={"category": "Groceries", "create_rule": True}
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["category"] == "Groceries"
    assert updated_data["category_source"] == "user"
    assert updated_data["confidence"] == 1.0

    # 3. Test that rule was learned
    match = match_rule("Unknown Merchant 123", user_id=1)
    assert match is not None
    assert match[0] == "Groceries"
