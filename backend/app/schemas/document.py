from pydantic import BaseModel, ConfigDict
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

class ColumnMappingSchema(BaseModel):
    date_col: Optional[str] = None
    description_col: Optional[str] = None
    debit_col: Optional[str] = None
    credit_col: Optional[str] = None
    amount_col: Optional[str] = None
    balance_col: Optional[str] = None
    direction_col: Optional[str] = None
    reference_col: Optional[str] = None
    confidence: float = 0.0
    needs_confirmation: bool = False
    warnings: list[str] = []
    headers: list[str] = []
    preview_rows: list[dict[str, Any]] = []

class UploadResponse(BaseModel):
    document_id: int
    filename: str
    status: str
    row_count: int
    imported_count: int
    duplicate_count: int
    parse_errors: list[dict]
    mapping_suggestion: Optional[ColumnMappingSchema] = None
    headers: list[str] = []
    preview_rows: list[dict[str, Any]] = []
