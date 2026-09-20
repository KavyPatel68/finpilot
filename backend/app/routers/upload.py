import os
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.config import settings
from app.models.document import Document, DocumentStatus, FileType
from app.models.transaction import Transaction, TransactionDirection, CategorySource
from app.schemas.document import UploadResponse, DocumentResponse, ColumnMappingSchema
from app.services.ingestion.parser_csv import parse_file
from app.services.ingestion.parser_pdf import parse_pdf
from app.services.ingestion.deduplicator import deduplicate
from app.services.ingestion.column_detector import ColumnMapping
from app.services.categorization.categorizer import categorize_transactions

router = APIRouter(tags=["upload"])

_DIRECTION_MAP = {
    "income": TransactionDirection.income,
    "expense": TransactionDirection.expense,
}

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    account_id: int = Form(...),
    user_id: int = Form(1),
    pdf_password: str = Form(None),
    db: Session = Depends(get_db)
):
    doc_uuid = str(uuid.uuid4())
    user_dir = os.path.join(settings.UPLOADS_DIR, str(user_id), doc_uuid)
    os.makedirs(user_dir, exist_ok=True)
    
    content = await file.read()
    if settings.DEMO_MODE and len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="In Demo Mode, file uploads are limited to 2 MB. Please upload a smaller sample or click 'Load Sample Statement'."
        )
    file_path = os.path.join(user_dir, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)

    ext = (file.filename or "").rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        file_type = FileType.pdf
    elif ext in ('xls', 'xlsx'):
        file_type = FileType.xlsx
    else:
        file_type = FileType.csv

    doc = Document(
        user_id=user_id,
        account_id=account_id,
        filename=file.filename,
        file_path=file_path,
        file_type=file_type,
        status=DocumentStatus.processing,
        parse_errors=[]
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        if file_type == FileType.pdf:
            parse_result = parse_pdf(file_path, password=pdf_password)
        else:
            ftype = 'xlsx' if file_type == FileType.xlsx else 'csv'
            parse_result = parse_file(file_path, file_type=ftype)
    except ValueError as e:
        if 'password' in str(e).lower() or 'encrypted' in str(e).lower():
            doc.status = DocumentStatus.error
            doc.parse_errors = [{"row": 0, "message": str(e)}]
            db.commit()
            return UploadResponse(
                document_id=doc.id,
                filename=doc.filename,
                status='error',
                row_count=0,
                imported_count=0,
                duplicate_count=0,
                parse_errors=doc.parse_errors,
            )
        raise

    total_rows = parse_result.total_rows if parse_result.total_rows > 0 else (len(parse_result.transactions) + len(parse_result.errors))

    mapping_suggestion = None
    if parse_result.mapping and parse_result.mapping.needs_confirmation:
        doc.status = DocumentStatus.needs_mapping
        doc.row_count = total_rows
        doc.parse_errors = [{"row": err.row, "message": err.reason} for err in parse_result.errors]
        db.commit()

        mapping_suggestion = ColumnMappingSchema(
            date_col=parse_result.mapping.date_col,
            description_col=parse_result.mapping.description_col,
            debit_col=parse_result.mapping.debit_col,
            credit_col=parse_result.mapping.credit_col,
            amount_col=parse_result.mapping.amount_col,
            balance_col=parse_result.mapping.balance_col,
            direction_col=parse_result.mapping.direction_col,
            confidence=parse_result.mapping.confidence,
            needs_confirmation=parse_result.mapping.needs_confirmation,
            warnings=parse_result.mapping.warnings,
            headers=parse_result.headers or parse_result.mapping.headers,
            preview_rows=parse_result.preview_rows or parse_result.mapping.preview_rows,
        )

        return UploadResponse(
            document_id=doc.id,
            filename=doc.filename,
            status='needs_mapping',
            row_count=total_rows,
            imported_count=0,
            duplicate_count=0,
            parse_errors=doc.parse_errors,
            mapping_suggestion=mapping_suggestion,
            headers=parse_result.headers or parse_result.mapping.headers,
            preview_rows=parse_result.preview_rows or parse_result.mapping.preview_rows,
        )

    if parse_result.errors and len(parse_result.errors) > 0 and len(parse_result.transactions) == 0:
        doc.status = DocumentStatus.error
        doc.row_count = total_rows
        doc.parse_errors = [{"row": err.row, "message": err.reason} for err in parse_result.errors]
        db.commit()
        return UploadResponse(
            document_id=doc.id,
            filename=doc.filename,
            status='error',
            row_count=total_rows,
            imported_count=0,
            duplicate_count=0,
            parse_errors=doc.parse_errors,
            headers=parse_result.headers,
            preview_rows=parse_result.preview_rows,
        )

    dedup_result = deduplicate(parse_result.transactions, db, user_id, account_id)

    new_txns: list[Transaction] = []
    for txn_parsed in dedup_result.to_insert:
        txn = Transaction(
            user_id=user_id,
            account_id=account_id,
            document_id=doc.id,
            date=txn_parsed.date,
            amount_minor=txn_parsed.amount_minor,
            direction=_DIRECTION_MAP[txn_parsed.direction],
            balance_minor=txn_parsed.balance_minor,
            raw_description=txn_parsed.raw_description,
            merchant_normalized=txn_parsed.merchant_hint,
            payment_method=txn_parsed.payment_method,
            category='Other',
            category_source=CategorySource.rule,
        )
        db.add(txn)
        new_txns.append(txn)

    db.flush()

    # Automatically categorize newly ingested transactions
    if new_txns:
        await categorize_transactions(new_txns, db, user_id=user_id)

    doc.status = DocumentStatus.done
    doc.row_count = total_rows
    doc.imported_count = len(dedup_result.to_insert)
    doc.duplicate_count = dedup_result.duplicate_count
    doc.parse_errors = [{"row": err.row, "message": err.reason} for err in parse_result.errors]
    doc.processed_at = datetime.now(timezone.utc)

    db.commit()

    # Invalidate cached Q&A on upload
    from app.services.cache_service import invalidate_user_qa_cache
    invalidate_user_qa_cache(db, user_id=user_id)

    return UploadResponse(
        document_id=doc.id,
        filename=doc.filename,
        status='done',
        row_count=doc.row_count,
        imported_count=doc.imported_count,
        duplicate_count=doc.duplicate_count,
        parse_errors=doc.parse_errors,
        headers=parse_result.headers,
        preview_rows=parse_result.preview_rows,
    )

@router.post("/documents/{doc_id}/confirm-mapping", response_model=UploadResponse)
async def confirm_mapping(
    doc_id: int,
    mapping: ColumnMappingSchema,
    db: Session = Depends(get_db)
):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    col_map = ColumnMapping(
        date_col=mapping.date_col,
        description_col=mapping.description_col,
        debit_col=mapping.debit_col,
        credit_col=mapping.credit_col,
        amount_col=mapping.amount_col,
        balance_col=mapping.balance_col,
        direction_col=mapping.direction_col,
        confidence=mapping.confidence,
        needs_confirmation=False,
        warnings=mapping.warnings
    )

    if doc.file_type == FileType.pdf:
        parse_result = parse_pdf(doc.file_path, mapping=col_map)
    else:
        ftype = 'xlsx' if doc.file_type == FileType.xlsx else 'csv'
        parse_result = parse_file(doc.file_path, mapping=col_map, file_type=ftype)

    dedup_result = deduplicate(parse_result.transactions, db, doc.user_id, doc.account_id)

    new_txns: list[Transaction] = []
    for txn_parsed in dedup_result.to_insert:
        txn = Transaction(
            user_id=doc.user_id,
            account_id=doc.account_id,
            document_id=doc.id,
            date=txn_parsed.date,
            amount_minor=txn_parsed.amount_minor,
            direction=_DIRECTION_MAP[txn_parsed.direction],
            balance_minor=txn_parsed.balance_minor,
            raw_description=txn_parsed.raw_description,
            merchant_normalized=txn_parsed.merchant_hint,
            payment_method=txn_parsed.payment_method,
            category='Other',
            category_source=CategorySource.rule,
        )
        db.add(txn)
        new_txns.append(txn)

    db.flush()

    if new_txns:
        await categorize_transactions(new_txns, db, user_id=doc.user_id)

    total_rows = parse_result.total_rows if parse_result.total_rows > 0 else (len(parse_result.transactions) + len(parse_result.errors))
    doc.status = DocumentStatus.done
    doc.row_count = total_rows
    doc.imported_count = len(dedup_result.to_insert)
    doc.duplicate_count = dedup_result.duplicate_count
    doc.parse_errors = [{"row": err.row, "message": err.reason} for err in parse_result.errors]
    doc.processed_at = datetime.now(timezone.utc)

    db.commit()

    from app.services.cache_service import invalidate_user_qa_cache
    invalidate_user_qa_cache(db, user_id=doc.user_id)
    
    return UploadResponse(
        document_id=doc.id,
        filename=doc.filename,
        status='done',
        row_count=doc.row_count,
        imported_count=doc.imported_count,
        duplicate_count=doc.duplicate_count,
        parse_errors=doc.parse_errors,
        headers=parse_result.headers,
        preview_rows=parse_result.preview_rows,
    )

@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(user_id: int, db: Session = Depends(get_db)):
    docs = db.scalars(select(Document).where(Document.user_id == user_id)).all()
    return docs

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.query(Transaction).filter(Transaction.document_id == doc_id).delete()
    db.delete(doc)
    db.commit()
    return {"status": "ok"}


@router.post("/upload/seed-demo")
def seed_demo_data(
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Loads 6 months of deterministic synthetic data (152 transactions) with planted scenarios."""
    from data.seed.synthetic_data import seed_data
    from app.services.cache_service import invalidate_user_qa_cache
    from sqlalchemy import select, func

    seed_data()

    # Ensure a Document entry exists so it appears in Statement History
    existing_doc = db.scalar(
        select(Document).where(
            Document.user_id == user_id,
            Document.filename == "synthetic_statements_apr_sep_2024.csv"
        )
    )
    if not existing_doc:
        doc = Document(
            user_id=user_id,
            account_id=1,
            filename="synthetic_statements_apr_sep_2024.csv",
            file_path="data/seed/synthetic_data.py",
            file_type=FileType.csv,
            status=DocumentStatus.done,
            row_count=152,
            imported_count=152,
            duplicate_count=0,
            parse_errors=[],
            processed_at=datetime.now(timezone.utc),
        )
        db.add(doc)
        db.commit()

    invalidate_user_qa_cache(db, user_id=user_id)

    txn_count = db.scalar(
        select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
    ) or 152

    return {
        "status": "ok",
        "imported_count": txn_count,
        "months_covered": 6,
        "message": f"Demo data loaded successfully: {txn_count} transactions across 6 months (Apr - Sep 2024).",
    }


@router.post("/upload/sample-statement", response_model=UploadResponse)
async def upload_sample_statement(
    account_id: int = Query(1),
    user_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Imports the bundled sample bank statement (170 rows, HDFC CSV format) without requiring user to provide a file."""
    from app.models.account import Account, AccountType
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        acc = Account(id=account_id, user_id=user_id, name="HDFC Savings", type=AccountType.bank, currency="INR")
        db.add(acc)
        db.commit()

    sample_src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "sample_statement.csv")
    if not os.path.exists(sample_src):
        raise HTTPException(status_code=404, detail="Bundled sample statement file not found.")

    doc_uuid = str(uuid.uuid4())
    user_dir = os.path.join(settings.UPLOADS_DIR, str(user_id), doc_uuid)
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, "sample_hdfc_statement.csv")
    
    with open(sample_src, "rb") as src, open(file_path, "wb") as dst:
        dst.write(src.read())

    doc = Document(
        user_id=user_id,
        account_id=account_id,
        filename="sample_hdfc_statement.csv",
        file_path=file_path,
        file_type=FileType.csv,
        status=DocumentStatus.processing,
        parse_errors=[]
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    parse_result = parse_file(file_path, file_type='csv')
    total_rows = parse_result.total_rows if parse_result.total_rows > 0 else (len(parse_result.transactions) + len(parse_result.errors))

    dedup_result = deduplicate(parse_result.transactions, db, user_id, account_id)

    new_txns: list[Transaction] = []
    for txn_parsed in dedup_result.to_insert:
        txn = Transaction(
            user_id=user_id,
            account_id=account_id,
            document_id=doc.id,
            date=txn_parsed.date,
            amount_minor=txn_parsed.amount_minor,
            direction=_DIRECTION_MAP[txn_parsed.direction],
            balance_minor=txn_parsed.balance_minor,
            raw_description=txn_parsed.raw_description,
            merchant_normalized=txn_parsed.merchant_hint,
            payment_method=txn_parsed.payment_method,
            category='Other',
            category_source=CategorySource.rule,
        )
        db.add(txn)
        new_txns.append(txn)

    db.flush()

    if new_txns:
        await categorize_transactions(new_txns, db, user_id=user_id)

    doc.status = DocumentStatus.done
    doc.row_count = total_rows
    doc.imported_count = len(dedup_result.to_insert)
    doc.duplicate_count = dedup_result.duplicate_count
    doc.parse_errors = [{"row": err.row, "message": err.reason} for err in parse_result.errors]
    doc.processed_at = datetime.now(timezone.utc)

    db.commit()

    return UploadResponse(
        document_id=doc.id,
        filename=doc.filename,
        status='done',
        row_count=total_rows,
        imported_count=len(dedup_result.to_insert),
        duplicate_count=dedup_result.duplicate_count,
        parse_errors=doc.parse_errors,
        headers=parse_result.headers,
        preview_rows=parse_result.preview_rows,
    )

