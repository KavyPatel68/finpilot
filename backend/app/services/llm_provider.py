import json
import time
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import httpx
import anthropic

from app.config import settings


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)


# ── Rate Limiter & Circuit Breaker ───────────────────────────────────────────

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "closed"  # "closed" | "open" | "half_open"

    def record_success(self):
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def is_open(self) -> bool:
        if self.state == "open":
            if time.time() - self.last_failure_time > self.cooldown_seconds:
                self.state = "half_open"
                return False
            return True
        return False

    def get_remaining_cooldown(self) -> int:
        if self.state != "open":
            return 0
        elapsed = time.time() - self.last_failure_time
        return max(0, int(self.cooldown_seconds - elapsed))


circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    cooldown_seconds=settings.CIRCUIT_BREAKER_COOLDOWN_SECONDS,
)


# ── Base Provider Interface ──────────────────────────────────────────────────

class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 400,
        temperature: float = 0.0,
    ) -> LLMResponse:
        pass


# ── 1. None Provider (Default - 100% Free & Offline) ──────────────────────────

class NoneProvider(BaseLLMProvider):
    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 400,
        temperature: float = 0.0,
    ) -> LLMResponse:
        return LLMResponse(
            content="FinPilot is running in offline mode (`LLM_PROVIDER=none`). All questions and calculations are performed using deterministic rules and templates.",
            model="rule-engine-v1",
            usage={"input": 0, "output": 0, "cached_read": 0},
            tool_calls=[],
        )


# ── 2. OpenAI-Compatible Provider (Ollama, Gemini, Groq) ──────────────────────

class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        provider_name: str = "openai_compatible",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider_name = provider_name

    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 400,
        temperature: float = 0.0,
    ) -> LLMResponse:
        if circuit_breaker.is_open():
            cd = circuit_breaker.get_remaining_cooldown()
            return LLMResponse(
                content=f"Running in basic mode (Provider rate limited; circuit breaker active for {cd}s).",
                model=f"{self.model}-circuit-breaker",
                usage={"input": 0, "output": 0, "cached_read": 0},
                tool_calls=[],
            )

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Convert tools to OpenAI format if provided
        if tools:
            openai_tools = []
            for t in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                    },
                })
            payload["tools"] = openai_tools

        endpoint = f"{self.base_url}/chat/completions"
        max_retries = 2
        delay = 1.0

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    resp = await client.post(endpoint, json=payload, headers=headers)

                    if resp.status_code == 429:
                        if attempt < max_retries:
                            await asyncio.sleep(delay)
                            delay *= 2
                            continue
                        else:
                            circuit_breaker.record_failure()
                            return LLMResponse(
                                content="Running in basic mode (Provider free-tier rate limit exceeded: 429 Too Many Requests).",
                                model=self.model,
                                usage={"input": 0, "output": 0, "cached_read": 0},
                                tool_calls=[],
                            )

                    resp.raise_for_status()
                    data = resp.json()

                    circuit_breaker.record_success()

                    choice = data["choices"][0] if data.get("choices") else {}
                    message = choice.get("message", {})
                    content = message.get("content") or ""

                    tool_calls = []
                    if message.get("tool_calls"):
                        for tc in message["tool_calls"]:
                            fn = tc.get("function", {})
                            name = fn.get("name")
                            raw_args = fn.get("arguments", "{}")
                            try:
                                parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                            except Exception:
                                parsed_args = {}
                            tool_calls.append({"name": name, "args": parsed_args, "id": tc.get("id", name)})

                    usage = data.get("usage", {})
                    return LLMResponse(
                        content=content,
                        model=self.model,
                        usage={
                            "input": usage.get("prompt_tokens", 0),
                            "output": usage.get("completion_tokens", 0),
                            "cached_read": 0,
                        },
                        tool_calls=tool_calls,
                    )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                circuit_breaker.record_failure()
                return LLMResponse(
                    content=f"Running in basic mode (API Error {e.response.status_code}).",
                    model=self.model,
                    usage={"input": 0, "output": 0, "cached_read": 0},
                    tool_calls=[],
                )
            except Exception as e:
                circuit_breaker.record_failure()
                return LLMResponse(
                    content=f"Running in basic mode (Connection failed to {self.provider_name}).",
                    model=self.model,
                    usage={"input": 0, "output": 0, "cached_read": 0},
                    tool_calls=[],
                )

        return LLMResponse(
            content="Running in basic mode (Provider request timeout).",
            model=self.model,
            usage={"input": 0, "output": 0, "cached_read": 0},
            tool_calls=[],
        )


