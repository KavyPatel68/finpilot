from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.chat import ChatMessage, ChatRole
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatMessageResponse,
)
from app.services.agent.orchestrator import run_agent

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
async def send_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    # 1. Fetch recent conversation history
    past_messages = (
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.user_id == payload.user_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(10)
        )
        .all()
    )
    history = [
        {"role": m.role.value if hasattr(m.role, "value") else str(m.role), "content": m.content}
        for m in past_messages
    ]

    # 2. Persist user message
    user_record = ChatMessage(
        user_id=payload.user_id,
        role=ChatRole.user,
        content=payload.message,
    )
    db.add(user_record)
    db.commit()

    # 3. Execute agent
    agent_output = await run_agent(
        user_message=payload.message,
        db=db,
        user_id=payload.user_id,
        chat_history=history,
    )

    # 4. Persist assistant reply
    assistant_record = ChatMessage(
        user_id=payload.user_id,
        role=ChatRole.assistant,
        content=agent_output["reply"],
        tool_calls=agent_output.get("tool_calls"),
        tool_results=agent_output.get("tool_results"),
    )
    db.add(assistant_record)
    db.commit()
    db.refresh(assistant_record)

    calc_meta = {
        "intent": agent_output.get("intent"),
        "confidence": agent_output.get("confidence"),
        "is_zero_token": (
            (agent_output.get("confidence") is not None and agent_output.get("confidence", 0) >= 0.80)
            or agent_output.get("is_cached", False)
            or agent_output.get("offline_mode", False)
        ),
        "is_cached": agent_output.get("is_cached", False),
        "offline_mode": agent_output.get("offline_mode", False),
        "tokens_used": agent_output.get("tokens_used", 0),
        "model": (
            "Zero-Token Intent Engine"
            if agent_output.get("confidence") is not None and agent_output.get("confidence", 0) >= 0.80
            else "SQLite Cache"
            if agent_output.get("is_cached")
            else "Deterministic Offline Mode"
            if agent_output.get("offline_mode")
            else "Claude Haiku 4.5"
        ),
    }

    return ChatResponse(
        reply=agent_output["reply"],
        tool_calls=agent_output.get("tool_calls"),
        tool_results=agent_output.get("tool_results"),
        message_id=assistant_record.id,
        calculation_metadata=calc_meta,
    )



@router.get("/history", response_model=List[ChatMessageResponse])
def get_chat_history(
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    messages = (
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.asc())
        )
        .all()
    )
    return messages


@router.delete("/history")
def clear_chat_history(
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
    db.commit()
    return {"status": "ok", "message": "Chat history cleared successfully"}
