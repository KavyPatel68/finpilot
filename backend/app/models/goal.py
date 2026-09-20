from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
from app.database import Base
import enum

class GoalType(enum.Enum):
    emergency_fund = "emergency_fund"
    purchase = "purchase"
    custom = "custom"

class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(Enum(GoalType), nullable=False)
    target_amount_minor = Column(Integer, nullable=False)
    current_amount_minor = Column(Integer, default=0)
    target_date = Column(Date, nullable=True)
    monthly_contribution_planned_minor = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
