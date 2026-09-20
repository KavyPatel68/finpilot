import math
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.transaction import Transaction, TransactionDirection
from app.models.budget import Budget
from app.models.goal import Goal
from app.models.recurring import RecurringGroup
from app.models.insight import Insight
from app.models.account import Account
from app.services.analytics.monthly_summary import generate_monthly_summary
from app.services.analytics.anomaly_detector import detect_anomalies
from app.utils.amount import format_amount
from app.schemas.report import (
    MonthlyReportResponse,
    ReportCashFlow,
    ReportCategorySpend,
    ReportMerchantSpend,
    ReportBudgetStatus,
    ReportGoalStatus,
    ReportRecurringItem,
    ReportAnomalyItem,
    ReportActionItem,
)

DISCLAIMER_TEXT = (
    "FinPilot is a personal finance analytics tool and is NOT a registered financial, "
    "investment, or legal advisor. All insights, projections, and checklists are informational "
    "heuristics derived from your uploaded statements. FinPilot never recommends specific securities, "
    "stocks, crypto, loans, or financial products. Consult a qualified professional for financial planning decisions."
)


def generate_monthly_report(
    db: Session,
    month_str: str,  # "YYYY-MM"
    user_id: int = 1,
) -> MonthlyReportResponse:
    """Aggregates an executive monthly financial report including cash flow, spending breakdown,

    budget adherence, savings goals velocity, subscriptions, anomalies, and actionable next-steps.
    """
    # 1. Fetch currency from user's primary account or default INR
    user_acc = db.scalar(
        select(Account).where(Account.user_id == user_id).order_by(Account.id.asc())
    )
    currency = user_acc.currency if user_acc and user_acc.currency else "INR"

    # 2. Monthly Summary aggregation
    summary_obj = generate_monthly_summary(db, month_str=month_str, user_id=user_id)
    payload = summary_obj.payload or {}

    start_date = date.fromisoformat(f"{month_str}-01")
    month_name = start_date.strftime("%B %Y")
    next_month_date = start_date + relativedelta(months=1)

    income_minor = payload.get("income_minor", 0)
    expense_minor = payload.get("expense_minor", 0)
    net_savings_minor = payload.get("net_savings_minor", 0)
    savings_rate_pct = payload.get("savings_rate_pct", 0.0)
    mom_change_pct = payload.get("mom_change_pct")
    recurring_spend_minor = payload.get("recurring_spend_minor", 0)

    cash_flow = ReportCashFlow(
        income_minor=income_minor,
        income_display=format_amount(income_minor, currency),
        expense_minor=expense_minor,
        expense_display=format_amount(expense_minor, currency),
        net_savings_minor=net_savings_minor,
        net_savings_display=format_amount(net_savings_minor, currency),
        savings_rate_pct=savings_rate_pct,
        mom_change_pct=mom_change_pct,
        recurring_spend_minor=recurring_spend_minor,
        recurring_spend_display=format_amount(recurring_spend_minor, currency),
    )

    # 3. Top categories & merchants
    top_categories = [
        ReportCategorySpend(
            category=cat["category"],
            amount_minor=cat["amount_minor"],
            amount_display=cat["amount_display"],
            pct_of_total=cat["pct_of_total"],
            transaction_count=cat["transaction_count"],
        )
        for cat in payload.get("top_categories", [])
    ]

    top_merchants = [
        ReportMerchantSpend(
            merchant=m["merchant"],
            amount_minor=m["amount_minor"],
            amount_display=m["amount_display"],
            transaction_count=m["transaction_count"],
        )
        for m in payload.get("top_merchants", [])
    ]

    # 4. Budgets evaluation for target month
    budgets = (
        db.scalars(
            select(Budget)
            .where(Budget.user_id == user_id)
            .order_by(Budget.monthly_limit_minor.desc())
        )
        .all()
    )

    spend_query = (
        select(Transaction.category, func.sum(Transaction.amount_minor))
        .where(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date < next_month_date,
            Transaction.direction == TransactionDirection.expense,
            Transaction.is_transfer.is_(False),
        )
        .group_by(Transaction.category)
    )
    spend_by_cat = dict(db.execute(spend_query).all())

    budget_statuses: List[ReportBudgetStatus] = []
    for b in budgets:
        spent = spend_by_cat.get(b.category, 0)
        remaining = max(0, b.monthly_limit_minor - spent)
        spent_pct = (
            round((spent / b.monthly_limit_minor) * 100, 1)
            if b.monthly_limit_minor > 0
            else 0.0
        )
        if spent > b.monthly_limit_minor:
            status = "exceeded"
        elif spent_pct >= 80.0:
            status = "warning"
        else:
            status = "on_track"

        budget_statuses.append(
            ReportBudgetStatus(
                category=b.category,
                monthly_limit_minor=b.monthly_limit_minor,
                monthly_limit_display=format_amount(b.monthly_limit_minor, currency),
                spent_minor=spent,
                spent_display=format_amount(spent, currency),
                remaining_minor=remaining,
                remaining_display=format_amount(remaining, currency),
                spent_pct=spent_pct,
                status=status,
            )
        )

    # 5. Goals tracking
    today = date.today()
    goals = (
        db.scalars(
            select(Goal)
            .where(Goal.user_id == user_id, Goal.is_active.is_(True))
            .order_by(Goal.id.asc())
        )
        .all()
    )

    goal_statuses: List[ReportGoalStatus] = []
    for g in goals:
        prog_pct = (
            round((g.current_amount_minor / g.target_amount_minor) * 100, 1)
            if g.target_amount_minor > 0
            else 0.0
        )
        prog_pct = min(100.0, max(0.0, prog_pct))

        months_rem = None
        req_monthly = None
        on_track = None

        if g.target_date:
            rem_to_save = max(0, g.target_amount_minor - g.current_amount_minor)
            if g.target_date > today:
                months_rem = max(
                    1,
                    (g.target_date.year - today.year) * 12
                    + (g.target_date.month - today.month),
                )
                req_monthly = math.ceil(rem_to_save / months_rem)
                if g.monthly_contribution_planned_minor is not None:
                    on_track = g.monthly_contribution_planned_minor >= req_monthly
            else:
                months_rem = 0
                req_monthly = rem_to_save
                on_track = rem_to_save == 0

        goal_statuses.append(
            ReportGoalStatus(
                id=g.id,
                name=g.name,
                type=g.type.value if hasattr(g.type, "value") else str(g.type),
                target_amount_minor=g.target_amount_minor,
                target_amount_display=format_amount(g.target_amount_minor, currency),
                current_amount_minor=g.current_amount_minor,
                current_amount_display=format_amount(g.current_amount_minor, currency),
                progress_pct=prog_pct,
                target_date=str(g.target_date) if g.target_date else None,
                months_remaining=months_rem,
                required_monthly_savings_minor=req_monthly,
                required_monthly_savings_display=(
                    format_amount(req_monthly, currency) if req_monthly is not None else None
                ),
                on_track=on_track,
            )
        )

    # 6. Recurring Subscriptions
    recurrings = (
        db.scalars(
            select(RecurringGroup)
            .where(RecurringGroup.user_id == user_id)
            .order_by(RecurringGroup.avg_amount_minor.desc())
        )
        .all()
    )

    recurring_items = [
        ReportRecurringItem(
            id=r.id,
            merchant=r.merchant,
            avg_amount_minor=r.avg_amount_minor,
            avg_amount_display=format_amount(r.avg_amount_minor, currency),
            frequency=r.frequency.value if hasattr(r.frequency, "value") else str(r.frequency),
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
            type=r.type.value if hasattr(r.type, "value") else str(r.type),
        )
        for r in recurrings
    ]

    # 7. Anomalies for the target month
    anomalies = (
        db.scalars(
            select(Insight).where(
                Insight.user_id == user_id,
                Insight.month == month_str,
            )
        )
        .all()
    )

    if not anomalies:
        # Run anomaly detection to ensure all historical months are evaluated
        detect_anomalies(db, user_id=user_id)
        anomalies = (
            db.scalars(
                select(Insight).where(
                    Insight.user_id == user_id,
                    Insight.month == month_str,
                )
            )
            .all()
        )

    anomaly_items = [
        ReportAnomalyItem(
            id=a.id,
            type=a.type,
            severity=a.severity.value if hasattr(a.severity, "value") else str(a.severity),
            text=a.text,
            supporting_data=a.supporting_data,
        )
        for a in anomalies
    ]

    # 8. Actionable Checklist generation
    action_items: List[ReportActionItem] = []
    action_count = 0

    # Rule A: Flag duplicate charges
    for a in anomalies:
        if a.type == "duplicate_charge":
            sup = a.supporting_data or {}
            amt_minor = sup.get("amount_minor", 0)
            merch = sup.get("merchant", "Merchant")
            action_count += 1
            action_items.append(
                ReportActionItem(
                    id=f"act-{action_count}",
                    category="anomaly",
                    title=f"Review Potential Duplicate Charge ({merch})",
                    description=(
                        f"A duplicate charge of {format_amount(amt_minor, currency)} was detected on {merch}. "
                        "Check your bank statement and dispute the second transaction if debited twice."
                    ),
                    impact_type="high",
                    potential_savings_minor=amt_minor,
                    potential_savings_display=format_amount(amt_minor, currency),
                )
            )

    # Rule B: Over-budget categories
    for b in budget_statuses:
        if b.status == "exceeded":
            over_amt = b.spent_minor - b.monthly_limit_minor
            action_count += 1
            action_items.append(
                ReportActionItem(
                    id=f"act-{action_count}",
                    category="budget",
                    title=f"Rebalance {b.category} Spend",
                    description=(
                        f"You exceeded your {b.category} budget by {format_amount(over_amt, currency)} "
                        f"({b.spent_pct}% spent). Review discretionary items in this category or adjust your limit."
                    ),
                    impact_type="high",
                    potential_savings_minor=over_amt,
                    potential_savings_display=format_amount(over_amt, currency),
                )
            )
        elif b.status == "warning":
            action_count += 1
            action_items.append(
                ReportActionItem(
                    id=f"act-{action_count}",
                    category="budget",
                    title=f"Monitor {b.category} Buffer",
                    description=(
                        f"{b.category} is currently at {b.spent_pct}% of budget with only "
                        f"{b.remaining_display} remaining."
                    ),
                    impact_type="medium",
                )
            )

    # Rule C: Review possibly cancelled or inactive subscriptions
    for r in recurring_items:
        if r.status == "possibly_cancelled":
            action_count += 1
            action_items.append(
                ReportActionItem(
                    id=f"act-{action_count}",
                    category="subscription",
                    title=f"Confirm Cancellation: {r.merchant}",
                    description=(
                        f"{r.merchant} ({r.avg_amount_display}/{r.frequency}) hasn't been billed recently. "
                        "Confirm if you intended to cancel it to ensure autopay remains disabled."
                    ),
                    impact_type="medium",
                    potential_savings_minor=r.avg_amount_minor,
                    potential_savings_display=r.avg_amount_display,
                )
            )

    # Rule D: Spending Spikes
    for a in anomalies:
        if a.type == "spending_spike":
            sup = a.supporting_data or {}
            cat = sup.get("category", "Category")
            curr_amt = sup.get("current_spend_minor", 0)
            avg_amt = sup.get("average_spend_minor", 0)
            mult = sup.get("multiplier", 2.0)
            diff = curr_amt - avg_amt
            action_count += 1
            action_items.append(
                ReportActionItem(
                    id=f"act-{action_count}",
                    category="anomaly",
                    title=f"Cap Unplanned Spend in {cat}",
                    description=(
                        f"{cat} spending was {mult}x above your prior average ({format_amount(curr_amt, currency)} vs "
                        f"{format_amount(avg_amt, currency)}/mo). Setting a dedicated monthly budget can prevent future spikes."
                    ),
                    impact_type="medium",
                    potential_savings_minor=diff if diff > 0 else None,
                    potential_savings_display=format_amount(diff, currency) if diff > 0 else None,
                )
            )

    # Rule E: Goals that need acceleration
    for g in goal_statuses:
        if g.on_track is False and g.required_monthly_savings_minor:
            action_count += 1
            action_items.append(
                ReportActionItem(
                    id=f"act-{action_count}",
                    category="savings",
                    title=f"Accelerate {g.name} Savings",
                    description=(
                        f"To hit your target of {g.target_amount_display} by {g.target_date}, "
                        f"allocate {g.required_monthly_savings_display}/month (currently behind pace)."
                    ),
                    impact_type="medium",
                )
            )

    # Rule F: Discretionary spend optimization opportunity
    discretionary_cats = ["Dining", "Shopping", "Entertainment"]
    discretionary_spend = sum(
        c.amount_minor for c in top_categories if c.category in discretionary_cats
    )
    if expense_minor > 0 and (discretionary_spend / expense_minor) >= 0.20:
        trim_15 = int(discretionary_spend * 0.15)
        action_count += 1
        action_items.append(
            ReportActionItem(
                id=f"act-{action_count}",
                category="general",
                title="Trim 15% from Discretionary Outflows",
                description=(
                    f"Discretionary categories (Dining, Shopping, Entertainment) accounted for "
                    f"{format_amount(discretionary_spend, currency)} ({round((discretionary_spend/expense_minor)*100, 1)}% of expenses). "
                    f"Trimming 15% would save {format_amount(trim_15, currency)}/month toward your emergency fund or goals."
                ),
                impact_type="low",
                potential_savings_minor=trim_15,
                potential_savings_display=format_amount(trim_15, currency),
            )
        )

    # Rule G: Positive reinforcement if high savings rate
    if savings_rate_pct >= 25.0:
        action_count += 1
        action_items.append(
            ReportActionItem(
                id=f"act-{action_count}",
                category="savings",
                title="Sustain Your Strong Savings Habit",
                description=(
                    f"Outstanding work: you saved {savings_rate_pct}% of your income in {month_name}. "
                    "Transfer this surplus directly into your liquid emergency reserve or savings goal."
                ),
                impact_type="low",
            )
        )

    return MonthlyReportResponse(
        month=month_str,
        month_name=month_name,
        user_id=user_id,
        currency=currency,
        cash_flow=cash_flow,
        narrative=summary_obj.generated_text or "No narrative available.",
        top_categories=top_categories,
        top_merchants=top_merchants,
        budgets=budget_statuses,
        goals=goal_statuses,
        recurring=recurring_items,
        anomalies=anomaly_items,
        action_items=action_items,
        disclaimer=DISCLAIMER_TEXT,
    )
