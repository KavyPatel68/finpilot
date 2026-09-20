from datetime import date, datetime
from typing import Dict, Any, Optional, List
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.transaction import Transaction, TransactionDirection
from app.models.summary import MonthlySummary
from app.utils.amount import format_amount


def generate_monthly_summary(
    db: Session,
    month_str: str,  # Format: "YYYY-MM"
    user_id: int = 1,
) -> MonthlySummary:
    """Computes deterministic financial aggregations, MoM spending changes,

    top categories, and a structured monthly narrative for the user.
    """
    # 1. Fetch transactions for target month
    start_date = date.fromisoformat(f"{month_str}-01")
    next_month = start_date + relativedelta(months=1)

    txns = (
        db.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.date < next_month,
                Transaction.is_transfer.is_(False),
            )
        )
        .all()
    )

    income_minor = 0
    expense_minor = 0
    recurring_minor = 0

    category_totals: Dict[str, Dict[str, Any]] = {}
    merchant_totals: Dict[str, Dict[str, Any]] = {}

    for t in txns:
        if t.direction == TransactionDirection.income:
            income_minor += t.amount_minor
        else:
            expense_minor += t.amount_minor
            if t.is_recurring:
                recurring_minor += t.amount_minor

            # Category aggregation
            cat = t.category or "Other"
            if cat not in category_totals:
                category_totals[cat] = {"amount_minor": 0, "count": 0}
            category_totals[cat]["amount_minor"] += t.amount_minor
            category_totals[cat]["count"] += 1

            # Merchant aggregation
            merchant = (
                t.merchant_normalized
                or t.raw_description.split("/")[0].strip()
                or "Unknown Merchant"
            )
            if merchant not in merchant_totals:
                merchant_totals[merchant] = {"amount_minor": 0, "count": 0}
            merchant_totals[merchant]["amount_minor"] += t.amount_minor
            merchant_totals[merchant]["count"] += 1

    net_savings_minor = income_minor - expense_minor
    savings_rate_pct = (
        round((net_savings_minor / income_minor) * 100, 1) if income_minor > 0 else 0.0
    )

    # Sort categories and merchants
    sorted_categories = sorted(
        category_totals.items(), key=lambda x: x[1]["amount_minor"], reverse=True
    )
    top_categories = [
        {
            "category": cat,
            "amount_minor": data["amount_minor"],
            "amount_display": format_amount(data["amount_minor"]),
            "transaction_count": data["count"],
            "pct_of_total": (
                round((data["amount_minor"] / expense_minor) * 100, 1)
                if expense_minor > 0
                else 0.0
            ),
        }
        for cat, data in sorted_categories[:8]
    ]

    sorted_merchants = sorted(
        merchant_totals.items(), key=lambda x: x[1]["amount_minor"], reverse=True
    )
    top_merchants = [
        {
            "merchant": merch,
            "amount_minor": data["amount_minor"],
            "amount_display": format_amount(data["amount_minor"]),
            "transaction_count": data["count"],
        }
        for merch, data in sorted_merchants[:8]
    ]

    # Calculate own-account transfers (excluded from total outflow)
    transfers_txns = (
        db.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.date < next_month,
                (Transaction.is_transfer.is_(True)) | (Transaction.category == "Transfers"),
                Transaction.direction == TransactionDirection.expense,
            )
        )
        .all()
    )
    transfers_minor = sum(t.amount_minor for t in transfers_txns)

    # 2. Check partial month & MoM spending comparison
    days_in_month = (next_month - relativedelta(days=1)).day
    latest_user_date = db.scalar(
        select(func.max(Transaction.date)).where(Transaction.user_id == user_id)
    )
    is_partial_month = False
    partial_days = None
    if latest_user_date and latest_user_date.year == start_date.year and latest_user_date.month == start_date.month:
        if latest_user_date.day < days_in_month:
            is_partial_month = True
            partial_days = latest_user_date.day

    prev_month_date = start_date - relativedelta(months=1)
    if is_partial_month and partial_days:
        cutoff_date = prev_month_date + relativedelta(days=partial_days - 1)
        prev_txns = (
            db.scalars(
                select(Transaction).where(
                    Transaction.user_id == user_id,
                    Transaction.date >= prev_month_date,
                    Transaction.date <= cutoff_date,
                    Transaction.direction == TransactionDirection.expense,
                    Transaction.is_transfer.is_(False),
                )
            )
            .all()
        )
    else:
        prev_txns = (
            db.scalars(
                select(Transaction).where(
                    Transaction.user_id == user_id,
                    Transaction.date >= prev_month_date,
                    Transaction.date < start_date,
                    Transaction.direction == TransactionDirection.expense,
                    Transaction.is_transfer.is_(False),
                )
            )
            .all()
        )
    prev_expense_minor = sum(t.amount_minor for t in prev_txns)
    mom_change_pct = None
    if prev_expense_minor > 0:
        mom_change_pct = round(
            ((expense_minor - prev_expense_minor) / prev_expense_minor) * 100, 1
        )

    # 3. Generate structured narrative
    month_name = start_date.strftime("%B %Y")
    top_cat_text = (
        f"{top_categories[0]['category']} ({top_categories[0]['amount_display']})"
        if top_categories
        else "N/A"
    )

    mom_text = ""
    if mom_change_pct is not None:
        direction_word = "higher" if mom_change_pct > 0 else "lower"
        comparison_label = "vs same days last month" if is_partial_month else "than the previous month"
        mom_text = f" Spending was {abs(mom_change_pct)}% {direction_word} {comparison_label}."

    narrative = (
        f"In {month_name}, you had a total income of {format_amount(income_minor)} and expenses of "
        f"{format_amount(expense_minor)}, resulting in net savings of {format_amount(net_savings_minor)} "
        f"({savings_rate_pct}% savings rate). Your highest spending category was {top_cat_text}.{mom_text}"
    )

    payload = {
        "month": month_str,
        "income_minor": income_minor,
        "expense_minor": expense_minor,
        "net_savings_minor": net_savings_minor,
        "savings_rate_pct": savings_rate_pct,
        "recurring_spend_minor": recurring_minor,
        "transfers_minor": transfers_minor,
        "transfers_display": format_amount(transfers_minor),
        "is_partial_month": is_partial_month,
        "partial_days": partial_days,
        "top_categories": top_categories,
        "top_merchants": top_merchants,
        "mom_change_pct": mom_change_pct,
        "previous_expense_minor": prev_expense_minor,
    }

    # 4. Upsert MonthlySummary record
    summary = db.scalar(
        select(MonthlySummary).where(
            MonthlySummary.user_id == user_id,
            MonthlySummary.month == month_str,
        )
    )

    if not summary:
        summary = MonthlySummary(
            user_id=user_id,
            month=month_str,
            payload=payload,
            generated_text=narrative,
        )
        db.add(summary)
    else:
        summary.payload = payload
        summary.generated_text = narrative

    db.commit()
    db.refresh(summary)
    return summary
