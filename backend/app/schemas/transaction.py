from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime, date
from typing import Optional, List
from app.models.transaction import TransactionDirection, CategorySource
from app.utils.amount import format_amount


class TransactionBase(BaseModel):
    account_id: int
    document_id: Optional[int] = None
    date: date
    raw_description: str
    merchant_normalized: Optional[str] = None
    amount_minor: int
    direction: TransactionDirection
    category: Optional[str] = None
    subcategory: Optional[str] = None
    category_source: Optional[CategorySource] = None
    confidence: Optional[float] = None
    is_recurring: bool = False
    recurring_group_id: Optional[int] = None
    is_transfer: bool = False
    is_anomaly: bool = False
    notes: Optional[str] = None
    balance_minor: Optional[int] = None
    payment_method: Optional[str] = None

    @computed_field
    @property
    def amount_display(self) -> str:
        return format_amount(self.amount_minor)


class TransactionCreate(TransactionBase):
    user_id: int


class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TransactionUpdate(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    notes: Optional[str] = None
    is_transfer: Optional[bool] = None
    merchant_normalized: Optional[str] = None
    create_rule: bool = True  # whether to persist this as a rule for future uploads


class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
