import json
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.services.llm_provider import BaseLLMProvider, LLMMessage, get_llm_provider, circuit_breaker
from app.services.agent.tools import TOOLS_DEFINITIONS, execute_tool
from app.services.agent.intent_router import route_and_execute_intent
from app.services.agent.privacy import sanitize_tool_result
from app.services.agent.verifier import verify_answer
from app.services.agent.planner import run_json_planner
from app.services.cache_service import (
    get_user_data_version,
    compute_cache_key,
    get_cached_response,
    store_cached_response,
    log_ai_usage,
)

COMPACT_SYSTEM_PROMPT = """You are FinPilot, an AI personal finance assistant.
RULES:
1. Always ground your answers in verified user data from tool results. Never calculate or invent numbers.
2. STRICT GUARDRAIL: You are NOT an investment or financial advisor. Never recommend securities, stocks, crypto, or loans.
3. Be concise and supportive. Keep responses under 150 words. Format with clean bullet points.
"""

INVESTMENT_TRIGGERS = [
    "what stock", "which stock", "buy stock", "invest in crypto", "buy bitcoin",
    "which mutual fund", "best mutual fund", "should i invest", "recommend a stock",
    "stock tip", "crypto tip", "which crypto", "what crypto", "invest in", "invest into",
    "stocks to buy", "shares to buy", "best stock", "best crypto",
]


def _is_investment_advice_query(prompt: str) -> bool:
    p = prompt.lower()
    return any(t in p for t in INVESTMENT_TRIGGERS)


