from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database import get_db
from app.models.transaction import Transaction
from app.models.summary import MonthlySummary
from app.schemas.summary import MonthlySummaryResponse
from app.services.analytics.monthly_summary import generate_monthly_summary

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("/months", response_model=List[str])
def get_available_months(
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Returns list of distinct YYYY-MM months containing user transactions, sorted latest first."""
    results = (
        db.scalars(
            select(func.strftime("%Y-%m", Transaction.date))
            .where(Transaction.user_id == user_id)
            .distinct()
            .order_by(func.strftime("%Y-%m", Transaction.date).desc())
        )
        .all()
    )
    return [r for r in results if r]


@router.get("", response_model=MonthlySummaryResponse)
@router.get("/", response_model=MonthlySummaryResponse)
def get_monthly_summary(
    month: Optional[str] = Query(None, description="Month in YYYY-MM format"),
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    # Determine target month
    if not month:
        latest_date = db.scalar(
            select(func.max(Transaction.date)).where(Transaction.user_id == user_id)
        )
        if latest_date:
            month = latest_date.strftime("%Y-%m")
        else:
            month = date.today().strftime("%Y-%m")

    # Generate or retrieve existing summary
    summary = generate_monthly_summary(db, month_str=month, user_id=user_id)
    return summary


@router.get("/trends")
def get_spending_trends(
    months: int = Query(6, ge=1, le=24),
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Returns monthly income, expense, net savings, and savings rate trends for the last N months."""
    from app.utils.amount import format_amount

    available_months = (
        db.scalars(
            select(func.strftime("%Y-%m", Transaction.date))
            .where(Transaction.user_id == user_id)
            .distinct()
            .order_by(func.strftime("%Y-%m", Transaction.date).desc())
            .limit(months)
        )
        .all()
    )
    # Sort ascending for chronological trend charts
    sorted_months = sorted([m for m in available_months if m])

    trends = []
    for m in sorted_months:
        summary = generate_monthly_summary(db, month_str=m, user_id=user_id)
        p = summary.payload
        try:
            d = date.fromisoformat(f"{m}-01")
            m_name = d.strftime("%b %Y")
        except Exception:
            m_name = m

        trends.append({
            "month": m,
            "month_name": m_name,
            "income_minor": p.get("income_minor", 0),
            "income_display": format_amount(p.get("income_minor", 0)),
            "expense_minor": p.get("expense_minor", 0),
            "expense_display": format_amount(p.get("expense_minor", 0)),
            "net_savings_minor": p.get("net_savings_minor", 0),
            "net_savings_display": format_amount(p.get("net_savings_minor", 0)),
            "savings_rate_pct": p.get("savings_rate_pct", 0.0),
        })
    return trends


@router.post("/{month}/generate", response_model=MonthlySummaryResponse)
def regenerate_monthly_summary(
    month: str,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Force re-calculation of monthly summary."""
    summary = generate_monthly_summary(db, month_str=month, user_id=user_id)
    return summary

