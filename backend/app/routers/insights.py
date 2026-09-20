from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.insight import Insight, InsightSeverity
from app.schemas.insight import InsightResponse
from app.services.analytics.anomaly_detector import detect_anomalies

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=List[InsightResponse])
@router.get("/", response_model=List[InsightResponse])
def get_insights(
    user_id: int = Query(1),
    month: Optional[str] = None,
    type: Optional[str] = None,
    severity: Optional[InsightSeverity] = None,
    db: Session = Depends(get_db),
):
    query = select(Insight).where(Insight.user_id == user_id)

    if month:
        query = query.where(Insight.month == month)
    if type:
        query = query.where(Insight.type == type)
    if severity:
        query = query.where(Insight.severity == severity)

    query = query.order_by(Insight.created_at.desc(), Insight.id.desc())
    insights = db.scalars(query).all()

    # Auto-run detection if no insights exist yet
    if not insights:
        insights = detect_anomalies(db, user_id=user_id)
        if month:
            insights = [i for i in insights if i.month == month]

    return insights


@router.post("/detect", response_model=List[InsightResponse])
def trigger_anomaly_detection(
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Triggers duplicate charge and spending spike detection."""
    insights = detect_anomalies(db, user_id=user_id)
    return insights
