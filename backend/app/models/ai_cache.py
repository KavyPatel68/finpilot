from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Index
from app.database import Base


class AICache(Base):
    __tablename__ = "ai_cache"

    key_hash = Column(String(64), primary_key=True, index=True)  # SHA256 of task + prompt/inputs
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1, index=True)
    task_type = Column(String(50), nullable=False, index=True)  # "categorize", "qa", "insights", "routing"
    prompt_hash = Column(String(64), nullable=False)
    response_json = Column(JSON, nullable=False)
    estimated_tokens_saved = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_ai_cache_user_task", "user_id", "task_type"),
    )
