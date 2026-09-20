from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from app.database import Base
import enum

class InsightSeverity(enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"

class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month = Column(String, nullable=False) # Format YYYY-MM
    type = Column(String, nullable=False)
    severity = Column(Enum(InsightSeverity), nullable=False)
    text = Column(String, nullable=False)
    supporting_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
