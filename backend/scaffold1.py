import os
import json

base_dir = r"c:\Users\patel\OneDrive\Desktop\ai agent\finpilot\backend"

directories = [
    "app",
    "app/models",
    "app/schemas",
    "app/routers",
    "app/services",
    "app/services/ingestion",
    "app/services/categorization",
    "app/services/analytics",
    "app/services/agent",
    "app/services/report",
    "app/utils",
    "alembic",
    "alembic/versions",
    "data/seed",
    "data/uploads",
    "tests"
]

for d in directories:
    os.makedirs(os.path.join(base_dir, d), exist_ok=True)

files = {}

# requirements.txt
files["requirements.txt"] = """fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.36
alembic==1.13.3
pydantic==2.9.2
pydantic-settings==2.5.2
anthropic==0.34.2
pandas==2.2.3
openpyxl==3.1.5
pdfplumber==0.11.4
python-multipart==0.0.12
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
python-dotenv==1.0.1
typing-extensions==4.12.2
reportlab==4.2.5
"""

# .env.example
files[".env.example"] = """ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-sonnet-4-5
ANTHROPIC_MODEL_FAST=claude-haiku-4-5-20251001
DATABASE_URL=sqlite:///./data/finpilot.db
UPLOADS_DIR=./data/uploads
DEFAULT_CURRENCY=INR
CORS_ORIGINS=["http://localhost:5173"]
USE_OCR=false
"""

files["app/__init__.py"] = ""
files["app/models/__init__.py"] = ""
files["app/schemas/__init__.py"] = ""
files["app/routers/__init__.py"] = ""
files["app/services/__init__.py"] = ""
files["app/services/ingestion/__init__.py"] = ""
files["app/services/categorization/__init__.py"] = ""
files["app/services/analytics/__init__.py"] = ""
files["app/services/agent/__init__.py"] = ""
files["app/services/report/__init__.py"] = ""
files["app/utils/__init__.py"] = ""
files["tests/__init__.py"] = ""
files["data/uploads/.gitkeep"] = ""

files["app/config.py"] = """from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/finpilot.db"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"
    ANTHROPIC_MODEL_FAST: str = "claude-haiku-4-5-20251001"
    UPLOADS_DIR: str = "./data/uploads"
    DEFAULT_CURRENCY: str = "INR"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    DEFAULT_USER_ID: int = 1

settings = Settings()
"""

files["app/database.py"] = """from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
"""

files["app/models/user.py"] = """from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=True)
    display_name = Column(String, nullable=True)
    currency = Column(String, default="INR")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""

files["app/models/account.py"] = """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum

class AccountType(enum.Enum):
    bank = "bank"
    card = "card"
    cash = "cash"
    other = "other"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(Enum(AccountType), nullable=False)
    currency = Column(String, default="INR")
    account_number_masked = Column(String, nullable=True)
    institution = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""

files["app/models/document.py"] = """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from app.database import Base
import enum

class FileType(enum.Enum):
    csv = "csv"
    xlsx = "xlsx"
    pdf = "pdf"
    unknown = "unknown"

class DocumentStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.pending)
    parse_errors = Column(JSON, nullable=True)
    pdf_password = Column(String, nullable=True)
    row_count = Column(Integer, default=0)
    imported_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
"""

files["app/models/transaction.py"] = """from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum, Float, Boolean, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base
import enum

class TransactionDirection(enum.Enum):
    income = "income"
    expense = "expense"

class CategorySource(enum.Enum):
    rule = "rule"
    llm = "llm"
    user = "user"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    date = Column(Date, nullable=False)
    raw_description = Column(String, nullable=False)
    merchant_normalized = Column(String, nullable=True)
    amount_minor = Column(Integer, nullable=False)
    direction = Column(Enum(TransactionDirection), nullable=False)
    category = Column(String, nullable=True)
    subcategory = Column(String, nullable=True)
    category_source = Column(Enum(CategorySource), nullable=True)
    confidence = Column(Float, nullable=True)
    is_recurring = Column(Boolean, default=False)
    recurring_group_id = Column(Integer, ForeignKey("recurring_groups.id"), nullable=True)
    is_transfer = Column(Boolean, default=False)
    is_anomaly = Column(Boolean, default=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'account_id', 'date', 'amount_minor', 'raw_description', name='_user_account_date_amount_desc_uc'),
    )
"""

files["app/models/recurring.py"] = """from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum

class RecurringFrequency(enum.Enum):
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"

class RecurringStatus(enum.Enum):
    active = "active"
    possibly_cancelled = "possibly_cancelled"
    cancelled = "cancelled"

class RecurringType(enum.Enum):
    subscription = "subscription"
    bill = "bill"
    emi = "emi"
    other = "other"

class RecurringGroup(Base):
    __tablename__ = "recurring_groups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    merchant = Column(String, nullable=False)
    avg_amount_minor = Column(Integer, nullable=False)
    frequency = Column(Enum(RecurringFrequency), nullable=False)
    next_expected_date = Column(Date, nullable=True)
    last_seen = Column(Date, nullable=False)
    status = Column(Enum(RecurringStatus), nullable=False)
    type = Column(Enum(RecurringType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
"""

