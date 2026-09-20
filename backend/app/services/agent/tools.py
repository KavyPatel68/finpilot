from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, desc
from dateutil.relativedelta import relativedelta

from app.models.transaction import Transaction, TransactionDirection
from app.models.recurring import RecurringGroup, RecurringStatus
from app.models.budget import Budget
from app.models.goal import Goal
from app.models.insight import Insight
from app.services.analytics.monthly_summary import generate_monthly_summary
from app.services.analytics.recurring_detector import detect_recurring_groups
from app.services.analytics.anomaly_detector import detect_anomalies
from app.utils.amount import format_amount
from app.services.categorization.taxonomy import CATEGORIES

# ── 1. Tool Declarations (OpenAI / Anthropic Compatible Schemas) ──────────────

TOOLS_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "get_data_range",
        "description": "Returns the min date, max date, and available statement months so relative queries (e.g. 'this month', 'latest') are grounded in user statement data.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_spending_by_category",
        "description": "Retrieves categorical spending breakdown for a specific month (YYYY-MM). Can be filtered to a single category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Month in YYYY-MM format. Omit for latest statement month."},
                "category": {"type": "string", "description": "Optional category name (e.g. 'Dining', 'Shopping')."},
            },
        },
    },
    {
        "name": "get_top_merchants",
        "description": "Lists top payees / merchants by total expense amount for a given month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Month in YYYY-MM format."},
                "limit": {"type": "integer", "description": "Number of merchants to return (default 10, max 20)."},
            },
        },
    },
    {
        "name": "compare_periods",
        "description": "Compares spending between two statement months (e.g. '2024-06' and '2024-07') showing rupee difference and percentage change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period1": {"type": "string", "description": "First month in YYYY-MM format."},
                "period2": {"type": "string", "description": "Second month in YYYY-MM format."},
            },
            "required": ["period1", "period2"],
        },
    },
    {
        "name": "list_subscriptions",
        "description": "Lists recurring commitments, bills, subscriptions, and EMIs with frequency, average amount, next renewal date, and status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "possibly_cancelled", "cancelled", "all"], "description": "Filter status (default 'active')."},
            },
        },
    },
    {
        "name": "get_upcoming_obligations",
        "description": "Returns scheduled bills, EMIs, and renewal dates due within the next window_days (7-90 days).",
        "input_schema": {
            "type": "object",
            "properties": {
                "window_days": {"type": "integer", "description": "Number of days ahead to check (default 30)."},
            },
        },
    },
    {
        "name": "get_budget_status",
        "description": "Checks category budgets, actual month-to-date spending, remaining buffer, and over-budget warnings for a given month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Month in YYYY-MM format. Defaults to latest month."},
            },
        },
    },
    {
        "name": "get_committed_budget",
        "description": "Calculates total fixed recurring commitments (EMIs + bills) vs discretionary spending allowances.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Month in YYYY-MM format."},
            },
        },
    },
    {
        "name": "get_goal_progress",
        "description": "Retrieves the user's savings goals, progress percentages, target dates, and required monthly savings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id": {"type": "integer", "description": "Optional specific goal ID."},
            },
        },
    },
    {
        "name": "simulate_goal_scenario",
        "description": "Simulates how many months earlier a savings goal is reached when reducing discretionary category spend.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cut_category": {"type": "string", "description": "Category to reduce (e.g. 'Dining', 'Shopping')."},
                "cut_amount_rupees": {"type": "number", "description": "Monthly cut in Rupees (e.g. 3000)."},
                "goal_name": {"type": "string", "description": "Name of the target goal (e.g. 'Emergency Fund')."},
            },
            "required": ["cut_category", "cut_amount_rupees"],
        },
    },
    {
        "name": "search_transactions",
        "description": "Searches transactions by keyword, category, or date range. Capped at 30 rows.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword to search in description/merchant."},
                "category": {"type": "string", "description": "Filter by category."},
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD."},
                "end_date": {"type": "string", "description": "End date YYYY-MM-DD."},
                "limit": {"type": "integer", "description": "Max rows to return (default 10, max 30)."},
            },
        },
    },
    {
        "name": "get_anomalies",
        "description": "Returns detected duplicate charges, spending spikes, and subscription price hikes for a given month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Month in YYYY-MM format."},
            },
        },
    },
    # ── Action Tools (Return pending_action for UI confirmation) ─────────────
    {
        "name": "set_budget",
        "description": "Creates or updates a monthly budget limit for a category. Requires user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Category name."},
                "limit_rupees": {"type": "number", "description": "Monthly limit in Rupees."},
            },
            "required": ["category", "limit_rupees"],
        },
    },
    {
        "name": "create_goal",
        "description": "Creates a new savings goal milestone. Requires user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the goal."},
                "target_rupees": {"type": "number", "description": "Target amount in Rupees."},
                "target_date": {"type": "string", "description": "Target completion date (YYYY-MM-DD)."},
            },
            "required": ["name", "target_rupees"],
        },
    },
    {
        "name": "recategorize",
        "description": "Changes the category of a merchant and remembers the rule for future uploads. Requires user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "merchant": {"type": "string", "description": "Merchant or payee name."},
                "category": {"type": "string", "description": "New category name."},
            },
            "required": ["merchant", "category"],
        },
    },
    {
        "name": "mark_subscription_cancelled",
        "description": "Marks a recurring subscription as cancelled so it is excluded from upcoming bills. Requires user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "merchant": {"type": "string", "description": "Merchant name of the subscription to cancel."},
            },
            "required": ["merchant"],
        },
    },
]


