from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime, date
from typing import Optional
from app.utils.amount import format_amount


class BudgetBase(BaseModel):
    category: str
    monthly_limit_minor: int
    effective_from: date
    effective_to: Optional[date] = None

    @computed_field
    @property
    def monthly_limit_display(self) -> str:
        return format_amount(self.monthly_limit_minor)


class BudgetCreate(BaseModel):
    category: str
    monthly_limit_minor: int
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class BudgetUpdate(BaseModel):
    monthly_limit_minor: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class BudgetResponse(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BudgetProgressResponse(BudgetResponse):
    spent_minor: int = 0
    remaining_minor: int = 0
    spent_pct: float = 0.0
    status: str = "on_track"  # 'on_track' | 'warning' | 'exceeded'

    @computed_field
    @property
    def spent_display(self) -> str:
        return format_amount(self.spent_minor)

    @computed_field
    @property
    def remaining_display(self) -> str:
        return format_amount(self.remaining_minor)
