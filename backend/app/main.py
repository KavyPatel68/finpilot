from fastapi import FastAPI, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from sqlalchemy.orm import Session
from app.config import settings
from app.database import init_db, get_db
from app.models.user import User
from app.models.account import Account
from app.models.document import Document
from app.models.transaction import Transaction
from app.models.recurring import RecurringGroup
from app.models.budget import Budget
from app.models.goal import Goal
from app.models.insight import Insight
from app.models.summary import MonthlySummary
from app.models.chat import ChatMessage
from app.routers import upload, transactions, summary, subscriptions, budgets, goals, insights, chat, reports, ai

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
    db = next(get_db())
    default_user = db.query(User).filter(User.id == settings.DEFAULT_USER_ID).first()
    if not default_user:
        new_user = User(id=settings.DEFAULT_USER_ID, email="default@example.com", display_name="Default User")
        db.add(new_user)
        db.commit()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")
api_router.include_router(upload.router)
api_router.include_router(transactions.router)
api_router.include_router(summary.router)
api_router.include_router(subscriptions.router)
api_router.include_router(budgets.router)
api_router.include_router(goals.router)
api_router.include_router(insights.router)
api_router.include_router(chat.router)
api_router.include_router(reports.router)
api_router.include_router(ai.router)
app.include_router(api_router)

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0", "db": "connected"}

@app.delete("/api/users/{user_id}/data")
def delete_user_data(user_id: int, include_accounts: bool = False, db: Session = Depends(get_db)):
    deleted_counts: dict = {}

    # Delete in FK-safe order: children first, then parents
    # Null out recurring_group_id on transactions before deleting recurring_groups
    db.query(Transaction).filter(Transaction.user_id == user_id).update(
        {"recurring_group_id": None}, synchronize_session="fetch"
    )
    deleted_counts["transactions"] = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).delete(synchronize_session="fetch")
    deleted_counts["documents"] = db.query(Document).filter(
        Document.user_id == user_id
    ).delete(synchronize_session="fetch")
    deleted_counts["recurring_groups"] = db.query(RecurringGroup).filter(
        RecurringGroup.user_id == user_id
    ).delete(synchronize_session="fetch")
    deleted_counts["budgets"] = db.query(Budget).filter(
        Budget.user_id == user_id
    ).delete(synchronize_session="fetch")
    deleted_counts["goals"] = db.query(Goal).filter(
        Goal.user_id == user_id
    ).delete(synchronize_session="fetch")
    deleted_counts["insights"] = db.query(Insight).filter(
        Insight.user_id == user_id
    ).delete(synchronize_session="fetch")
    deleted_counts["summaries"] = db.query(MonthlySummary).filter(
        MonthlySummary.user_id == user_id
    ).delete(synchronize_session="fetch")
    deleted_counts["chat_messages"] = db.query(ChatMessage).filter(
        ChatMessage.user_id == user_id
    ).delete(synchronize_session="fetch")

    if include_accounts:
        deleted_counts["accounts"] = db.query(Account).filter(
            Account.user_id == user_id
        ).delete(synchronize_session="fetch")

    db.commit()
    return deleted_counts
