from typing import NamedTuple
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.transaction import Transaction
from app.services.ingestion.parser_csv import ParsedTransaction

class DeduplicationResult(NamedTuple):
    to_insert: list[ParsedTransaction]
    duplicates: list[ParsedTransaction]
    duplicate_count: int

def deduplicate(
    parsed: list[ParsedTransaction],
    db: Session,
    user_id: int,
    account_id: int,
) -> DeduplicationResult:
    """Remove transactions already in DB and within-batch duplicates."""
    to_insert = []
    duplicates = []
    
    seen_keys = set()
    
    # 1. Within-batch dedup
    batch_non_duplicates = []
    for txn in parsed:
        key = (txn.date, txn.amount_minor, txn.raw_description[:100])
        if key in seen_keys:
            duplicates.append(txn)
        else:
            seen_keys.add(key)
            batch_non_duplicates.append(txn)
            
    if not batch_non_duplicates:
        return DeduplicationResult(
            to_insert=[],
            duplicates=duplicates,
            duplicate_count=len(duplicates)
        )

    # 2. DB dedup
    if db is not None:
        min_date = min(t.date for t in batch_non_duplicates)
        max_date = max(t.date for t in batch_non_duplicates)
        
        existing_txns = db.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.account_id == account_id,
                Transaction.date >= min_date,
                Transaction.date <= max_date
            )
        ).all()
        
        existing_keys = {
            (t.date, t.amount_minor, (t.raw_description or '')[:100])
            for t in existing_txns
        }
        
        for txn in batch_non_duplicates:
            key = (txn.date, txn.amount_minor, txn.raw_description[:100])
            if key in existing_keys:
                duplicates.append(txn)
            else:
                to_insert.append(txn)
    else:
        to_insert = batch_non_duplicates

    return DeduplicationResult(
        to_insert=to_insert,
        duplicates=duplicates,
        duplicate_count=len(duplicates)
    )
