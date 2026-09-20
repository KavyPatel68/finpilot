from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any

class MonthlySummaryBase(BaseModel):
    month: str
    payload: Dict[str, Any]
    generated_text: Optional[str] = None

class MonthlySummaryCreate(MonthlySummaryBase):
    user_id: int

class MonthlySummaryResponse(MonthlySummaryBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
