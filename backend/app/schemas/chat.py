from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models.chat import ChatRole


class ChatMessageBase(BaseModel):
    role: ChatRole
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None


class ChatMessageCreate(ChatMessageBase):
    user_id: int


class ChatMessageResponse(ChatMessageBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    message: str
    user_id: int = 1


class ChatResponse(BaseModel):
    reply: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None
    message_id: Optional[int] = None
    calculation_metadata: Optional[Dict[str, Any]] = None

