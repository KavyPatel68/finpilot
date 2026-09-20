import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.llm_provider import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    NoneProvider,
    FakeLLMProvider,
    OpenAICompatibleProvider,
    CircuitBreaker,
    get_llm_provider,
)
from app.services.agent.privacy import anonymize_text, sanitize_tool_result
from app.services.agent.verifier import verify_answer, extract_claims
from app.services.agent.orchestrator import run_agent


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. NoneProvider (Offline Out-of-the-Box) ─────────────────────────────────

@pytest.mark.asyncio
async def test_none_provider_offline():
    provider = NoneProvider()
    resp = await provider.complete([LLMMessage(role="user", content="Hello FinPilot")])
    assert "offline mode" in resp.content.lower()
    assert resp.model == "rule-engine-v1"
    assert resp.usage["input"] == 0
    assert resp.usage["output"] == 0


# ── 2. FakeLLMProvider (Testing / Zero Network) ──────────────────────────────

@pytest.mark.asyncio
async def test_fake_llm_provider():
    provider = FakeLLMProvider(
        canned_response="Here is your spending analysis.",
        canned_tools=[{"name": "get_spending_by_category", "args": {"category": "Dining"}}],
    )
    resp = await provider.complete([LLMMessage(role="user", content="Where did money go?")])
    assert resp.content == "Here is your spending analysis."
    assert resp.model == "fake-llm-model"
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0]["name"] == "get_spending_by_category"


# ── 3. Circuit Breaker & Rate Limit Storm ────────────────────────────────────

def test_circuit_breaker_logic():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
    assert not cb.is_open()
    assert cb.get_remaining_cooldown() == 0

    # 1st failure
    cb.record_failure()
    assert not cb.is_open()

    # 2nd failure
    cb.record_failure()
    assert not cb.is_open()

    # 3rd failure -> trips circuit
    cb.record_failure()
    assert cb.is_open()
    assert cb.get_remaining_cooldown() > 0

    # Reset
    cb.record_success()
    assert not cb.is_open()


@pytest.mark.asyncio
async def test_openai_compatible_circuit_breaker_trip():
    prov = OpenAICompatibleProvider(
        base_url="http://mock-endpoint/v1",
        api_key="test-key",
        model="mock-model",
        provider_name="test_groq",
    )

    # Simulate 429 storm using mock client
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        # Run calls to trip circuit breaker
        res = await prov.complete([LLMMessage(role="user", content="test")])
        assert "rate limit exceeded" in res.content.lower() or "basic mode" in res.content.lower()


# ── 4. Privacy Filter ────────────────────────────────────────────────────────

def test_privacy_filter_strips_pii():
    sensitive_text = (
        "Customer Rahul Sharma (PAN: ABCDE1234F, IFSC: HDFC0001234, "
        "A/C: 987654321012, Phone: 9876543210, Email: test@finpilot.in) spent ₹500 at Swiggy."
    )
    cleaned = anonymize_text(sensitive_text)
    assert "ABCDE1234F" not in cleaned
    assert "[PAN_REDACTED]" in cleaned
    assert "HDFC0001234" not in cleaned
    assert "[IFSC_REDACTED]" in cleaned
    assert "987654321012" not in cleaned
    assert "[ACCOUNT_REDACTED]" in cleaned
    assert "9876543210" not in cleaned
    assert "[PHONE_REDACTED]" in cleaned
    assert "test@finpilot.in" not in cleaned
    assert "[EMAIL_REDACTED]" in cleaned
    assert "Swiggy" in cleaned


def test_sanitize_tool_result():
    tool_output = {
        "user_id": 1,
        "account_number": "123456789012",
        "account_number_masked": "XXXX1234",
        "merchants": [
            {"merchant": "Swiggy", "raw_description": "UPI/123456/Swiggy Bangalore/HDFC0001234/9876543210"},
        ],
    }
    sanitized = sanitize_tool_result(tool_output)
    assert "account_number" not in sanitized
    assert "user_id" not in sanitized
    merchant_entry = sanitized["merchants"][0]
    assert merchant_entry["merchant"] == "Swiggy"
    assert "HDFC0001234" not in merchant_entry["description"]
    assert "[IFSC_REDACTED]" in merchant_entry["description"]


# ── 5. Number Verifier (Hallucination Detection) ─────────────────────────────

def test_verifier_catches_hallucinated_amounts():
    tool_data = [
        {
            "categories": [
                {"category": "Dining", "amount_minor": 150000, "amount_formatted": "₹1,500.00"},
            ],
            "total_expense": "₹1,500.00",
        }
    ]

    # Valid text with verified numbers
    valid_text = "You spent ₹1,500.00 on Dining this month."
    is_valid, out_text, ungrounded = verify_answer(valid_text, tool_data)
    assert is_valid is True
    assert len(ungrounded) == 0

    # Hallucinated number (e.g. ₹9,999.00 not present anywhere)
    hallucinated_text = "You spent ₹9,999.00 on Dining and 78% on Groceries."
    is_valid, fallback_text, ungrounded = verify_answer(hallucinated_text, tool_data)
    assert is_valid is False
    assert len(ungrounded) > 0
    assert "₹1,500.00" in fallback_text  # Fallback produces grounded summary


# ── 6. AI Endpoints: Config, Test Connection, Usage ──────────────────────────

def test_ai_config_endpoint(client: TestClient):
    # GET initial config
    res = client.get("/api/ai/config")
    assert res.status_code == 200
    data = res.json()
    assert "provider" in data
    assert "provider_tier" in data

    # POST update to ollama
    update_res = client.post(
        "/api/ai/config",
        json={"provider": "ollama", "model": "qwen2.5:7b", "base_url": "http://localhost:11434/v1"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["provider"] == "ollama"
    assert update_res.json()["provider_tier"] == "Local"
    assert update_res.json()["is_free"] is True

    # Test connection on 'none' provider
    test_res = client.post("/api/ai/test-connection", json={"provider": "none"})
    assert test_res.status_code == 200
    assert test_res.json()["status"] == "ok"
    assert "offline" in test_res.json()["message"].lower()

    # Revert to 'none'
    client.post("/api/ai/config", json={"provider": "none"})


def test_ai_usage_endpoint_free_tier(client: TestClient):
    # Switch provider to none
    client.post("/api/ai/config", json={"provider": "none"})
    res = client.get("/api/ai/usage?user_id=1")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "none"
    assert data["is_free"] is True
    assert data["estimated_cost_inr"] == 0.0
    assert data["estimated_cost_usd"] == 0.0


# ── 7. Agent Offline Flow (Zero Network) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_runs_with_none_provider(db: Session):
    # Set provider to none
    settings.LLM_PROVIDER = "none"

    # Router handled query
    res = await run_agent(
        user_message="What are my subscriptions?",
        db=db,
        user_id=1,
    )
    assert res is not None
    assert "reply" in res
    assert len(res["reply"]) > 0

    # Non-router query falling back to offline mode cleanly
    res_unknown = await run_agent(
        user_message="Explain quantum mechanics and personal finance",
        db=db,
        user_id=1,
    )
    assert "offline mode" in res_unknown["reply"].lower()
    assert res_unknown.get("offline_mode") is True
