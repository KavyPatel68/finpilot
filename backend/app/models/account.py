from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum

class AccountType(enum.Enum):
    bank = "bank"
    card = "card"
    cash = "cash"
    other = "other"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(Enum(AccountType), nullable=False)
    currency = Column(String, default="INR")
    account_number_masked = Column(String, nullable=True)
    institution = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