files["app/models/budget.py"] = """from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String, nullable=False)
    monthly_limit_minor = Column(Integer, nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""

files["app/models/goal.py"] = """from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
from app.database import Base
import enum

class GoalType(enum.Enum):
    emergency_fund = "emergency_fund"
    purchase = "purchase"
    custom = "custom"

class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(Enum(GoalType), nullable=False)
    target_amount_minor = Column(Integer, nullable=False)
    current_amount_minor = Column(Integer, default=0)
    target_date = Column(Date, nullable=True)
    monthly_contribution_planned_minor = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
"""

files["app/models/insight.py"] = """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON
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
"""

files["app/models/summary.py"] = """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base

class MonthlySummary(Base):
    __tablename__ = "monthly_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month = Column(String, nullable=False) # Format YYYY-MM
    payload = Column(JSON, nullable=False)
    generated_text = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""

files["app/models/chat.py"] = """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from app.database import Base
import enum

class ChatRole(enum.Enum):
    user = "user"
    assistant = "assistant"
    tool = "tool"

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(ChatRole), nullable=False)
    content = Column(String, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    tool_results = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""

# SCHEMAS
files["app/schemas/user.py"] = """from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    currency: str = "INR"

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
"""

files["app/schemas/account.py"] = """from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.account import AccountType

class AccountBase(BaseModel):
    name: str
    type: AccountType
    currency: str = "INR"
    account_number_masked: Optional[str] = None
    institution: Optional[str] = None

class AccountCreate(AccountBase):
    user_id: int

class AccountResponse(AccountBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
"""

files["app/schemas/document.py"] = """from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models.document import FileType, DocumentStatus

class DocumentBase(BaseModel):
    account_id: Optional[int] = None
    filename: str
    file_path: str
    file_type: FileType
    status: DocumentStatus = DocumentStatus.pending
    parse_errors: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    imported_count: int = 0
    duplicate_count: int = 0

class DocumentCreate(DocumentBase):
    user_id: int
    pdf_password: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
"""

files["app/schemas/transaction.py"] = """from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime, date
from typing import Optional
from app.models.transaction import TransactionDirection, CategorySource
from app.utils.amount import format_amount

class TransactionBase(BaseModel):
    account_id: int
    document_id: Optional[int] = None
    date: date
    raw_description: str
    merchant_normalized: Optional[str] = None
    amount_minor: int
    direction: TransactionDirection
    category: Optional[str] = None
    subcategory: Optional[str] = None
    category_source: Optional[CategorySource] = None
    confidence: Optional[float] = None
    is_recurring: bool = False
    recurring_group_id: Optional[int] = None
    is_transfer: bool = False
    is_anomaly: bool = False
    notes: Optional[str] = None

    @computed_field
    @property
    def amount_display(self) -> str:
        return format_amount(self.amount_minor)

class TransactionCreate(TransactionBase):
    user_id: int

class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
"""

files["app/schemas/recurring.py"] = """from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime, date
from typing import Optional
from app.models.recurring import RecurringFrequency, RecurringStatus, RecurringType
from app.utils.amount import format_amount

class RecurringGroupBase(BaseModel):
    merchant: str
    avg_amount_minor: int
    frequency: RecurringFrequency
    next_expected_date: Optional[date] = None
    last_seen: date
    status: RecurringStatus
    type: RecurringType

    @computed_field
    @property
    def avg_amount_display(self) -> str:
        return format_amount(self.avg_amount_minor)

class RecurringGroupCreate(RecurringGroupBase):
    user_id: int

class RecurringGroupResponse(RecurringGroupBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
"""

files["app/schemas/budget.py"] = """from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime, date
from typing import Optional
from app.utils.amount import format_amount

class BudgetBase(BaseModel):
    category: str
    monthly_limit_minor: int
    effective_from: date
    effective_to: Optional[date] = None

    @computed_field
    @property
    def monthly_limit_display(self) -> str:
        return format_amount(self.monthly_limit_minor)

class BudgetCreate(BudgetBase):
    user_id: int

class BudgetResponse(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
"""

files["app/schemas/goal.py"] = """from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime, date
from typing import Optional
from app.models.goal import GoalType
from app.utils.amount import format_amount

class GoalBase(BaseModel):
    name: str
    type: GoalType
    target_amount_minor: int
    current_amount_minor: int = 0
    target_date: Optional[date] = None
    monthly_contribution_planned_minor: Optional[int] = None
    is_active: bool = True

    @computed_field
    @property
    def target_amount_display(self) -> str:
        return format_amount(self.target_amount_minor)
    
    @computed_field
    @property
    def current_amount_display(self) -> str:
        return format_amount(self.current_amount_minor)

class GoalCreate(GoalBase):
    user_id: int

class GoalResponse(GoalBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
"""

files["app/schemas/insight.py"] = """from pydantic import BaseModel, ConfigDict
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
"""

files["app/schemas/summary.py"] = """from pydantic import BaseModel, ConfigDict
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
"""

files["app/schemas/chat.py"] = """from pydantic import BaseModel, ConfigDict
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
"""

for path, content in files.items():
    with open(os.path.join(base_dir, path), "w", encoding="utf-8") as f:
        f.write(content)
