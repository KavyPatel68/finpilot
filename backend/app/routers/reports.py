from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database import get_db
from app.models.transaction import Transaction
from app.schemas.report import MonthlyReportResponse
from app.services.report.insights_engine import generate_monthly_report
from app.services.report.pdf_exporter import build_monthly_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/months")
def get_available_months(
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Returns all available statement months for which transactions exist, sorted descending."""
    # Group transactions by YYYY-MM
    txns = (
        db.execute(
            select(
                func.strftime("%Y-%m", Transaction.date).label("month"),
                func.count(Transaction.id).label("count"),
            )
            .where(Transaction.user_id == user_id)
            .group_by("month")
            .order_by(func.strftime("%Y-%m", Transaction.date).desc())
        )
        .all()
    )

    result = []
    for r in txns:
        if r[0]:
            try:
                m_date = date.fromisoformat(f"{r[0]}-01")
                m_name = m_date.strftime("%B %Y")
            except Exception:
                m_name = r[0]
            result.append({
                "month": r[0],
                "month_name": m_name,
                "transaction_count": r[1],
            })

    return {"months": result}


@router.get("/{month}", response_model=MonthlyReportResponse)
def get_monthly_report_data(
    month: str,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Returns comprehensive monthly analytics, category breakdowns, budgets, goals, anomalies,

    and an actionable decision checklist for the specified month (YYYY-MM).
    """
    try:
        date.fromisoformat(f"{month}-01")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid month format. Expected 'YYYY-MM' (e.g. '2024-08').",
        )

    # Check if any transactions exist for this month
    count = db.scalar(
        select(func.count(Transaction.id)).where(
            Transaction.user_id == user_id,
            func.strftime("%Y-%m", Transaction.date) == month,
        )
    )
    if not count:
        raise HTTPException(
            status_code=404,
            detail=f"No transaction records found for statement period '{month}'.",
        )

    report = generate_monthly_report(db, month_str=month, user_id=user_id)
    return report


@router.get("/{month}/pdf")
def download_monthly_report_pdf(
    month: str,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Generates and streams an executive A4 PDF statement report for the specified month."""
    try:
        date.fromisoformat(f"{month}-01")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid month format. Expected 'YYYY-MM' (e.g. '2024-08').",
        )

    count = db.scalar(
        select(func.count(Transaction.id)).where(
            Transaction.user_id == user_id,
            func.strftime("%Y-%m", Transaction.date) == month,
        )
    )
    if not count:
        raise HTTPException(
            status_code=404,
            detail=f"No transaction records found for statement period '{month}'.",
        )

    report = generate_monthly_report(db, month_str=month, user_id=user_id)
    pdf_bytes = build_monthly_pdf(report)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=FinPilot_Report_{month}.pdf",
            "Content-Type": "application/pdf",
        },
    )
