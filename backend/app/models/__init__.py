# Import all models to ensure they are registered on Base.metadata.
# This file must be imported before any call to Base.metadata.create_all()
# or SQLAlchemy relationship resolution.
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.document import Document, DocumentStatus, FileType
from app.models.transaction import Transaction, TransactionDirection, CategorySource
from app.models.recurring import RecurringGroup, RecurringFrequency, RecurringStatus, RecurringType
from app.models.budget import Budget
from app.models.goal import Goal, GoalType
from app.models.insight import Insight, InsightSeverity
from app.models.summary import MonthlySummary
from app.models.chat import ChatMessage, ChatRole
from app.models.ai_cache import AICache
from app.models.ai_usage import AIUsageLog

__all__ = [
    "User",
    "Account", "AccountType",
    "Document", "DocumentStatus", "FileType",
    "Transaction", "TransactionDirection", "CategorySource",
    "RecurringGroup", "RecurringFrequency", "RecurringStatus", "RecurringType",
    "Budget",
    "Goal", "GoalType",
    "Insight", "InsightSeverity",
    "MonthlySummary",
    "ChatMessage", "ChatRole",
    "AICache",
    "AIUsageLog",
]
