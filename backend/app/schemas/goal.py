from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime, date
from typing import Optional
from app.models.goal import GoalType
from app.utils.amount import format_amount


class GoalBase(BaseModel):
    name: str
    type: GoalType
    target_amount_minor: int
    current_amount_minor: int = 0
    target_date: Optional[date] = None
    monthly_contribution_planned_minor: Optional[int] = None
    is_active: bool = True

    @computed_field
    @property
    def target_amount_display(self) -> str:
        return format_amount(self.target_amount_minor)

    @computed_field
    @property
    def current_amount_display(self) -> str:
        return format_amount(self.current_amount_minor)


class GoalCreate(BaseModel):
    name: str
    type: GoalType = GoalType.custom
    target_amount_minor: int
    current_amount_minor: int = 0
    target_date: Optional[date] = None
    monthly_contribution_planned_minor: Optional[int] = None
    is_active: bool = True


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[GoalType] = None
    target_amount_minor: Optional[int] = None
    current_amount_minor: Optional[int] = None
    target_date: Optional[date] = None
    monthly_contribution_planned_minor: Optional[int] = None
    is_active: Optional[bool] = None


class GoalResponse(GoalBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class GoalProgressResponse(GoalResponse):
    progress_pct: float = 0.0
    months_remaining: Optional[int] = None
    required_monthly_savings_minor: Optional[int] = None
    on_track: Optional[bool] = None

    @computed_field
    @property
    def required_monthly_savings_display(self) -> str:
        if self.required_monthly_savings_minor is None:
            return "—"
        return format_amount(self.required_monthly_savings_minor)

    @computed_field
    @property
    def monthly_contribution_planned_display(self) -> str:
        if self.monthly_contribution_planned_minor is None:
            return "—"
        return format_amount(self.monthly_contribution_planned_minor)


class GoalSimulationRequest(BaseModel):
    goal_id: int
    cut_category: str
    cut_amount_minor: int  # Amount cut per month in minor units


class GoalSimulationResponse(BaseModel):
    goal_id: int
    goal_name: str
    cut_category: str
    cut_amount_minor: int
    cut_amount_display: str
    current_target_date: Optional[date] = None
    simulated_target_date: Optional[date] = None
    months_saved: int
    narrative: str
