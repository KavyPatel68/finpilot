import hashlib
import json
from datetime import datetime, date
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete

from app.config import settings
from app.models.ai_cache import AICache
from app.models.ai_usage import AIUsageLog
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.goal import Goal


def get_user_data_version(db: Session, user_id: int = 1) -> str:
    """Computes a lightweight deterministic data-version token for a user.

    Any insert, delete, or category update alters this token.
    """
    txn_stats = db.execute(
        select(
            func.count(Transaction.id),
            func.coalesce(func.max(Transaction.id), 0),
        ).where(Transaction.user_id == user_id)
    ).first()
    txn_count = txn_stats[0] if txn_stats else 0
    max_txn_id = txn_stats[1] if txn_stats else 0

    budget_count = db.scalar(
        select(func.count(Budget.id)).where(Budget.user_id == user_id)
    ) or 0

    goal_count = db.scalar(
        select(func.count(Goal.id)).where(Goal.user_id == user_id)
    ) or 0

    raw = f"{user_id}:{txn_count}:{max_txn_id}:{budget_count}:{goal_count}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def compute_cache_key(
    task_type: str,
    normalized_input: str,
    user_id: int = 1,
    data_version: Optional[str] = None,
) -> str:
    """Computes a unique SHA-256 cache key.

    For Q&A and reports, incorporates the user's data-version token.
    For merchant classification, uses the normalized merchant name.
    """
    cleaned = normalized_input.strip().lower()
    if data_version:
        token = f"{task_type}:{user_id}:{data_version}:{cleaned}"
    else:
        token = f"{task_type}:{cleaned}"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_cached_response(
    db: Session,
    key_hash: str,
) -> Optional[Dict[str, Any]]:
    """Retrieves a cached JSON response if present."""
    cached = db.get(AICache, key_hash)
    if cached:
        return cached.response_json
    return None


def store_cached_response(
    db: Session,
    key_hash: str,
    user_id: int,
    task_type: str,
    prompt_str: str,
    response_json: Any,
    estimated_tokens_saved: int = 0,
) -> AICache:
    """Persists an LLM output into SQLite cache."""
    prompt_hash = hashlib.sha256(prompt_str.encode("utf-8")).hexdigest()
    cached = db.get(AICache, key_hash)
    if not cached:
        cached = AICache(
            key_hash=key_hash,
            user_id=user_id,
            task_type=task_type,
            prompt_hash=prompt_hash,
            response_json=response_json,
            estimated_tokens_saved=estimated_tokens_saved,
            created_at=datetime.utcnow(),
        )
        db.add(cached)
    else:
        cached.response_json = response_json
        cached.estimated_tokens_saved = estimated_tokens_saved
        cached.created_at = datetime.utcnow()

    db.commit()
    return cached


def invalidate_user_qa_cache(db: Session, user_id: int = 1) -> int:
    """Clears all Q&A and report cached responses for a user upon statement upload or category override."""
    stmt = delete(AICache).where(
        AICache.user_id == user_id,
        AICache.task_type.in_(["qa", "report", "insights", "routing"]),
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_read_tokens: int = 0,
) -> Tuple[float, float]:
    """Calculates estimated cost in USD and INR based on settings."""
    prices = settings.MODEL_PRICES.get(
        model,
        settings.MODEL_PRICES.get("claude-haiku-4-5-20251001", {"input": 1.0, "output": 5.0, "cache_read": 0.1}),
    )
    # Prices are per million tokens
    cost_usd = (
        (input_tokens / 1_000_000.0) * prices.get("input", 1.0)
        + (output_tokens / 1_000_000.0) * prices.get("output", 5.0)
        + (cached_read_tokens / 1_000_000.0) * prices.get("cache_read", 0.1)
    )
    cost_inr = cost_usd * settings.USD_TO_INR_RATE
    return round(cost_usd, 6), round(cost_inr, 4)


def log_ai_usage(
    db: Session,
    user_id: int,
    task_type: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_read_tokens: int = 0,
    is_cache_hit: bool = False,
    tokens_saved: int = 0,
) -> AIUsageLog:
    """Records token consumption and estimated cost in INR & USD."""
    cost_usd, cost_inr = calculate_cost(model, input_tokens, output_tokens, cached_read_tokens)
    log = AIUsageLog(
        user_id=user_id,
        task_type=task_type,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_read_tokens=cached_read_tokens,
        tokens_saved=tokens_saved,
        is_cache_hit=is_cache_hit,
        estimated_cost_usd=cost_usd,
        estimated_cost_inr=cost_inr,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    return log
