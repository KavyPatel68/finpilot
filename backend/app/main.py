from fastapi import FastAPI, Depends, APIRouter, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from collections import defaultdict
import os
import time
from sqlalchemy.orm import Session
from sqlalchemy import text
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

    if settings.DEMO_MODE:
        txn_count = db.query(Transaction).count()
        if txn_count == 0:
            print("DEMO_MODE active and database empty: auto-seeding 6-month synthetic dataset...")
            try:
                from data.seed.synthetic_data import seed_data
                seed_data()
                print("Demo data auto-seeded successfully on startup.")
            except Exception as e:
                print(f"Failed to auto-seed demo data: {e}")

    yield

app = FastAPI(
    title="FinPilot API",
    description="Privacy-First Personal Finance Copilot",
    version="1.0.0",
    lifespan=lifespan
)

# Light in-memory rate limiting (120 req/min per IP)
_ip_request_timestamps = defaultdict(list)
RATE_LIMIT_WINDOW = 60.0  # seconds
RATE_LIMIT_MAX = 120      # requests per window

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and not path.startswith("/api/health"):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        timestamps = _ip_request_timestamps[client_ip]
        cutoff = now - RATE_LIMIT_WINDOW
        _ip_request_timestamps[client_ip] = [t for t in timestamps if t > cutoff]
        if len(_ip_request_timestamps[client_ip]) >= RATE_LIMIT_MAX:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Demo mode rate limit is 120 requests per minute. Please slow down."}
            )
        _ip_request_timestamps[client_ip].append(now)

    return await call_next(request)

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

@api_router.get("/health")
@app.get("/health")
def health(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
    return {
        "status": "ok",
        "version": "1.0.0",
        "db": db_status,
        "demo_mode": settings.DEMO_MODE,
    }

@api_router.get("/demo/status")
def get_demo_status(db: Session = Depends(get_db)):
    count = db.query(Transaction).filter(Transaction.user_id == settings.DEFAULT_USER_ID).count()
    return {
        "demo_mode": settings.DEMO_MODE,
        "transaction_count": count,
        "seeded": count > 0,
    }

@api_router.post("/demo/reset")
def reset_demo_data(user_id: int = 1, db: Session = Depends(get_db)):
    from data.seed.synthetic_data import seed_data
    from app.services.cache_service import invalidate_user_qa_cache
    seed_data()
    invalidate_user_qa_cache(db, user_id=user_id)
    count = db.query(Transaction).filter(Transaction.user_id == user_id).count()
    return {
        "status": "ok",
        "message": f"Demo data reset to initial 6-month seed state ({count} transactions).",
        "transaction_count": count,
    }

@api_router.delete("/users/{user_id}/data")
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

app.include_router(api_router)

# Resolve frontend dist directory for single-service production serving
def resolve_frontend_dist() -> str | None:
    candidates = [
        os.path.abspath(settings.FRONTEND_DIST_DIR),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")),
        os.path.abspath(os.path.join(os.getcwd(), "frontend", "dist")),
        os.path.abspath(os.path.join(os.getcwd(), "dist")),
    ]
    for c in candidates:
        if os.path.isdir(c) and os.path.exists(os.path.join(c, "index.html")):
            return c
    return None

frontend_dist = resolve_frontend_dist()
if frontend_dist:
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Do not hijack API, Docs, or OpenAPI schema routes
        if full_path.startswith(("api/", "api", "docs", "redoc", "openapi.json")):
            raise HTTPException(status_code=404, detail="Not Found")

        candidate_file = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(candidate_file):
            return FileResponse(candidate_file)

        return FileResponse(os.path.join(frontend_dist, "index.html"))
