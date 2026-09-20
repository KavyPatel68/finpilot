from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, CategorySource
from app.services.llm_provider import BaseLLMProvider, get_llm_provider
from app.services.categorization.rule_engine import match_rule
from app.services.categorization.llm_categorizer import categorize_batch_with_llm


async def categorize_transactions(
    transactions: List[Transaction],
    db: Session,
    llm_provider: Optional[BaseLLMProvider] = None,
    user_id: int = 1,
) -> List[Transaction]:
    """Unified two-tier categorization engine:

    1. Tier 1: Regex & keyword rules (instant, 100% confidence, free).
    2. Tier 2: LLM fast model batch fallback for unresolved transactions.
    3. Resilient fallback to 'Other' for unrecognized merchants.
    """
    if not transactions:
        return []

    unresolved_for_llm: List[Transaction] = []

    # ── Tier 1: Rule Engine ────────────────────────────────────────────────
    for txn in transactions:
        # Don't overwrite manual user categorizations
        if txn.category_source == CategorySource.user:
            continue

        rule_match = match_rule(
            raw_description=txn.raw_description,
            merchant_hint=txn.merchant_normalized,
            user_id=user_id,
        )

        if rule_match:
            cat, subcat, _ = rule_match
            txn.category = cat
            txn.subcategory = subcat
            txn.category_source = CategorySource.rule
            txn.confidence = 1.0
            if cat == "Transfers" or "transfer" in (txn.raw_description or "").lower():
                txn.is_transfer = True
        else:
            # Check if narration indicates transfer even if not matched by rule
            if "transfer" in (txn.raw_description or "").lower() or "self transfer" in (txn.raw_description or "").lower():
                txn.category = "Transfers"
                txn.is_transfer = True
                txn.category_source = CategorySource.rule
                txn.confidence = 0.95
            else:
                # Send to Tier 2 LLM if not classified by rule
                unresolved_for_llm.append(txn)

    # ── Tier 2: LLM Categorizer (Batched) ──────────────────────────────────
    if unresolved_for_llm:
        provider = llm_provider or get_llm_provider()
        batch_size = 25

        for i in range(0, len(unresolved_for_llm), batch_size):
            chunk = unresolved_for_llm[i : i + batch_size]
            items_payload = [
                {
                    "id": t.id or idx,
                    "narration": t.raw_description,
                    "amount_minor": t.amount_minor,
                    "direction": t.direction.value if hasattr(t.direction, "value") else str(t.direction),
                }
                for idx, t in enumerate(chunk)
            ]

            # Map payload ID back to txn object
            id_to_txn = {items_payload[idx]["id"]: t for idx, t in enumerate(chunk)}

            llm_results = await categorize_batch_with_llm(
                items_payload,
                provider,
                db=db,
                user_id=user_id,
            )

            for item_id, result in llm_results.items():
                if item_id in id_to_txn:
                    t = id_to_txn[item_id]
                    if result.confidence >= 0.4 and result.category != "Other":
                        t.category = result.category
                        t.subcategory = result.subcategory
                        t.confidence = result.confidence
                        t.category_source = CategorySource.llm
                        if result.merchant_clean and not t.merchant_normalized:
                            t.merchant_normalized = result.merchant_clean
                    else:
                        t.category = "Other"
                        t.category_source = CategorySource.rule
                        t.confidence = 0.0

    db.commit()
    return transactions
