from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base

class MonthlySummary(Base):
    __tablename__ = "monthly_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month = Column(String, nullable=False) # Format YYYY-MM
    payload = Column(JSON, nullable=False)
    generated_text = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
