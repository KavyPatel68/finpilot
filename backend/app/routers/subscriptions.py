from typing import Optional, List, Dict, Any
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.recurring import RecurringGroup, RecurringStatus, RecurringFrequency
from app.schemas.recurring import RecurringGroupResponse
from app.services.analytics.recurring_detector import detect_recurring_groups
from app.utils.amount import format_amount

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _roll_forward_date(base_date: date, frequency: RecurringFrequency, min_date: date) -> date:
    curr = base_date
    delta_days = 30
    if frequency == RecurringFrequency.weekly:
        delta_days = 7
    elif frequency == RecurringFrequency.quarterly:
        delta_days = 90
    elif frequency == RecurringFrequency.yearly:
        delta_days = 365

    while curr < min_date:
        curr = curr + timedelta(days=delta_days)
    return curr


@router.get("/upcoming")
def get_upcoming_obligations(
    days: int = Query(30, ge=7, le=90),
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Returns scheduled upcoming commitments (EMIs, bills, subscriptions) within the next N days."""
    groups = (
        db.scalars(
            select(RecurringGroup)
            .where(
                RecurringGroup.user_id == user_id,
                RecurringGroup.status != RecurringStatus.cancelled,
            )
            .order_by(RecurringGroup.next_expected_date.asc())
        )
        .all()
    )

    if not groups:
        groups, _ = detect_recurring_groups(db, user_id=user_id)

    today = date.today()
    # If dataset is historical, use latest last_seen as reference point
    if groups and all(g.last_seen < (today - timedelta(days=180)) for g in groups):
        ref_date = max(g.last_seen for g in groups)
    else:
        ref_date = today

    end_window = ref_date + timedelta(days=days)

    upcoming_items: List[Dict[str, Any]] = []
    total_upcoming_minor = 0

    for g in groups:
        if not g.next_expected_date:
            continue

        due_date = _roll_forward_date(g.next_expected_date, g.frequency, ref_date)

        if ref_date <= due_date <= end_window:
            days_until = (due_date - ref_date).days
            total_upcoming_minor += g.avg_amount_minor
            upcoming_items.append(
                {
                    "id": g.id,
                    "merchant": g.merchant,
                    "type": g.type.value if hasattr(g.type, "value") else str(g.type),
                    "amount_minor": g.avg_amount_minor,
                    "amount_display": format_amount(g.avg_amount_minor),
                    "due_date": str(due_date),
                    "days_until_due": days_until,
                    "frequency": g.frequency.value if hasattr(g.frequency, "value") else str(g.frequency),
                }
            )

    upcoming_items.sort(key=lambda x: x["days_until_due"])

    return {
        "reference_date": str(ref_date),
        "window_days": days,
        "total_upcoming_minor": total_upcoming_minor,
        "total_upcoming_display": format_amount(total_upcoming_minor),
        "count": len(upcoming_items),
        "items": upcoming_items,
    }


@router.get("", response_model=List[RecurringGroupResponse])
@router.get("/", response_model=List[RecurringGroupResponse])
def get_subscriptions(
    user_id: int = Query(1),
    status: Optional[RecurringStatus] = None,
    db: Session = Depends(get_db),
):
    query = select(RecurringGroup).where(RecurringGroup.user_id == user_id)
    if status:
        query = query.where(RecurringGroup.status == status)
    query = query.order_by(RecurringGroup.avg_amount_minor.desc())
    groups = db.scalars(query).all()

    # Auto-detect if no groups exist yet
    if not groups:
        groups, _ = detect_recurring_groups(db, user_id=user_id)

    return groups


@router.post("/detect")
def trigger_detection(
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    groups, price_hikes = detect_recurring_groups(db, user_id=user_id)
    return {
        "groups_count": len(groups),
        "price_hikes": price_hikes,
        "message": f"Successfully detected {len(groups)} recurring commitments",
    }


@router.get("/hikes")
def get_price_hikes(
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Returns detected subscription price increases (e.g. Netflix jumping from ₹649 to ₹799)."""
    _, hikes = detect_recurring_groups(db, user_id=user_id)
    return [
        {
            "merchant": h["merchant"],
            "previous_amount_minor": h["previous_amount_minor"],
            "previous_amount_display": format_amount(h["previous_amount_minor"]),
            "new_amount_minor": h["new_amount_minor"],
            "new_amount_display": format_amount(h["new_amount_minor"]),
            "difference_minor": h["difference_minor"],
            "difference_display": format_amount(h["difference_minor"]),
            "effective_date": str(h["effective_date"]),
        }
        for h in hikes
    ]



@router.patch("/{group_id}/status", response_model=RecurringGroupResponse)
def update_subscription_status(
    group_id: int,
    status: RecurringStatus = Query(...),
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    group = db.get(RecurringGroup, group_id)
    if not group or group.user_id != user_id:
        raise HTTPException(status_code=404, detail="Subscription group not found")

    group.status = status
    db.commit()
    db.refresh(group)
    return group
