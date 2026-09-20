from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum, Float, Boolean, UniqueConstraint
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
    # Added in M2: ingestion enrichments
    balance_minor = Column(Integer, nullable=True)    # running balance from statement
    payment_method = Column(String, nullable=True)    # UPI, NEFT, IMPS, ATM, POS, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'account_id', 'date', 'amount_minor', 'raw_description',
                         name='_user_account_date_amount_desc_uc'),
    )
