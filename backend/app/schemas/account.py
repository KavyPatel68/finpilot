from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.account import AccountType

class AccountBase(BaseModel):
    name: str
    type: AccountType
    currency: str = "INR"
    account_number_masked: Optional[str] = None
    institution: Optional[str] = None

class AccountCreate(AccountBase):
    user_id: int

class AccountResponse(AccountBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
