from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from app.database import Base
import enum


class FileType(enum.Enum):
    csv = "csv"
    xlsx = "xlsx"
    excel = "excel"   # alias accepted by router
    pdf = "pdf"
    unknown = "unknown"


class DocumentStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    needs_mapping = "needs_mapping"   # low-confidence column detection
    done = "done"
    completed = "completed"           # alias used by router
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
