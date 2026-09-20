from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from app.database import Base


class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1, index=True)
    task_type = Column(String(50), nullable=False, index=True)  # "categorize", "qa", "insights", "router"
    model = Column(String(100), nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    cached_read_tokens = Column(Integer, default=0, nullable=False)
    tokens_saved = Column(Integer, default=0, nullable=False)
    is_cache_hit = Column(Boolean, default=False, nullable=False)
    estimated_cost_usd = Column(Float, default=0.0, nullable=False)
    estimated_cost_inr = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_ai_usage_user_created", "user_id", "created_at"),
    )
