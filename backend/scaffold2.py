import os

base_dir = r"c:\Users\patel\OneDrive\Desktop\ai agent\finpilot\backend"
files = {}

# ROUTERS
router_template = """from fastapi import APIRouter

router = APIRouter(prefix="/{prefix}", tags=["{tags}"])

@router.get("/")
def get_{prefix}():
    # stub
    return {{"status": "not implemented"}}
"""

routers = [
    ("upload", "uploads"),
    ("transactions", "transactions"),
    ("summary", "summaries"),
    ("subscriptions", "subscriptions"),
    ("budgets", "budgets"),
    ("goals", "goals"),
    ("insights", "insights"),
    ("chat", "chat"),
    ("reports", "reports")
]

for prefix, tags in routers:
    files[f"app/routers/{prefix}.py"] = router_template.format(prefix=prefix, tags=tags)


# SERVICES
files["app/services/llm_provider.py"] = """from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import anthropic
from app.config import settings
from abc import ABC, abstractmethod

@dataclass
class LLMMessage:
    role: str
    content: str

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]

class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: List[LLMMessage], model: Optional[str] = None, system: Optional[str] = None, max_tokens: int = 1024) -> LLMResponse:
        pass

    @abstractmethod
    async def complete_with_tools(self, messages: List[LLMMessage], tools: List[Dict[str, Any]], model: Optional[str] = None, system: Optional[str] = None, max_tokens: int = 4096) -> LLMResponse:
        pass

class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(self, messages: List[LLMMessage], model: Optional[str] = None, system: Optional[str] = None, max_tokens: int = 1024) -> LLMResponse:
        model_name = model or settings.ANTHROPIC_MODEL
        # guardrails for account numbers should be applied here
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        response = await self.client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            messages=formatted_messages,
            system=system or ""
        )
        return LLMResponse(content=response.content[0].text, model=model_name, usage={"input": response.usage.input_tokens, "output": response.usage.output_tokens})

    async def complete_with_tools(self, messages: List[LLMMessage], tools: List[Dict[str, Any]], model: Optional[str] = None, system: Optional[str] = None, max_tokens: int = 4096) -> LLMResponse:
        model_name = model or settings.ANTHROPIC_MODEL
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        response = await self.client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            messages=formatted_messages,
            system=system or "",
            tools=tools
        )
        # simplistic parsing for stub
        return LLMResponse(content=str(response.content), model=model_name, usage={"input": response.usage.input_tokens, "output": response.usage.output_tokens})

class FakeLLMProvider(BaseLLMProvider):
    async def complete(self, messages: List[LLMMessage], model: Optional[str] = None, system: Optional[str] = None, max_tokens: int = 1024) -> LLMResponse:
        return LLMResponse(content="Canned response", model="fake-model", usage={"input": 10, "output": 10})

    async def complete_with_tools(self, messages: List[LLMMessage], tools: List[Dict[str, Any]], model: Optional[str] = None, system: Optional[str] = None, max_tokens: int = 4096) -> LLMResponse:
        return LLMResponse(content="Canned response with tools", model="fake-model", usage={"input": 10, "output": 10})

def get_llm_provider() -> BaseLLMProvider:
    return AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY)
"""

files["app/services/categorization/taxonomy.py"] = """CATEGORIES = [
    "Income", "Housing/Rent", "Utilities", "Groceries", "Dining",
    "Transport", "Fuel", "Shopping", "Subscriptions", "Entertainment",
    "Health", "Education", "Insurance", "EMI/Loans", "Travel",
    "Transfers", "Fees/Charges", "Other"
]
"""

# UTILS
files["app/utils/amount.py"] = """from decimal import Decimal, ROUND_HALF_UP

MINOR_UNIT_MAP = {"INR": 100, "USD": 100, "EUR": 100, "GBP": 100}

def to_minor(amount: Decimal, currency: str = "INR") -> int:
    \"\"\"Convert decimal amount to minor units (integer). Uses Decimal arithmetic.\"\"\"
    factor = MINOR_UNIT_MAP.get(currency.upper(), 100)
    return int((amount * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def from_minor(minor: int, currency: str = "INR") -> Decimal:
    \"\"\"Convert minor units back to Decimal.\"\"\"
    factor = MINOR_UNIT_MAP.get(currency.upper(), 100)
    return Decimal(minor) / Decimal(factor)

def format_amount(minor: int, currency: str = "INR") -> str:
    \"\"\"Format as ₹1,23,456.78 for INR or $1,234.56 for others.\"\"\"
    val = float(from_minor(minor, currency))
    if currency.upper() == "INR":
        return f"₹{val:,.2f}" # simplifed for now
    elif currency.upper() == "USD":
        return f"${val:,.2f}"
    return f"{val:,.2f} {currency}"
"""

files["app/utils/number_formats.py"] = """from decimal import Decimal
import re

def parse_indian_number(s: str) -> Decimal:
    \"\"\"Parse '1,23,456.78' or '1,23,456' removing Indian-style commas.\"\"\"
    s = re.sub(r"[^\d.\-]", "", s.replace(",", ""))
    return Decimal(s) if s else Decimal("0")
"""

files["app/utils/date_utils.py"] = """from datetime import date, datetime
from typing import Tuple

def parse_date(s: str) -> date:
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%b %d %Y", "%d/%m/%y"]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not parse date {s}")

def month_str(d: date) -> str:
    return d.strftime("%Y-%m")

def resolve_relative_period(expr: str, anchor: date) -> Tuple[date, date]:
    # simplified stub for resolve_relative_period
    return anchor, anchor
"""

# MAIN APP
files["app/main.py"] = """from fastapi import FastAPI, Depends, APIRouter
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
from app.routers import upload, transactions, summary, subscriptions, budgets, goals, insights, chat, reports

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
app.include_router(api_router)

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0", "db": "connected"}

@app.delete("/api/users/{user_id}/data")
def delete_user_data(user_id: int, include_accounts: bool = False, db: Session = Depends(get_db)):
    deleted_counts = {}
    
    deleted_counts["transactions"] = db.query(Transaction).filter(Transaction.user_id == user_id).delete()
    deleted_counts["documents"] = db.query(Document).filter(Document.user_id == user_id).delete()
    deleted_counts["budgets"] = db.query(Budget).filter(Budget.user_id == user_id).delete()
    deleted_counts["goals"] = db.query(Goal).filter(Goal.user_id == user_id).delete()
    deleted_counts["insights"] = db.query(Insight).filter(Insight.user_id == user_id).delete()
    deleted_counts["summaries"] = db.query(MonthlySummary).filter(MonthlySummary.user_id == user_id).delete()
    deleted_counts["chat_messages"] = db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
    deleted_counts["recurring_groups"] = db.query(RecurringGroup).filter(RecurringGroup.user_id == user_id).delete()
    
    if include_accounts:
        deleted_counts["accounts"] = db.query(Account).filter(Account.user_id == user_id).delete()
        
    db.commit()
    return deleted_counts
"""

for path, content in files.items():
    with open(os.path.join(base_dir, path), "w", encoding="utf-8") as f:
        f.write(content)
