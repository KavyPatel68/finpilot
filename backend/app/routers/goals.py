import math
from typing import Optional, List
from datetime import date
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.goal import Goal
from app.schemas.goal import (
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    GoalProgressResponse,
    GoalSimulationRequest,
    GoalSimulationResponse,
)
from app.utils.amount import format_amount

router = APIRouter(prefix="/goals", tags=["goals"])


def _calculate_goal_progress(goal: Goal) -> GoalProgressResponse:
    today = date.today()
    progress_pct = (
        round((goal.current_amount_minor / goal.target_amount_minor) * 100, 1)
        if goal.target_amount_minor > 0
        else 0.0
    )
    progress_pct = min(100.0, max(0.0, progress_pct))

    months_remaining = None
    required_monthly = None
    on_track = None

    if goal.target_date:
        remaining_to_save = max(0, goal.target_amount_minor - goal.current_amount_minor)
        if goal.target_date > today:
            months_remaining = max(
                1,
                (goal.target_date.year - today.year) * 12
                + (goal.target_date.month - today.month),
            )
            required_monthly = math.ceil(remaining_to_save / months_remaining)
            if goal.monthly_contribution_planned_minor is not None:
                on_track = goal.monthly_contribution_planned_minor >= required_monthly
        else:
            months_remaining = 0
            required_monthly = remaining_to_save
            on_track = remaining_to_save == 0

    return GoalProgressResponse(
        id=goal.id,
        user_id=goal.user_id,
        name=goal.name,
        type=goal.type,
        target_amount_minor=goal.target_amount_minor,
        current_amount_minor=goal.current_amount_minor,
        target_date=goal.target_date,
        monthly_contribution_planned_minor=goal.monthly_contribution_planned_minor,
        is_active=goal.is_active,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
        progress_pct=progress_pct,
        months_remaining=months_remaining,
        required_monthly_savings_minor=required_monthly,
        on_track=on_track,
    )


@router.get("", response_model=List[GoalProgressResponse])
@router.get("/", response_model=List[GoalProgressResponse])
def list_goals(
    user_id: int = Query(1),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = select(Goal).where(Goal.user_id == user_id)
    if is_active is not None:
        query = query.where(Goal.is_active == is_active)
    query = query.order_by(Goal.created_at.desc())
    goals = db.scalars(query).all()

    return [_calculate_goal_progress(g) for g in goals]


@router.post("", response_model=GoalResponse)
@router.post("/", response_model=GoalResponse)
def create_goal(
    payload: GoalCreate,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    goal = Goal(
        user_id=user_id,
        name=payload.name,
        type=payload.type,
        target_amount_minor=payload.target_amount_minor,
        current_amount_minor=payload.current_amount_minor,
        target_date=payload.target_date,
        monthly_contribution_planned_minor=payload.monthly_contribution_planned_minor,
        is_active=payload.is_active,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.patch("/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    goal = db.get(Goal, goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(status_code=404, detail="Goal not found")

    if payload.name is not None:
        goal.name = payload.name
    if payload.type is not None:
        goal.type = payload.type
    if payload.target_amount_minor is not None:
        goal.target_amount_minor = payload.target_amount_minor
    if payload.current_amount_minor is not None:
        goal.current_amount_minor = payload.current_amount_minor
    if payload.target_date is not None:
        goal.target_date = payload.target_date
    if payload.monthly_contribution_planned_minor is not None:
        goal.monthly_contribution_planned_minor = (
            payload.monthly_contribution_planned_minor
        )
    if payload.is_active is not None:
        goal.is_active = payload.is_active

    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/{goal_id}")
def delete_goal(
    goal_id: int,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    goal = db.get(Goal, goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(status_code=404, detail="Goal not found")

    db.delete(goal)
    db.commit()
    return {"status": "ok", "message": "Goal deleted successfully"}


@router.post("/simulate", response_model=GoalSimulationResponse)
def simulate_goal_acceleration(
    payload: GoalSimulationRequest,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Simulates goal acceleration when reducing discretionary spend in a category."""
    goal = db.get(Goal, payload.goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(status_code=404, detail="Goal not found")

    today = date.today()
    remaining_minor = max(0, goal.target_amount_minor - goal.current_amount_minor)

    # Current baseline monthly savings rate
    current_planned = goal.monthly_contribution_planned_minor or 1000000  # fallback ₹10,000
    new_monthly_planned = current_planned + payload.cut_amount_minor

    current_months = math.ceil(remaining_minor / current_planned) if current_planned > 0 else 24
    new_months = math.ceil(remaining_minor / new_monthly_planned) if new_monthly_planned > 0 else 12

    months_saved = max(0, current_months - new_months)
    simulated_target_date = today + relativedelta(months=new_months)

    cut_display = format_amount(payload.cut_amount_minor)
    narrative = (
        f"By reducing your {payload.cut_category} spend by {cut_display}/month, you can reach your "
        f"'{goal.name}' goal {months_saved} month{'s' if months_saved != 1 else ''} earlier "
        f"({simulated_target_date.strftime('%B %Y')})."
    )

    return GoalSimulationResponse(
        goal_id=goal.id,
        goal_name=goal.name,
        cut_category=payload.cut_category,
        cut_amount_minor=payload.cut_amount_minor,
        cut_amount_display=cut_display,
        current_target_date=goal.target_date,
        simulated_target_date=simulated_target_date,
        months_saved=months_saved,
        narrative=narrative,
    )
