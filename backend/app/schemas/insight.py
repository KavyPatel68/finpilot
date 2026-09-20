from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.insight import InsightSeverity

class InsightBase(BaseModel):
    month: str
    type: str
    severity: InsightSeverity
    text: str
    supporting_data: Optional[Dict[str, Any]] = None

class InsightCreate(InsightBase):
    user_id: int

class InsightResponse(InsightBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
