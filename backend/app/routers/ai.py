import time
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.config import settings
from app.database import get_db
from app.models.ai_usage import AIUsageLog
from app.models.ai_cache import AICache
from app.services.llm_provider import (
    get_llm_provider,
    circuit_breaker,
    LLMMessage,
    OpenAICompatibleProvider,
    AnthropicProvider,
)

router = APIRouter(prefix="/ai", tags=["ai"])


class ModeUpdateRequest(BaseModel):
    mode: str  # "off" | "cheap" | "full"


class ConfigUpdateRequest(BaseModel):
    provider: str  # "none" | "ollama" | "gemini" | "groq" | "anthropic"
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class TestConnectionRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


def _get_provider_tier(provider: str) -> str:
    p = provider.lower()
    if p == "none":
        return "Offline"
    elif p == "ollama":
        return "Local"
    elif p in ("gemini", "groq"):
        return "Free Tier"
    elif p == "anthropic":
        return "Paid Cloud"
    return "Custom"


def _get_current_provider_model(provider: str) -> str:
    p = provider.lower()
    if p == "none":
        return "rule-engine-v1"
    elif p == "ollama":
        return settings.OLLAMA_MODEL
    elif p == "gemini":
        return settings.GEMINI_MODEL
    elif p == "groq":
        return settings.GROQ_MODEL
    elif p == "anthropic":
        return settings.ANTHROPIC_MODEL_FAST
    return "custom"


def _get_current_base_url(provider: str) -> str:
    p = provider.lower()
    if p == "ollama":
        return settings.OLLAMA_BASE_URL
    elif p == "gemini":
        return settings.GEMINI_BASE_URL
    elif p == "groq":
        return settings.GROQ_BASE_URL
    return ""


def _is_api_key_set(provider: str) -> bool:
    p = provider.lower()
    if p == "none" or p == "ollama":
        return True
    elif p == "gemini":
        return bool(settings.GEMINI_API_KEY)
    elif p == "groq":
        return bool(settings.GROQ_API_KEY)
    elif p == "anthropic":
        return bool(settings.ANTHROPIC_API_KEY)
    return False


@router.get("/config")
def get_ai_config():
    """Returns the current LLM provider configuration and circuit breaker status."""
    prov = settings.LLM_PROVIDER
    return {
        "provider": prov,
        "provider_tier": _get_provider_tier(prov),
        "model": _get_current_provider_model(prov),
        "base_url": _get_current_base_url(prov),
        "is_key_set": _is_api_key_set(prov),
        "circuit_breaker_open": circuit_breaker.is_open(),
        "circuit_breaker_cooldown": circuit_breaker.get_remaining_cooldown(),
        "is_free": prov in ("none", "ollama", "gemini", "groq"),
    }


@router.post("/config")
def update_ai_config(payload: ConfigUpdateRequest):
    """Updates the active LLM provider, base URL, model, and optional API key at runtime."""
    prov = payload.provider.lower().strip()
    if prov not in ("none", "ollama", "gemini", "groq", "anthropic", "fake"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider '{prov}'. Choose from: none, ollama, gemini, groq, anthropic.",
        )

    settings.LLM_PROVIDER = prov

    if prov == "ollama":
        if payload.model:
            settings.OLLAMA_MODEL = payload.model
        if payload.base_url:
            settings.OLLAMA_BASE_URL = payload.base_url
    elif prov == "gemini":
        if payload.model:
            settings.GEMINI_MODEL = payload.model
        if payload.base_url:
            settings.GEMINI_BASE_URL = payload.base_url
        if payload.api_key:
            settings.GEMINI_API_KEY = payload.api_key
    elif prov == "groq":
        if payload.model:
            settings.GROQ_MODEL = payload.model
        if payload.base_url:
            settings.GROQ_BASE_URL = payload.base_url
        if payload.api_key:
            settings.GROQ_API_KEY = payload.api_key
    elif prov == "anthropic":
        if payload.model:
            settings.ANTHROPIC_MODEL_FAST = payload.model
        if payload.api_key:
            settings.ANTHROPIC_API_KEY = payload.api_key

    # Reset circuit breaker when user changes config
    circuit_breaker.record_success()

    return {
        "status": "ok",
        "provider": settings.LLM_PROVIDER,
        "provider_tier": _get_provider_tier(settings.LLM_PROVIDER),
        "model": _get_current_provider_model(settings.LLM_PROVIDER),
        "base_url": _get_current_base_url(settings.LLM_PROVIDER),
        "is_free": settings.LLM_PROVIDER in ("none", "ollama", "gemini", "groq"),
    }


