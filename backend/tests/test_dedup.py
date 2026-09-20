from datetime import date
from app.services.ingestion.deduplicator import deduplicate
from app.services.ingestion.parser_csv import ParsedTransaction

def test_within_batch_dedup():
    txns = [
        ParsedTransaction(date=date(2024,4,1), raw_description='Salary', amount_minor=8500000, direction='income'),
        ParsedTransaction(date=date(2024,4,1), raw_description='Salary', amount_minor=8500000, direction='income'),  # dup
    ]
    result = deduplicate(txns, db=None, user_id=1, account_id=1)
    assert len(result.to_insert) == 1
    assert result.duplicate_count == 1

def test_unique_transactions_not_duped():
    txns = [
        ParsedTransaction(date=date(2024,4,1), raw_description='Salary', amount_minor=8500000, direction='income'),
        ParsedTransaction(date=date(2024,4,5), raw_description='Rent', amount_minor=2200000, direction='expense'),
    ]
    result = deduplicate(txns, db=None, user_id=1, account_id=1)
    assert len(result.to_insert) == 2
    assert result.duplicate_count == 0
