import re
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.transaction import Transaction, TransactionDirection
from app.models.recurring import (
    RecurringGroup,
    RecurringFrequency,
    RecurringStatus,
    RecurringType,
)


def _normalize_recurring_merchant(raw_description: str, merchant_normalized: Optional[str]) -> str:
    """Extracts a clean merchant identifier suitable for grouping recurring charges."""
    if merchant_normalized and len(merchant_normalized) >= 2:
        name = merchant_normalized.strip()
    else:
        name = raw_description.strip()

    # Remove payment rails, transaction refs, and trailing numbers
    name = re.sub(r"^(UPI|NEFT|IMPS|POS|ACH|NACH|ATM|REF)[\/\-\s]+[A-Z0-9\/\-]+[\/\-\s]*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"REF#[A-Z0-9]+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(CR|DR|PAYMENT|TRANSFER)\b", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[0-9]{5,}", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title() or "Unknown Merchant"


def _detect_frequency(intervals: List[int]) -> Optional[Tuple[RecurringFrequency, int]]:
    """Detects recurring interval pattern from a list of day intervals.

    Returns (RecurringFrequency, interval_days) or None.
    """
    if not intervals:
        return None

    median_interval = sorted(intervals)[len(intervals) // 2]

    if 5 <= median_interval <= 10:
        return RecurringFrequency.weekly, 7
    elif 24 <= median_interval <= 35:
        return RecurringFrequency.monthly, 30
    elif 75 <= median_interval <= 105:
        return RecurringFrequency.quarterly, 90
    elif 340 <= median_interval <= 390:
        return RecurringFrequency.yearly, 365

    return None


def _classify_recurring_type(merchant: str, category: Optional[str]) -> RecurringType:
    merch_low = merchant.lower()
    cat_low = (category or "").lower()

    if "emi" in merch_low or "loan" in merch_low or "emi" in cat_low:
        return RecurringType.emi
    if "subscription" in cat_low or any(
        s in merch_low for s in ["netflix", "spotify", "prime", "hotstar", "youtube", "patreon"]
    ):
        return RecurringType.subscription
    if any(b in cat_low for b in ["utilities", "housing", "rent", "insurance"]):
        return RecurringType.bill
    return RecurringType.other


def detect_recurring_groups(
    db: Session,
    user_id: int = 1,
) -> Tuple[List[RecurringGroup], List[Dict[str, Any]]]:
    """Scans all expense transactions for recurring subscriptions, bills, and EMIs.

    Also identifies price hikes and links transactions to recurring groups.
    Returns (created_or_updated_groups, price_hike_insights).
    """
    txns = (
        db.scalars(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.direction == TransactionDirection.expense,
                Transaction.is_transfer.is_(False),
            )
            .order_by(Transaction.date.asc())
        )
        .all()
    )

    if not txns:
        return [], []

    latest_dataset_date = max(t.date for t in txns)

    # Group transactions by cleaned merchant
    merchant_map: Dict[str, List[Transaction]] = {}
    for t in txns:
        key = _normalize_recurring_merchant(t.raw_description, t.merchant_normalized)
        if key not in merchant_map:
            merchant_map[key] = []
        merchant_map[key].append(t)

    result_groups: List[RecurringGroup] = []
    price_hike_insights: List[Dict[str, Any]] = []

    for merchant_name, m_txns in merchant_map.items():
        if len(m_txns) < 2:
            continue

        # Sort chronologically
        m_txns.sort(key=lambda x: x.date)

        # Calculate intervals
        intervals = []
        for i in range(1, len(m_txns)):
            diff = (m_txns[i].date - m_txns[i - 1].date).days
            if diff > 0:
                intervals.append(diff)

        freq_match = _detect_frequency(intervals)
        if not freq_match:
            continue

        frequency, interval_days = freq_match
        last_txn = m_txns[-1]
        last_seen = last_txn.date

        # Check for price hike: compare recent amount with baseline
        amounts = [t.amount_minor for t in m_txns]
        avg_amount = sum(amounts) // len(amounts)
        latest_amount = amounts[-1]

        # Price hike check: if earlier transactions had a consistent lower price
        # and latest transaction(s) jumped up
        earlier_amounts = amounts[:-1]
        earlier_avg = sum(earlier_amounts) // len(earlier_amounts)
        if latest_amount > earlier_avg and (latest_amount - earlier_avg) >= 5000:  # >= ₹50 jump
            price_hike_insights.append(
                {
                    "merchant": merchant_name,
                    "previous_amount_minor": earlier_avg,
                    "new_amount_minor": latest_amount,
                    "effective_date": last_seen,
                    "difference_minor": latest_amount - earlier_avg,
                }
            )

        # Status
        days_since_last = (latest_dataset_date - last_seen).days
        if days_since_last > (interval_days * 1.8):
            status = RecurringStatus.possibly_cancelled
        else:
            status = RecurringStatus.active

        rec_type = _classify_recurring_type(merchant_name, last_txn.category)
        next_expected = last_seen + timedelta(days=interval_days)

        # Check if group already exists in DB
        group = db.scalar(
            select(RecurringGroup).where(
                RecurringGroup.user_id == user_id,
                RecurringGroup.merchant == merchant_name,
            )
        )

        if not group:
            group = RecurringGroup(
                user_id=user_id,
                merchant=merchant_name,
                avg_amount_minor=latest_amount,
                frequency=frequency,
                next_expected_date=next_expected,
                last_seen=last_seen,
                status=status,
                type=rec_type,
            )
            db.add(group)
            db.flush()
        else:
            group.avg_amount_minor = latest_amount
            group.frequency = frequency
            group.next_expected_date = next_expected
            group.last_seen = last_seen
            if group.status != RecurringStatus.cancelled:
                group.status = status
            group.type = rec_type

        # Link all member transactions to this group
        for t in m_txns:
            t.is_recurring = True
            t.recurring_group_id = group.id

        result_groups.append(group)

    db.commit()
    return result_groups, price_hike_insights
