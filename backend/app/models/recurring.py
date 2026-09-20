from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum

class RecurringFrequency(enum.Enum):
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"

class RecurringStatus(enum.Enum):
    active = "active"
    possibly_cancelled = "possibly_cancelled"
    cancelled = "cancelled"

class RecurringType(enum.Enum):
    subscription = "subscription"
    bill = "bill"
    emi = "emi"
    other = "other"

class RecurringGroup(Base):
    __tablename__ = "recurring_groups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    merchant = Column(String, nullable=False)
    avg_amount_minor = Column(Integer, nullable=False)
    frequency = Column(Enum(RecurringFrequency), nullable=False)
    next_expected_date = Column(Date, nullable=True)
    last_seen = Column(Date, nullable=False)
    status = Column(Enum(RecurringStatus), nullable=False)
    type = Column(Enum(RecurringType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
