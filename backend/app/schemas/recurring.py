from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime, date
from typing import Optional
from app.models.recurring import RecurringFrequency, RecurringStatus, RecurringType
from app.utils.amount import format_amount

class RecurringGroupBase(BaseModel):
    merchant: str
    avg_amount_minor: int
    frequency: RecurringFrequency
    next_expected_date: Optional[date] = None
    last_seen: date
    status: RecurringStatus
    type: RecurringType

    @computed_field
    @property
    def avg_amount_display(self) -> str:
        return format_amount(self.avg_amount_minor)

class RecurringGroupCreate(RecurringGroupBase):
    user_id: int

class RecurringGroupResponse(RecurringGroupBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
