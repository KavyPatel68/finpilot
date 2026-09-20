from typing import Optional, List
from datetime import date
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database import get_db
from app.models.budget import Budget
from app.models.transaction import Transaction, TransactionDirection
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetProgressResponse,
    BudgetResponse,
)
from app.services.categorization.taxonomy import CATEGORIES

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=List[BudgetProgressResponse])
@router.get("/", response_model=List[BudgetProgressResponse])
def list_budgets(
    user_id: int = Query(1),
    month: Optional[str] = Query(None, description="Month in YYYY-MM format"),
    db: Session = Depends(get_db),
):
    """Lists category budgets with month-to-date spending, remaining balance, and alert status."""
    if not month:
        latest_date = db.scalar(
            select(func.max(Transaction.date)).where(Transaction.user_id == user_id)
        )
        if latest_date:
            month = latest_date.strftime("%Y-%m")
        else:
            month = date.today().strftime("%Y-%m")

    start_date = date.fromisoformat(f"{month}-01")
    next_month = start_date + relativedelta(months=1)

    budgets = (
        db.scalars(
            select(Budget)
            .where(Budget.user_id == user_id)
            .order_by(Budget.monthly_limit_minor.desc())
        )
        .all()
    )

    # Calculate current month spend per category
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

    results: List[BudgetProgressResponse] = []
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

        results.append(
            BudgetProgressResponse(
                id=b.id,
                user_id=b.user_id,
                category=b.category,
                monthly_limit_minor=b.monthly_limit_minor,
                effective_from=b.effective_from,
                effective_to=b.effective_to,
                created_at=b.created_at,
                spent_minor=spent,
                remaining_minor=remaining,
                spent_pct=spent_pct,
                status=status,
            )
        )

    return results


@router.post("", response_model=BudgetResponse)
@router.post("/", response_model=BudgetResponse)
def create_budget(
    payload: BudgetCreate,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    if payload.category not in CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Category '{payload.category}' is not valid. Allowed categories: {CATEGORIES}",
        )

    # Check if budget already exists for this category
    existing = db.scalar(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.category == payload.category,
        )
    )
    if existing:
        # Update existing
        existing.monthly_limit_minor = payload.monthly_limit_minor
        if payload.effective_from:
            existing.effective_from = payload.effective_from
        db.commit()
        db.refresh(existing)
        return existing

    budget = Budget(
        user_id=user_id,
        category=payload.category,
        monthly_limit_minor=payload.monthly_limit_minor,
        effective_from=payload.effective_from or date.today().replace(day=1),
        effective_to=payload.effective_to,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.patch("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    budget = db.get(Budget, budget_id)
    if not budget or budget.user_id != user_id:
        raise HTTPException(status_code=404, detail="Budget not found")

    if payload.monthly_limit_minor is not None:
        budget.monthly_limit_minor = payload.monthly_limit_minor
    if payload.effective_from is not None:
        budget.effective_from = payload.effective_from
    if payload.effective_to is not None:
        budget.effective_to = payload.effective_to

    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}")
def delete_budget(
    budget_id: int,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    budget = db.get(Budget, budget_id)
    if not budget or budget.user_id != user_id:
        raise HTTPException(status_code=404, detail="Budget not found")

    db.delete(budget)
    db.commit()
    return {"status": "ok", "message": "Budget deleted successfully"}