# ── 2. Tool Execution Logic (Deterministic & user_id Scoped) ─────────────────

def execute_tool(
    tool_name: str,
    tool_args: Dict[str, Any],
    db: Session,
    user_id: int = 1,
) -> Dict[str, Any]:
    """Executes deterministic tool calls against the database with strict scoping."""
    # Normalize aliases
    if tool_name == "get_monthly_summary":
        tool_name = "get_spending_by_category"
    elif tool_name == "get_subscriptions":
        tool_name = "list_subscriptions"
    elif tool_name == "get_goals":
        tool_name = "get_goal_progress"
    elif tool_name == "simulate_spending_cut":
        tool_name = "simulate_goal_scenario"

    # 1. get_data_range
    if tool_name == "get_data_range":
        min_date = db.scalar(select(func.min(Transaction.date)).where(Transaction.user_id == user_id))
        max_date = db.scalar(select(func.max(Transaction.date)).where(Transaction.user_id == user_id))
        months_rows = db.execute(
            select(func.strftime("%Y-%m", Transaction.date))
            .where(Transaction.user_id == user_id)
            .distinct()
            .order_by(desc(func.strftime("%Y-%m", Transaction.date)))
        ).all()
        months = [r[0] for r in months_rows if r[0]]
        return {
            "min_date": str(min_date) if min_date else None,
            "max_date": str(max_date) if max_date else None,
            "latest_month": months[0] if months else None,
            "available_months": months,
            "total_months": len(months),
        }

    # Helper to resolve month
    def _resolve_month(m: Optional[str]) -> str:
        if m:
            return m
        latest = db.scalar(select(func.max(Transaction.date)).where(Transaction.user_id == user_id))
        return latest.strftime("%Y-%m") if latest else date.today().strftime("%Y-%m")

    # 2. get_spending_by_category
    if tool_name == "get_spending_by_category":
        month = _resolve_month(tool_args.get("month"))
        summary = generate_monthly_summary(db, month_str=month, user_id=user_id)
        p = summary.payload
        top_cats = p.get("top_categories", [])
        requested_cat = tool_args.get("category")

        if requested_cat:
            cat_lower = requested_cat.lower()
            matching = [c for c in top_cats if cat_lower in c["category"].lower()]
            if matching:
                target = matching[0]
                return {
                    "month": month,
                    "category": target["category"],
                    "amount": target["amount_display"],
                    "amount_minor": target["amount_minor"],
                    "pct_of_total": f"{target['pct_of_total']}%",
                    "transaction_count": target["transaction_count"],
                    "total_month_expenses": format_amount(p["expense_minor"]),
                }
            else:
                return {
                    "month": month,
                    "category": requested_cat,
                    "amount": "₹0.00",
                    "amount_minor": 0,
                    "pct_of_total": "0.0%",
                    "transaction_count": 0,
                    "total_month_expenses": format_amount(p["expense_minor"]),
                    "note": f"No expenses found for category '{requested_cat}' in {month}.",
                }

        return {
            "month": month,
            "income": format_amount(p["income_minor"]),
            "expenses": format_amount(p["expense_minor"]),
            "net_savings": format_amount(p["net_savings_minor"]),
            "savings_rate": f"{p['savings_rate_pct']}%",
            "mom_spending_change": f"{p['mom_change_pct']}%" if p.get("mom_change_pct") is not None else "N/A",
            "top_categories": top_cats[:10],
        }

    # 3. get_top_merchants
    elif tool_name == "get_top_merchants":
        month = _resolve_month(tool_args.get("month"))
        start_date = date.fromisoformat(f"{month}-01")
        next_month = start_date + relativedelta(months=1)
        limit = min(20, max(1, tool_args.get("limit", 10)))

        query = (
            select(
                func.coalesce(Transaction.merchant_normalized, Transaction.raw_description).label("merchant"),
                func.sum(Transaction.amount_minor).label("total_minor"),
                func.count(Transaction.id).label("txn_count"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.date < next_month,
                Transaction.direction == TransactionDirection.expense,
                Transaction.is_transfer.is_(False),
            )
            .group_by("merchant")
            .order_by(desc("total_minor"))
            .limit(limit)
        )
        rows = db.execute(query).all()
        return {
            "month": month,
            "count": len(rows),
            "merchants": [
                {
                    "merchant": r[0],
                    "amount": format_amount(r[1]),
                    "amount_minor": r[1],
                    "transaction_count": r[2],
                }
                for r in rows
            ],
        }

    # 4. compare_periods
    elif tool_name == "compare_periods":
        p1 = tool_args.get("period1")
        p2 = tool_args.get("period2")
        if not p1 or not p2:
            return {"error": "Both 'period1' and 'period2' are required in YYYY-MM format."}

        s1 = generate_monthly_summary(db, month_str=p1, user_id=user_id).payload
        s2 = generate_monthly_summary(db, month_str=p2, user_id=user_id).payload

        exp1 = s1["expense_minor"]
        exp2 = s2["expense_minor"]
        diff_minor = exp2 - exp1
        pct_change = round((diff_minor / exp1) * 100, 1) if exp1 > 0 else 0.0

        return {
            "period1": p1,
            "period1_expense": format_amount(exp1),
            "period2": p2,
            "period2_expense": format_amount(exp2),
            "difference": format_amount(abs(diff_minor)),
            "difference_minor": diff_minor,
            "percentage_change": f"{'+' if pct_change > 0 else ''}{pct_change}%",
            "direction": "increased" if diff_minor > 0 else "decreased" if diff_minor < 0 else "unchanged",
        }

    # 5. list_subscriptions
    elif tool_name == "list_subscriptions":
        status_filter = tool_args.get("status", "active")
        q = select(RecurringGroup).where(RecurringGroup.user_id == user_id)
        if status_filter != "all":
            q = q.where(RecurringGroup.status == status_filter)

        groups = db.scalars(q.order_by(desc(RecurringGroup.avg_amount_minor))).all()
        if not groups and status_filter in ["active", "all"]:
            groups, _ = detect_recurring_groups(db, user_id=user_id)

        total_monthly_minor = sum(
            g.avg_amount_minor * 4 if g.frequency.value == "weekly"
            else g.avg_amount_minor // 3 if g.frequency.value == "quarterly"
            else g.avg_amount_minor // 12 if g.frequency.value == "yearly"
            else g.avg_amount_minor
            for g in groups if g.status.value == "active"
        )

        return {
            "count": len(groups),
            "total_monthly_recurring": format_amount(total_monthly_minor),
            "total_monthly_recurring_minor": total_monthly_minor,
            "subscriptions": [
                {
                    "id": g.id,
                    "merchant": g.merchant,
                    "frequency": g.frequency.value if hasattr(g.frequency, "value") else str(g.frequency),
                    "amount": format_amount(g.avg_amount_minor),
                    "amount_minor": g.avg_amount_minor,
                    "status": g.status.value if hasattr(g.status, "value") else str(g.status),
                    "type": g.type.value if hasattr(g.type, "value") else str(g.type),
                    "next_due_date": str(g.next_expected_date) if g.next_expected_date else None,
                }
                for g in groups
            ],
        }

    # 6. get_upcoming_obligations
    elif tool_name == "get_upcoming_obligations":
        days = min(90, max(7, tool_args.get("window_days", 30)))
        from app.routers.subscriptions import get_upcoming_obligations as list_upcoming_commitments
        try:
            res = list_upcoming_commitments(days=days, user_id=user_id, db=db)
            return res if isinstance(res, dict) else res.model_dump()
        except Exception:
            # Fallback direct lookup
            groups = db.scalars(select(RecurringGroup).where(RecurringGroup.user_id == user_id, RecurringGroup.status == RecurringStatus.active)).all()
            return {
                "window_days": days,
                "count": len(groups),
                "items": [
                    {
                        "merchant": g.merchant,
                        "amount": format_amount(g.avg_amount_minor),
                        "frequency": str(g.frequency.value),
                        "due_date": str(g.next_expected_date or date.today()),
                    }
                    for g in groups[:15]
                ],
            }

    # 7. get_budget_status
    elif tool_name == "get_budget_status":
        month = _resolve_month(tool_args.get("month"))
        start_date = date.fromisoformat(f"{month}-01")
        next_month = start_date + relativedelta(months=1)

        budgets = db.scalars(select(Budget).where(Budget.user_id == user_id)).all()
        spend_query = (
            select(Transaction.category, func.sum(Transaction.amount_minor))
            .where(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.date < next_month,
                Transaction.direction == TransactionDirection.expense,
                Transaction.is_transfer.is_(False),
            )
            .group_by(Transaction.category)
        )
        spend_by_cat = dict(db.execute(spend_query).all())

        results = []
        for b in budgets:
            spent = spend_by_cat.get(b.category, 0)
            pct = round((spent / b.monthly_limit_minor) * 100, 1) if b.monthly_limit_minor > 0 else 0
            results.append({
                "category": b.category,
                "monthly_limit": format_amount(b.monthly_limit_minor),
                "monthly_limit_minor": b.monthly_limit_minor,
                "spent": format_amount(spent),
                "spent_minor": spent,
                "remaining": format_amount(max(0, b.monthly_limit_minor - spent)),
                "remaining_minor": max(0, b.monthly_limit_minor - spent),
                "spent_pct": f"{pct}%",
                "status": "exceeded" if spent > b.monthly_limit_minor else "warning" if pct >= 80 else "on_track",
            })
        return {"month": month, "count": len(results), "budgets": results}

    # 8. get_committed_budget
    elif tool_name == "get_committed_budget":
        month = _resolve_month(tool_args.get("month"))
        groups = db.scalars(select(RecurringGroup).where(RecurringGroup.user_id == user_id, RecurringGroup.status == RecurringStatus.active)).all()
        fixed_minor = sum(g.avg_amount_minor for g in groups if g.type.value in ["emi", "bill"])
        subs_minor = sum(g.avg_amount_minor for g in groups if g.type.value == "subscription")
        budgets = db.scalars(select(Budget).where(Budget.user_id == user_id)).all()
        total_budget_limit = sum(b.monthly_limit_minor for b in budgets)

        return {
            "month": month,
            "fixed_debt_and_utilities": format_amount(fixed_minor),
            "fixed_debt_and_utilities_minor": fixed_minor,
            "discretionary_subscriptions": format_amount(subs_minor),
            "discretionary_subscriptions_minor": subs_minor,
            "total_budgeted_caps": format_amount(total_budget_limit),
            "total_budgeted_caps_minor": total_budget_limit,
            "total_committed_outflow": format_amount(fixed_minor + subs_minor),
        }

    # 9. get_goal_progress
    elif tool_name == "get_goal_progress":
        q = select(Goal).where(Goal.user_id == user_id)
        if tool_args.get("goal_id"):
            q = q.where(Goal.id == tool_args["goal_id"])
        goals = db.scalars(q).all()

        return {
            "count": len(goals),
            "goals": [
                {
                    "id": g.id,
                    "name": g.name,
                    "target_amount": format_amount(g.target_amount_minor),
                    "target_amount_minor": g.target_amount_minor,
                    "current_saved": format_amount(g.current_amount_minor),
                    "current_saved_minor": g.current_amount_minor,
                    "progress_pct": f"{round((g.current_amount_minor / g.target_amount_minor) * 100, 1)}%" if g.target_amount_minor > 0 else "0.0%",
                    "target_date": str(g.target_date) if g.target_date else None,
                    "planned_monthly": format_amount(g.monthly_contribution_planned_minor) if g.monthly_contribution_planned_minor else None,
                }
                for g in goals
            ],
        }

    # 10. simulate_goal_scenario
    elif tool_name == "simulate_goal_scenario":
        cut_cat = tool_args["cut_category"]
        cut_rupees = float(tool_args["cut_amount_rupees"])
        cut_minor = int(cut_rupees * 100)

        goal = None
        if tool_args.get("goal_name"):
            gname = tool_args["goal_name"].lower()
            goals = db.scalars(select(Goal).where(Goal.user_id == user_id)).all()
            goal = next((g for g in goals if gname in g.name.lower()), None)
        if not goal:
            goal = db.scalar(select(Goal).where(Goal.user_id == user_id).order_by(Goal.id.asc()))

        if not goal:
            return {"error": "No active savings goal found to simulate."}

        rem_minor = max(0, goal.target_amount_minor - goal.current_amount_minor)
        cur_contrib = goal.monthly_contribution_planned_minor or 1000000
        new_contrib = cur_contrib + cut_minor

        cur_months = (rem_minor + cur_contrib - 1) // cur_contrib if cur_contrib > 0 else 24
        new_months = (rem_minor + new_contrib - 1) // new_contrib if new_contrib > 0 else 12
        months_saved = max(0, cur_months - new_months)

        return {
            "goal_name": goal.name,
            "category_cut": cut_cat,
            "monthly_cut": format_amount(cut_minor),
            "monthly_cut_minor": cut_minor,
            "months_saved": months_saved,
            "simulated_completion_date": str(date.today() + relativedelta(months=new_months)),
            "message": f"By reducing {cut_cat} spend by {format_amount(cut_minor)}/month, you could achieve your '{goal.name}' goal {months_saved} month{'s' if months_saved != 1 else ''} earlier.",
        }

    # 11. search_transactions
    elif tool_name == "search_transactions":
        query = select(Transaction).where(Transaction.user_id == user_id)
        if tool_args.get("query"):
            term = f"%{tool_args['query'].strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(Transaction.raw_description).like(term),
                    func.lower(Transaction.merchant_normalized).like(term),
                )
            )
        if tool_args.get("category"):
            query = query.where(Transaction.category == tool_args["category"])
        if tool_args.get("start_date"):
            query = query.where(Transaction.date >= date.fromisoformat(tool_args["start_date"]))
        if tool_args.get("end_date"):
            query = query.where(Transaction.date <= date.fromisoformat(tool_args["end_date"]))

        limit = min(30, max(1, tool_args.get("limit", 10)))
        txns = db.scalars(query.order_by(desc(Transaction.date)).limit(limit)).all()

        return {
            "count": len(txns),
            "transactions": [
                {
                    "id": t.id,
                    "date": str(t.date),
                    "merchant": t.merchant_normalized or t.raw_description,
                    "amount": format_amount(t.amount_minor),
                    "amount_minor": t.amount_minor,
                    "direction": str(t.direction.value),
                    "category": t.category,
                }
                for t in txns
            ],
        }

    # 12. get_anomalies
    elif tool_name == "get_anomalies":
        month = tool_args.get("month")
        q = select(Insight).where(Insight.user_id == user_id)
        if month:
            q = q.where(Insight.month == month)
        insights = db.scalars(q.order_by(desc(Insight.created_at))).all()
        if not insights:
            insights = detect_anomalies(db, user_id=user_id)
            if month:
                insights = [i for i in insights if i.month == month]

        return {
            "count": len(insights),
            "anomalies": [
                {
                    "type": i.type,
                    "severity": str(i.severity.value),
                    "month": i.month,
                    "description": i.text,
                }
                for i in insights
            ],
        }

    # ── 13-16. Action Tools (Staged confirmation) ───────────────────────────
    elif tool_name in ["set_budget", "create_goal", "recategorize", "mark_subscription_cancelled"]:
        import uuid
        action_id = f"act_{uuid.uuid4().hex[:8]}"

        if tool_name == "set_budget":
            cat = tool_args.get("category", "General")
            if cat not in CATEGORIES:
                return {"error": f"Invalid category '{cat}'. Valid categories: {CATEGORIES[:8]}..."}
            lim = float(tool_args.get("limit_rupees", 5000))
            summary = f"Set monthly budget limit for **{cat}** to **₹{lim:,.2f}**"
        elif tool_name == "create_goal":
            g_name = tool_args.get("name", "New Savings Goal")
            target = float(tool_args.get("target_rupees", 50000))
            t_date = tool_args.get("target_date") or str(date.today() + relativedelta(years=1))
            summary = f"Create new goal **'{g_name}'** targeting **₹{target:,.2f}** by **{t_date}**"
        elif tool_name == "recategorize":
            merch = tool_args.get("merchant", "")
            cat = tool_args.get("category", "Other")
            summary = f"Recategorize **'{merch}'** to **{cat}** and remember rule for future uploads"
        elif tool_name == "mark_subscription_cancelled":
            merch = tool_args.get("merchant", "")
            summary = f"Mark subscription **'{merch}'** as cancelled"

        return {
            "status": "confirmation_required",
            "pending_action": {
                "action_id": action_id,
                "tool_name": tool_name,
                "parameters": tool_args,
                "summary": summary,
            },
            "message": f"Action prepared: {summary}. Please confirm to proceed.",
        }

    return {"error": f"Unknown tool: '{tool_name}'. Available tools: {[t['name'] for t in TOOLS_DEFINITIONS]}"}