@router.post("/test-connection")
async def test_connection(payload: TestConnectionRequest):
    """Sends a minimal probe request to verify connectivity and latency."""
    prov = (payload.provider or settings.LLM_PROVIDER).lower().strip()
    start_time = time.time()

    if prov == "none":
        return {
            "status": "ok",
            "latency_ms": 1,
            "provider": "none",
            "message": "Deterministic offline engine ready (0ms latency, zero tokens).",
        }

    try:
        if prov in ("ollama", "gemini", "groq"):
            base_url = payload.base_url or _get_current_base_url(prov)
            api_key = payload.api_key or (
                settings.GEMINI_API_KEY if prov == "gemini" else settings.GROQ_API_KEY if prov == "groq" else "ollama"
            )
            model = payload.model or _get_current_provider_model(prov)
            test_provider = OpenAICompatibleProvider(
                base_url=base_url,
                api_key=api_key,
                model=model,
                provider_name=prov,
            )
            res = await test_provider.complete(
                messages=[LLMMessage(role="user", content="Ping. Respond with 'pong'.")],
                max_tokens=10,
            )
        elif prov == "anthropic":
            api_key = payload.api_key or settings.ANTHROPIC_API_KEY
            if not api_key:
                return {
                    "status": "error",
                    "latency_ms": 0,
                    "provider": "anthropic",
                    "message": "Anthropic API key is missing.",
                }
            test_provider = AnthropicProvider(api_key=api_key)
            res = await test_provider.complete(
                messages=[LLMMessage(role="user", content="Ping. Respond with 'pong'.")],
                max_tokens=10,
            )
        else:
            return {"status": "ok", "latency_ms": 5, "provider": prov, "message": "Provider simulated."}

        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "status": "ok",
            "latency_ms": latency_ms,
            "provider": prov,
            "message": f"Successfully connected to {prov} ({res.model}) in {latency_ms}ms.",
            "response": res.content[:60],
        }
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "status": "error",
            "latency_ms": latency_ms,
            "provider": prov,
            "message": f"Connection failed: {str(e)}",
        }


@router.get("/usage")
def get_ai_usage_stats(
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Returns AI token consumption, cache efficiency metrics, and estimated costs in ₹ and $."""
    today_start = datetime.combine(date.today(), datetime.min.time())

    # Aggregate today's usage
    today_logs = (
        db.execute(
            select(
                func.coalesce(func.sum(AIUsageLog.input_tokens), 0),
                func.coalesce(func.sum(AIUsageLog.output_tokens), 0),
                func.coalesce(func.sum(AIUsageLog.cached_read_tokens), 0),
                func.coalesce(func.sum(AIUsageLog.tokens_saved), 0),
                func.coalesce(func.sum(AIUsageLog.estimated_cost_inr), 0.0),
                func.coalesce(func.sum(AIUsageLog.estimated_cost_usd), 0.0),
                func.count(AIUsageLog.id),
            )
            .where(
                AIUsageLog.user_id == user_id,
                AIUsageLog.created_at >= today_start,
            )
        )
        .first()
    )

    inp = today_logs[0] if today_logs else 0
    out = today_logs[1] if today_logs else 0
    cached_read = today_logs[2] if today_logs else 0
    tokens_saved = today_logs[3] if today_logs else 0
    raw_cost_inr = round(float(today_logs[4]), 2) if today_logs else 0.0
    raw_cost_usd = round(float(today_logs[5]), 4) if today_logs else 0.0
    req_count = today_logs[6] if today_logs else 0

    cache_hits = (
        db.scalar(
            select(func.count(AIUsageLog.id)).where(
                AIUsageLog.user_id == user_id,
                AIUsageLog.created_at >= today_start,
                AIUsageLog.is_cache_hit.is_(True),
            )
        )
        or 0
    )

    cache_hit_rate_pct = round((cache_hits / req_count) * 100, 1) if req_count > 0 else 0.0

    prov = settings.LLM_PROVIDER
    is_free = prov in ("none", "ollama", "gemini", "groq")

    return {
        "tokens_used_today": inp + out,
        "input_tokens_today": inp,
        "output_tokens_today": out,
        "cached_read_tokens_today": cached_read,
        "tokens_saved_by_cache": tokens_saved,
        "cache_hit_rate_pct": cache_hit_rate_pct,
        "estimated_cost_inr": 0.0 if is_free else raw_cost_inr,
        "estimated_cost_usd": 0.0 if is_free else raw_cost_usd,
        "is_free": is_free,
        "provider": prov,
        "provider_tier": _get_provider_tier(prov),
        "circuit_breaker_open": circuit_breaker.is_open(),
        "circuit_breaker_cooldown": circuit_breaker.get_remaining_cooldown(),
        "is_estimated": True,
        "currency_symbol": "₹",
        "total_requests": req_count,
        "llm_mode": settings.LLM_MODE,
        "model_fast": _get_current_provider_model(prov),
        "model_smart": settings.ANTHROPIC_MODEL_SMART,
    }


@router.post("/mode")
def set_ai_mode(
    payload: ModeUpdateRequest,
):
    """Sets LLM_MODE at runtime: 'off', 'cheap', or 'full'."""
    mode = payload.mode.lower().strip()
    if mode not in ["off", "cheap", "full"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid mode. Allowed values: 'off', 'cheap', 'full'.",
        )
    settings.LLM_MODE = mode
    return {
        "status": "ok",
        "llm_mode": settings.LLM_MODE,
        "description": (
            "Deterministic offline rules & templates"
            if mode == "off"
            else "Aggressive caching & zero-cost router priority"
            if mode == "cheap"
            else "Full AI assistance with smart models enabled"
        ),
    }


@router.delete("/cache")
def clear_ai_cache(
    user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Purges cached LLM outputs for testing and benchmarks."""
    from app.services.cache_service import invalidate_user_qa_cache
    from sqlalchemy import delete
    del_count = db.execute(delete(AICache).where(AICache.user_id == user_id)).rowcount
    db.commit()
    return {"status": "ok", "cleared_entries": del_count}
