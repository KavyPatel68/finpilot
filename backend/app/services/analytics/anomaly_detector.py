import re
from datetime import date, timedelta
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.transaction import Transaction, TransactionDirection
from app.models.insight import Insight, InsightSeverity
from app.utils.amount import format_amount


def _clean_merchant_for_dup(raw: str, norm: str | None) -> str:
    target = norm or raw
    target = re.sub(r"REF#[A-Z0-9]+", "", target, flags=re.IGNORECASE)
    target = re.sub(r"^(UPI|NEFT|IMPS|POS)[\/\-\s]+", "", target, flags=re.IGNORECASE)
    return target.strip().lower()


def detect_anomalies(
    db: Session,
    user_id: int = 1,
    target_month: str | None = None,  # e.g. "2024-06"
) -> List[Insight]:
    """Detects duplicate charges, category spending spikes, and large outlier transactions.

    Flags matching transactions with is_anomaly=True and generates Insight records.
    """
    created_insights: List[Insight] = []

    # ── 1. Duplicate Charge Detection ───────────────────────────────────────
    # Look for identical amounts on the same account within a 2-day window
    all_expenses = (
        db.scalars(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.direction == TransactionDirection.expense,
                Transaction.is_transfer.is_(False),
            )
            .order_by(Transaction.date.asc(), Transaction.id.asc())
        )
        .all()
    )

    seen_pairs = set()
    for i in range(len(all_expenses)):
        t1 = all_expenses[i]
        for j in range(i + 1, len(all_expenses)):
            t2 = all_expenses[j]

            # Stop scanning if outside the 2-day window
            if (t2.date - t1.date).days > 2:
                break

            if t1.account_id == t2.account_id and t1.amount_minor == t2.amount_minor:
                m1 = _clean_merchant_for_dup(t1.raw_description, t1.merchant_normalized)
                m2 = _clean_merchant_for_dup(t2.raw_description, t2.merchant_normalized)

                # Check if descriptions or cleaned merchants match
                if m1 in m2 or m2 in m1 or t1.category == t2.category:
                    pair_key = tuple(sorted([t1.id, t2.id]))
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        t1.is_anomaly = True
                        t2.is_anomaly = True

                        month_key = t1.date.strftime("%Y-%m")
                        merchant_display = (
                            t1.merchant_normalized
                            or t1.raw_description.split()[0]
                            or "Merchant"
                        )
                        amt_str = format_amount(t1.amount_minor)

                        insight = Insight(
                            user_id=user_id,
                            month=month_key,
                            type="duplicate_charge",
                            severity=InsightSeverity.warning,
                            text=(
                                f"Possible duplicate charge: {merchant_display} charged {amt_str} "
                                f"twice within 48 hours (on {t1.date.strftime('%b %d')} and {t2.date.strftime('%b %d')})."
                            ),
                            supporting_data={
                                "transaction_ids": [t1.id, t2.id],
                                "amount_minor": t1.amount_minor,
                                "merchant": merchant_display,
                                "dates": [str(t1.date), str(t2.date)],
                            },
                        )
                        db.add(insight)
                        created_insights.append(insight)

    # ── 2. Category Spending Spikes ────────────────────────────────────────
    # Group spending by (month, category)
    monthly_cat_spend = defaultdict(lambda: defaultdict(int))
    all_months = set()

    for t in all_expenses:
        m = t.date.strftime("%Y-%m")
        all_months.add(m)
        cat = t.category or "Other"
        monthly_cat_spend[m][cat] += t.amount_minor

    sorted_months = sorted(list(all_months))

    for idx, m in enumerate(sorted_months):
        if idx < 1:
            continue  # Need at least 1 prior month for baseline

        prior_months = sorted_months[max(0, idx - 4) : idx]

        for cat, current_spend in monthly_cat_spend[m].items():
            if cat in ["Income", "Transfers"]:
                continue

            prior_spends = [
                monthly_cat_spend[pm].get(cat, 0) for pm in prior_months
            ]
            avg_prior = (
                sum(prior_spends) / len(prior_spends) if prior_spends else 0
            )

            # Spike condition: > 2x baseline and absolute difference >= ₹5,000 (500,000 minor)
            if avg_prior > 0 and current_spend >= (avg_prior * 2.0) and (current_spend - avg_prior) >= 500000:
                mult = round(current_spend / avg_prior, 1)
                curr_str = format_amount(current_spend)
                avg_str = format_amount(int(avg_prior))

                insight = Insight(
                    user_id=user_id,
                    month=m,
                    type="spending_spike",
                    severity=InsightSeverity.warning,
                    text=(
                        f"Spending spike in {cat}: You spent {curr_str} in {m}, which is {mult}x "
                        f"your typical average ({avg_str}/month)."
                    ),
                    supporting_data={
                        "category": cat,
                        "current_spend_minor": current_spend,
                        "average_spend_minor": int(avg_prior),
                        "multiplier": mult,
                    },
                )
                db.add(insight)
                created_insights.append(insight)

    db.commit()
    return created_insights
