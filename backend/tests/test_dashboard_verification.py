import os
import pytest
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionDirection
from app.services.ingestion.parser_csv import parse_file
from app.services.ingestion.deduplicator import deduplicate
from app.services.categorization.categorizer import categorize_transactions
from app.services.analytics.monthly_summary import generate_monthly_summary

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "finpilot_test_statement_hdfc_style.csv")

@pytest.mark.asyncio
async def test_dashboard_verification_numbers(db):
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

    # Parse and insert transactions
    parse_result = parse_file(FIXTURE_PATH)
    dedup = deduplicate(parse_result.transactions, db, 1, 1)

    txns = []
    for p in dedup.to_insert:
        t = Transaction(
            user_id=1,
            account_id=1,
            date=p.date,
            amount_minor=p.amount_minor,
            direction=TransactionDirection[p.direction],
            raw_description=p.raw_description,
            merchant_normalized=p.merchant_hint,
            balance_minor=p.balance_minor,
            is_transfer=False,
        )
        db.add(t)
        txns.append(t)
    db.commit()

    await categorize_transactions(txns, db, user_id=1)
    db.commit()

    # Generate summary for September 2026
    summary = generate_monthly_summary(db, "2026-09", user_id=1)
    payload = summary.payload

    # 1. Money out: 46,184
    assert payload["expense_minor"] == 4618400

    # 2. Left over: 28,816
    assert payload["net_savings_minor"] == 2881600

    # 3. Savings rate: 38.4%
    assert payload["savings_rate_pct"] == 38.4

    # 4. Transfers: 10,000 shown as excluded
    assert payload["transfers_minor"] == 1000000

    # 5. Category breakdown checks:
    # Housing: 18,000
    # Utilities: 2,259 (Torrent Power 1,910 + Jio 349)
    categories = {c["category"]: c["amount_minor"] for c in payload["top_categories"]}

    housing_key = "Housing/Rent" if "Housing/Rent" in categories else "Housing"
    assert categories.get(housing_key) == 1800000
    assert categories.get("Utilities") == 225900

    # 6. Verify "Transfers" is NOT in top_categories
    assert "Transfers" not in categories

    # 7. Partial month verification
    assert payload["is_partial_month"] is True
    assert payload["partial_days"] == 18
