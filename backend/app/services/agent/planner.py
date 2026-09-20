import json
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.services.llm_provider import BaseLLMProvider, LLMMessage
from app.services.agent.tools import TOOLS_DEFINITIONS, execute_tool
from app.services.agent.privacy import sanitize_tool_result
from app.services.agent.verifier import verify_answer, _format_grounded_fallback

PLANNER_SYSTEM_PROMPT = """You are FinPilot's Financial Query Planner.
Given a user query, determine the single best tool to call from the available tools list to retrieve accurate financial records.
Respond ONLY with a valid JSON object matching this schema:
{
  "tool": "<tool_name_or_none>",
  "args": { ... }
}
Do NOT include markdown formatting, backticks, or any explanation text outside the JSON object.
"""

PHRASER_SYSTEM_PROMPT = """You are FinPilot, an AI personal finance assistant.
RULES:
1. Always ground your answers strictly in the verified user data provided. Do NOT calculate or invent numbers.
2. STRICT GUARDRAIL: You are NOT an investment or financial advisor. Never recommend securities, stocks, crypto, or loans.
3. Be concise and supportive. Keep responses under 150 words. Format with clean bullet points.
"""


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extracts JSON object from text, handling markdown code blocks and whitespace."""
    text = text.strip()
    # Strip markdown fences if present
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        bracket_match = re.search(r"\{.*?\}", text, re.DOTALL)
        if bracket_match:
            text = bracket_match.group(0)

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


async def run_json_planner(
    user_message: str,
    provider: BaseLLMProvider,
    db: Session,
    user_id: int = 1,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Executes a single-shot JSON planning round suitable for weak or small local/free models

    (e.g. Ollama 7B/8B, Groq Llama, Gemini Flash).
    1. Asks model for {"tool": "...", "args": {...}}.
    2. Executes tool locally on SQLite.
    3. Anonymizes tool results before phrasing.
    4. Phraser generates concise response.
    5. Verifier checks numbers against tool data.
    """
    tools_summary = [
        {"name": t["name"], "description": t["description"], "parameters": t.get("input_schema", {})}
        for t in TOOLS_DEFINITIONS
    ]

    planner_prompt = (
        f"Available Tools:\n{json.dumps(tools_summary, indent=2)}\n\n"
        f"User Query: {user_message}\n\n"
        "Return the tool to call as JSON:"
    )

    messages = [
        LLMMessage(role="system", content=PLANNER_SYSTEM_PROMPT),
        LLMMessage(role="user", content=planner_prompt),
    ]

    total_input = 0
    total_output = 0

    plan_res = await provider.complete(messages=messages, max_tokens=150, temperature=0.0)
    total_input += plan_res.usage.get("input", 0)
    total_output += plan_res.usage.get("output", 0)

    parsed = _extract_json(plan_res.content)
    executed_tools: List[Dict[str, Any]] = []
    tool_results: List[Dict[str, Any]] = []

    valid_tool_names = {t["name"] for t in TOOLS_DEFINITIONS}

    if parsed and parsed.get("tool") in valid_tool_names:
        tool_name = parsed["tool"]
        tool_args = parsed.get("args") or {}
        executed_tools.append({"tool": tool_name, "arguments": tool_args})

        raw_data = execute_tool(tool_name, tool_args, db, user_id=user_id)
        sanitized_data = sanitize_tool_result(raw_data)
        tool_results.append(sanitized_data)

    if not tool_results:
        # Fallback to general data range or categories if no tool selected
        default_data = execute_tool("get_data_range", {}, db, user_id=user_id)
        executed_tools.append({"tool": "get_data_range", "arguments": {}})
        tool_results.append(default_data)

    # Output Phrasing
    phrase_prompt = (
        f"User Query: {user_message}\n\n"
        f"Verified User Financial Records:\n{json.dumps(tool_results, indent=2)[:1800]}\n\n"
        "Please provide a concise answer directly answering the user's question using the data above."
    )

    phrase_messages = [
        LLMMessage(role="system", content=PHRASER_SYSTEM_PROMPT),
        LLMMessage(role="user", content=phrase_prompt),
    ]

    phrase_res = await provider.complete(messages=phrase_messages, max_tokens=250, temperature=0.1)
    total_input += phrase_res.usage.get("input", 0)
    total_output += phrase_res.usage.get("output", 0)

    raw_reply = phrase_res.content or _format_grounded_fallback(tool_results)

    # Verification Step
    is_valid, verified_text, ungrounded = verify_answer(raw_reply, tool_results)

    return {
        "reply": verified_text,
        "tool_calls": executed_tools,
        "tool_results": tool_results,
        "verified": is_valid,
        "ungrounded_claims": ungrounded,
        "usage": {
            "input": total_input,
            "output": total_output,
            "cached_read": 0,
        },
    }