# ── 3. Anthropic Provider (Optional Paid Cloud) ──────────────────────────────

class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        if api_key and settings.LLM_MODE != "off":
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            self.client = None

    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 400,
        temperature: float = 0.0,
    ) -> LLMResponse:
        if not self.client or not self.api_key:
            return LLMResponse(
                content="[Anthropic API key not configured] Analysis completed offline.",
                model="offline-fallback",
                usage={"input": 0, "output": 0, "cached_read": 0},
            )

        if circuit_breaker.is_open():
            cd = circuit_breaker.get_remaining_cooldown()
            return LLMResponse(
                content=f"Running in basic mode (Anthropic circuit breaker active for {cd}s).",
                model="circuit-breaker",
                usage={"input": 0, "output": 0, "cached_read": 0},
            )

        model_name = settings.ANTHROPIC_MODEL_FAST
        system_prompt = None
        formatted_messages = []

        for m in messages:
            if m.role == "system":
                system_prompt = m.content
            else:
                formatted_messages.append({"role": m.role, "content": m.content})

        kwargs: Dict[str, Any] = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": formatted_messages,
        }

        if system_prompt:
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        if tools:
            cached_tools = []
            for idx, t in enumerate(tools):
                t_copy = dict(t)
                if idx == len(tools) - 1:
                    t_copy["cache_control"] = {"type": "ephemeral"}
                cached_tools.append(t_copy)
            kwargs["tools"] = cached_tools

        try:
            response = await self.client.messages.create(**kwargs)
            circuit_breaker.record_success()

            text_content = ""
            tool_calls = []

            for block in response.content:
                if hasattr(block, "text"):
                    text_content += block.text
                elif getattr(block, "type", None) == "tool_use":
                    tool_calls.append({
                        "name": block.name,
                        "args": block.input,
                        "id": block.id,
                    })

            cached_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
            return LLMResponse(
                content=text_content,
                model=model_name,
                usage={
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens,
                    "cached_read": cached_read,
                },
                tool_calls=tool_calls,
            )
        except anthropic.RateLimitError:
            circuit_breaker.record_failure()
            return LLMResponse(
                content="Running in basic mode (Anthropic rate limit 429 exceeded).",
                model=model_name,
                usage={"input": 0, "output": 0, "cached_read": 0},
            )
        except Exception as e:
            circuit_breaker.record_failure()
            return LLMResponse(
                content=f"Running in basic mode (Anthropic API unavailable: {str(e)[:80]}).",
                model=model_name,
                usage={"input": 0, "output": 0, "cached_read": 0},
            )


# ── 4. Fake Provider (Testing - Zero Network Calls) ───────────────────────────

class FakeLLMProvider(BaseLLMProvider):
    def __init__(self, canned_response: Optional[str] = None, canned_tools: Optional[List[Dict[str, Any]]] = None):
        self.canned_response = canned_response or "Canned deterministic response from fake LLM."
        self.canned_tools = canned_tools or []

    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 400,
        temperature: float = 0.0,
    ) -> LLMResponse:
        return LLMResponse(
            content=self.canned_response,
            model="fake-llm-model",
            usage={"input": 15, "output": 25, "cached_read": 0},
            tool_calls=list(self.canned_tools),
        )


# ── Provider Factory ─────────────────────────────────────────────────────────

def get_llm_provider(provider_name: Optional[str] = None) -> BaseLLMProvider:
    """Instantiates the requested or configured provider."""
    name = (provider_name or settings.LLM_PROVIDER).lower().strip()

    if name == "none":
        return NoneProvider()
    elif name == "ollama":
        return OpenAICompatibleProvider(
            base_url=settings.OLLAMA_BASE_URL,
            api_key="ollama",
            model=settings.OLLAMA_MODEL,
            provider_name="ollama",
        )
    elif name == "gemini":
        return OpenAICompatibleProvider(
            base_url=settings.GEMINI_BASE_URL,
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            provider_name="gemini",
        )
    elif name == "groq":
        return OpenAICompatibleProvider(
            base_url=settings.GROQ_BASE_URL,
            api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL,
            provider_name="groq",
        )
    elif name == "anthropic":
        return AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY)
    elif name == "fake":
        return FakeLLMProvider()

    # Default fallback to NoneProvider
    return NoneProvider()
