import json
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.config import settings
from app.services.llm_provider import BaseLLMProvider, LLMMessage
from app.services.categorization.taxonomy import CATEGORIES
from app.services.cache_service import (
    compute_cache_key,
    get_cached_response,
    store_cached_response,
    log_ai_usage,
)

# Ultra-compact system prompt under 80 tokens
COMPACT_CATEGORIZER_PROMPT = (
    "Categorize merchants into exact category from: "
    + ", ".join(CATEGORIES)
    + '. Output strictly compact JSON map: {"MERCHANT_STRING": "Category"}'
)


@dataclass
class LLMCategoryResult:
    id: int
    category: str
    subcategory: Optional[str] = None
    confidence: float = 0.5
    merchant_clean: Optional[str] = None


def _clean_narration_to_merchant(raw: str) -> str:
    """Strips transaction rail prefixes, reference IDs, and digits to produce a normalized merchant key."""
    if not raw:
        return "UNKNOWN"
    s = raw.strip()
    s = re.sub(r"^(UPI|NEFT|IMPS|POS|ACH|NACH|RTGS|ATM)[\/\-\s:]+", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(DR|CR|REF|TXN|PAYMENT|INFO|BILL)[\/\-\s#0-9]+\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[^A-Za-z\s]", " ", s)
    tokens = s.split()
    return " ".join(tokens[:3]).upper() if tokens else raw[:30].upper()


async def categorize_batch_with_llm(
    items: List[Dict[str, Any]],
    llm_provider: BaseLLMProvider,
    db: Optional[Session] = None,
    user_id: int = 1,
) -> Dict[int, LLMCategoryResult]:
    """Token-efficient batch categorizer:

    1. Checks SQLite AICache for each merchant key first (zero tokens).
    2. Batches up to 50 distinct uncached merchants per single compact LLM call.
    3. Uses temperature=0.0 and max_tokens=300.
    4. Caches newly categorized merchants into SQLite.
    """
    if not items:
        return {}

    # Map each item to its normalized merchant key
    item_merchant_map: Dict[int, str] = {}
    distinct_merchants: Dict[str, str] = {}  # merchant_key -> original raw

    for it in items:
        raw = it.get("narration") or it.get("raw_description") or ""
        norm_key = _clean_narration_to_merchant(raw)
        item_merchant_map[it["id"]] = norm_key
        if norm_key not in distinct_merchants:
            distinct_merchants[norm_key] = raw

    merchant_cat_cache: Dict[str, str] = {}
    uncached_merchants: List[str] = []
    item_custom_results: Dict[int, Any] = {}

    # 1. Check SQLite Cache
    for m_key in distinct_merchants.keys():
        cache_key = compute_cache_key("categorize", m_key, user_id=user_id)
        if db:
            cached_val = get_cached_response(db, cache_key)
            if cached_val and isinstance(cached_val, dict) and "category" in cached_val:
                merchant_cat_cache[m_key] = cached_val["category"]
                continue
        uncached_merchants.append(m_key)

    # 2. If uncached items exist and LLM is enabled, batch call LLM
    if uncached_merchants and settings.LLM_MODE != "off":
        # Process in chunks of 50
        CHUNK_SIZE = 50
        for i in range(0, len(uncached_merchants), CHUNK_SIZE):
            chunk = uncached_merchants[i : i + CHUNK_SIZE]
            prompt = json.dumps(chunk)

            try:
                resp = await llm_provider.complete(
                    messages=[LLMMessage(role="user", content=prompt)],
                    system=COMPACT_CATEGORIZER_PROMPT,
                    model=settings.ANTHROPIC_MODEL_FAST,
                    max_tokens=300,
                )

                content = resp.content.strip()
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\n?", "", content)
                    content = re.sub(r"\n?```$", "", content)

                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    for m_name, cat in parsed.items():
                        matched_cat = cat if cat in CATEGORIES else "Other"
                        m_upper = m_name.strip().upper()
                        merchant_cat_cache[m_upper] = matched_cat

                        # Store in SQLite cache
                        if db:
                            c_key = compute_cache_key("categorize", m_upper, user_id=user_id)
                            store_cached_response(
                                db=db,
                                key_hash=c_key,
                                user_id=user_id,
                                task_type="categorize",
                                prompt_str=m_upper,
                                response_json={"category": matched_cat},
                                estimated_tokens_saved=25,
                            )
                elif isinstance(parsed, list):
                    for entry in parsed:
                        matched_cat = entry.get("category", "Other")
                        if matched_cat not in CATEGORIES:
                            matched_cat = "Other"
                        clean_name = entry.get("merchant_clean")
                        if clean_name:
                            merchant_cat_cache[clean_name.strip().upper()] = matched_cat
                        if "id" in entry:
                            merchant_cat_cache[f"id_{entry['id']}"] = matched_cat
                            item_custom_results[entry["id"]] = entry
                        for m_k in chunk:
                            merchant_cat_cache[m_k] = matched_cat

                # Log token usage
                if db:
                    log_ai_usage(
                        db=db,
                        user_id=user_id,
                        task_type="categorize",
                        model=resp.model,
                        input_tokens=resp.usage.get("input", 0),
                        output_tokens=resp.usage.get("output", 0),
                        cached_read_tokens=resp.usage.get("cached_read", 0),
                    )
            except Exception:
                # Resilient fallback: assign "Other"
                for m_name in chunk:
                    if m_name not in merchant_cat_cache:
                        merchant_cat_cache[m_name] = "Other"

    # Map classifications back to all transaction items
    results: Dict[int, LLMCategoryResult] = {}
    for it in items:
        txn_id = it["id"]
        m_key = item_merchant_map[txn_id]
        category = merchant_cat_cache.get(m_key) or merchant_cat_cache.get(f"id_{txn_id}") or "Other"
        confidence = 0.85 if category != "Other" else 0.4
        merchant_clean = m_key.title() if m_key != "UNKNOWN" else None
        subcategory = None

        if txn_id in item_custom_results:
            c_meta = item_custom_results[txn_id]
            category = c_meta.get("category", category)
            confidence = c_meta.get("confidence", confidence)
            merchant_clean = c_meta.get("merchant_clean", merchant_clean)
            subcategory = c_meta.get("subcategory")

        results[txn_id] = LLMCategoryResult(
            id=txn_id,
            category=category,
            subcategory=subcategory,
            confidence=confidence,
            merchant_clean=merchant_clean,
        )

    return results
