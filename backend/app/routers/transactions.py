import math
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, desc, asc

from app.database import get_db
from app.models.transaction import Transaction, TransactionDirection, CategorySource
from app.schemas.transaction import (
    TransactionResponse,
    TransactionUpdate,
    TransactionListResponse,
)
from app.services.categorization.taxonomy import CATEGORIES
from app.services.categorization.rule_engine import add_user_rule
from app.services.categorization.categorizer import categorize_transactions

router = APIRouter(tags=["transactions"])


@router.get("/categories", response_model=List[str])
def list_categories():
    """Returns the standardized 18-category financial taxonomy."""
    return CATEGORIES


@router.get("/transactions", response_model=TransactionListResponse)
def list_transactions(
    user_id: int = Query(1, description="User ID"),
    account_id: Optional[int] = None,
    category: Optional[str] = None,
    direction: Optional[TransactionDirection] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    is_recurring: Optional[bool] = None,
    is_transfer: Optional[bool] = None,
    is_anomaly: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("date"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
):
    query = select(Transaction).where(Transaction.user_id == user_id)

    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if category is not None:
        query = query.where(Transaction.category == category)
    if direction is not None:
        query = query.where(Transaction.direction == direction)
    if start_date is not None:
        query = query.where(Transaction.date >= start_date)
    if end_date is not None:
        query = query.where(Transaction.date <= end_date)
    if is_recurring is not None:
        query = query.where(Transaction.is_recurring == is_recurring)
    if is_transfer is not None:
        query = query.where(Transaction.is_transfer == is_transfer)
    if is_anomaly is not None:
        query = query.where(Transaction.is_anomaly == is_anomaly)

    if search:
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Transaction.raw_description).like(term),
                func.lower(Transaction.merchant_normalized).like(term),
                func.lower(Transaction.notes).like(term),
            )
        )

    # Count total matching rows
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    # Sorting
    sort_col = Transaction.date if sort_by == "date" else Transaction.amount_minor
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_col), asc(Transaction.id))
    else:
        query = query.order_by(desc(sort_col), desc(Transaction.id))

    # Pagination
    offset = (page - 1) * page_size
    items = db.scalars(query.offset(offset).limit(page_size)).all()

    total_pages = max(1, math.ceil(total / page_size))

    return TransactionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    txn = db.get(Transaction, transaction_id)
    if not txn or txn.user_id != user_id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.patch("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    update_data: TransactionUpdate,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    txn = db.get(Transaction, transaction_id)
    if not txn or txn.user_id != user_id:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if update_data.category is not None:
        cat = update_data.category
        if cat not in CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category '{cat}'. Allowed categories: {CATEGORIES}",
            )
        txn.category = cat
        txn.category_source = CategorySource.user
        txn.confidence = 1.0

        # Auto-create user rule for future uploads if requested
        if update_data.create_rule:
            rule_keyword = (
                txn.merchant_normalized
                or txn.raw_description.split("/")[0].strip()
                or txn.raw_description.strip()
            )
            if rule_keyword and len(rule_keyword) >= 3:
                add_user_rule(
                    user_id=txn.user_id,
                    keyword=rule_keyword,
                    category=cat,
                    subcategory=update_data.subcategory or txn.subcategory,
                )

        # Clear Q&A cache on category change
        from app.services.cache_service import invalidate_user_qa_cache
        invalidate_user_qa_cache(db, user_id=user_id)

    if update_data.subcategory is not None:
        txn.subcategory = update_data.subcategory
    if update_data.notes is not None:
        txn.notes = update_data.notes
    if update_data.is_transfer is not None:
        txn.is_transfer = update_data.is_transfer
    if update_data.merchant_normalized is not None:
        txn.merchant_normalized = update_data.merchant_normalized

    db.commit()
    db.refresh(txn)
    return txn


@router.post("/transactions/{transaction_id}/category", response_model=TransactionResponse)
def set_transaction_category(
    transaction_id: int,
    update_data: TransactionUpdate,
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Convenience endpoint to quickly update category and optionally teach the rule engine."""
    return update_transaction(
        transaction_id=transaction_id,
        update_data=update_data,
        user_id=user_id,
        db=db,
    )


@router.post("/transactions/categorize-pending")
async def categorize_pending_transactions(
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Categorizes all unclassified transactions for the given user."""
    pending = (
        db.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                or_(
                    Transaction.category.is_(None),
                    Transaction.category == "Other",
                ),
                Transaction.category_source != CategorySource.user,
            )
        ).all()
    )

    if not pending:
        return {"categorized_count": 0, "message": "No pending transactions found"}

    await categorize_transactions(pending, db, user_id=user_id)
    return {
        "categorized_count": len(pending),
        "message": f"Successfully processed {len(pending)} transactions",
    }