async def run_agent(
    user_message: str,
    db: Session,
    user_id: int = 1,
    chat_history: Optional[List[Dict[str, str]]] = None,
    llm_provider: Optional[BaseLLMProvider] = None,
) -> Dict[str, Any]:
    """Runs the FinPilot provider-agnostic decision-support agent:

    1. Instant refusal for investment advice (0 tokens).
    2. Zero-token intent router for 40+ common queries (0 tokens).
    3. SQLite Q&A cache check using user data-version token (0 tokens).
    4. Circuit breaker check: falls back to basic mode if tripped (0 tokens).
    5. Offline mode fallback if LLM_PROVIDER == 'none' or LLM_MODE == 'off' (0 tokens).
    6. Small-model planner & verifier for free/local/cloud LLMs.
    """
    # ── Step 1: Investment Advice Refusal (0 tokens) ─────────────────────────
    if _is_investment_advice_query(user_message):
        return {
            "reply": (
                "FinPilot is a personal finance decision-support tool, not a licensed financial or investment advisor. "
                "I cannot recommend specific securities, stocks, crypto, or investment products. "
                "However, I can help you analyze your spending trends, track recurring bills, and optimize your savings goals!"
            ),
            "tool_calls": [],
            "tool_results": [],
            "intent": "investment_refusal",
            "confidence": 1.0,
        }

    # ── Step 2: Zero-Token Intent Routing (0 tokens) ─────────────────────────
    intent_res = route_and_execute_intent(user_message, db, user_id=user_id)
    if intent_res.matched and intent_res.confidence >= 0.80:
        return {
            "reply": intent_res.reply,
            "tool_calls": intent_res.tool_calls,
            "tool_results": [intent_res.figures] if intent_res.figures else [],
            "intent": intent_res.intent,
            "confidence": intent_res.confidence,
        }

    # ── Step 3: SQLite Q&A Cache Check (0 tokens) ────────────────────────────
    data_version = get_user_data_version(db, user_id=user_id)
    cache_key = compute_cache_key("qa", user_message, user_id=user_id, data_version=data_version)
    cached_output = get_cached_response(db, cache_key)
    if cached_output and isinstance(cached_output, dict):
        log_ai_usage(
            db=db,
            user_id=user_id,
            task_type="qa",
            model=settings.ANTHROPIC_MODEL_FAST,
            input_tokens=0,
            output_tokens=0,
            is_cache_hit=True,
            tokens_saved=250,
        )
        cached_output["is_cached"] = True
        return cached_output

    # ── Step 4: Circuit Breaker Check (0 tokens) ─────────────────────────────
    if circuit_breaker.is_open():
        cd = circuit_breaker.get_remaining_cooldown()
        return {
            "reply": f"Running in basic mode (Provider rate limited; circuit breaker active for {cd}s).",
            "tool_calls": [],
            "tool_results": [],
            "circuit_breaker": True,
        }

    # ── Step 5: Offline Mode Fallback (0 tokens) ─────────────────────────────
    provider = llm_provider or get_llm_provider()
    active_provider = getattr(provider, "provider_name", settings.LLM_PROVIDER).lower()

    if active_provider == "none" or settings.LLM_MODE == "off":
        return {
            "reply": (
                "FinPilot is running in offline mode (`LLM_PROVIDER=none`). "
                "You can ask questions such as 'What are my subscriptions?', 'Show top categories', "
                "'How much did I spend in August 2024?', or 'Budget status' to view verified metrics with zero API costs."
            ),
            "tool_calls": [],
            "tool_results": [],
            "offline_mode": True,
        }

    # ── Step 6: Provider / Planner Execution ─────────────────────────────────
    # If using Anthropic with native tools
    if active_provider == "anthropic":
        messages: List[LLMMessage] = []
        if chat_history:
            for m in chat_history[-4:]:
                messages.append(LLMMessage(role=m["role"], content=m["content"]))
        messages.append(LLMMessage(role="user", content=user_message))

        executed_tools: List[Dict[str, Any]] = []
        tool_results: List[Dict[str, Any]] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_cached_read = 0
        reply_text = ""

        MAX_TOOL_LOOPS = 2
        for loop in range(MAX_TOOL_LOOPS):
            res = await provider.complete(
                messages=messages,
                tools=TOOLS_DEFINITIONS,
                max_tokens=250,
            )
            total_input_tokens += res.usage.get("input", 0)
            total_output_tokens += res.usage.get("output", 0)
            total_cached_read += res.usage.get("cached_read", 0)

            if not res.tool_calls:
                reply_text = res.content
                break

            for t_call in res.tool_calls[:1]:
                name = t_call["name"]
                args = t_call["args"]
                executed_tools.append({"tool": name, "arguments": args})
                data = execute_tool(name, args, db, user_id=user_id)
                sanitized = sanitize_tool_result(data)
                tool_results.append(sanitized)

                messages.append(LLMMessage(role="assistant", content=f"Called {name} with args {args}"))
                messages.append(
                    LLMMessage(role="user", content=f"Tool output: {json.dumps(sanitized)[:1500]}")
                )

            if loop == MAX_TOOL_LOOPS - 1:
                final_res = await provider.complete(messages=messages, max_tokens=250)
                total_input_tokens += final_res.usage.get("input", 0)
                total_output_tokens += final_res.usage.get("output", 0)
                reply_text = final_res.content

        # Run verifier on generated answer
        is_valid, verified_reply, ungrounded = verify_answer(reply_text, tool_results)

        final_payload = {
            "reply": verified_reply,
            "tool_calls": executed_tools,
            "tool_results": tool_results,
            "verified": is_valid,
        }
    else:
        # For Ollama, Gemini, Groq, FakeLLMProvider: use structured single-shot JSON planner
        planner_result = await run_json_planner(
            user_message=user_message,
            provider=provider,
            db=db,
            user_id=user_id,
            chat_history=chat_history,
        )
        final_payload = {
            "reply": planner_result["reply"],
            "tool_calls": planner_result["tool_calls"],
            "tool_results": planner_result["tool_results"],
            "verified": planner_result.get("verified", True),
        }
        total_input_tokens = planner_result.get("usage", {}).get("input", 0)
        total_output_tokens = planner_result.get("usage", {}).get("output", 0)
        total_cached_read = 0

    # Cache response in SQLite
    store_cached_response(
        db=db,
        key_hash=cache_key,
        user_id=user_id,
        task_type="qa",
        prompt_str=user_message,
        response_json=final_payload,
        estimated_tokens_saved=total_input_tokens + total_output_tokens,
    )

    # Log AI usage
    log_ai_usage(
        db=db,
        user_id=user_id,
        task_type="qa",
        model=getattr(provider, "model", settings.LLM_PROVIDER),
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        cached_read_tokens=total_cached_read,
    )

    return final_payload
