import pytest
from datetime import date
from app.models.account import Account, AccountType
from app.models.user import User
from app.models.transaction import Transaction, TransactionDirection
from app.models.recurring import RecurringStatus, RecurringFrequency
from app.services.analytics.recurring_detector import detect_recurring_groups


def test_recurring_interval_and_price_hike_detection(db):
    user = User(id=3, email="rec@test.com", display_name="Recurring User", currency="INR")
    db.add(user)
    acc = Account(id=3, user_id=3, name="Bank", type=AccountType.bank, currency="INR")
    db.add(acc)

    # Add 4 monthly Netflix transactions with a price hike in month 4
    dates = [
        date(2024, 4, 10),
        date(2024, 5, 10),
        date(2024, 6, 10),
        date(2024, 7, 10),
    ]
    amounts = [64900, 64900, 64900, 79900]  # ₹649 -> ₹799

    for d, amt in zip(dates, amounts):
        t = Transaction(
            user_id=3,
            account_id=3,
            date=d,
            raw_description="Netflix Subscription",
            amount_minor=amt,
            direction=TransactionDirection.expense,
            category="Subscriptions",
        )
        db.add(t)
    db.commit()

    groups, price_hikes = detect_recurring_groups(db, user_id=3)

    assert len(groups) >= 1
    netflix_grp = next((g for g in groups if "Netflix" in g.merchant), None)
    assert netflix_grp is not None
    assert netflix_grp.frequency == RecurringFrequency.monthly
    assert netflix_grp.avg_amount_minor == 79900
    assert netflix_grp.status == RecurringStatus.active

    # Price hike detected
    assert len(price_hikes) >= 1
    assert price_hikes[0]["merchant"] == "Netflix Subscription"
    assert price_hikes[0]["new_amount_minor"] == 79900


def test_subscriptions_router(client, db):
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, email="test@example.com", display_name="Test User", currency="INR")
        db.add(user)
        db.commit()

    # Get subscriptions
    res = client.get("/api/subscriptions?user_id=1")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

    if data:
        sub_id = data[0]["id"]
        # Update status to cancelled
        patch_res = client.patch(f"/api/subscriptions/{sub_id}/status?status=cancelled&user_id=1")
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "cancelled"
