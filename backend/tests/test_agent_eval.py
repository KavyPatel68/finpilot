import pytest
from sqlalchemy.orm import Session
from app.services.llm_provider import FakeLLMProvider
from app.services.agent.orchestrator import run_agent
from app.eval import EVAL_BENCHMARK


@pytest.mark.asyncio
async def test_30_question_eval_benchmark(db: Session):
    """Evaluates all 30 financial questions in the benchmark suite with a fake/offline provider,

    verifying 100% execution success, zero crash, and high zero-token coverage.
    """
    fake_provider = FakeLLMProvider(canned_response="Evaluated financial metrics.")

    passed = 0
    zero_token_count = 0

    for item in EVAL_BENCHMARK:
        query = item["query"]
        expected_intent = item.get("expected_intent")

        res = await run_agent(
            user_message=query,
            db=db,
            user_id=1,
            llm_provider=fake_provider,
        )

        assert res is not None
        assert "reply" in res
        assert len(res["reply"]) > 0

        intent = res.get("intent")
        conf = res.get("confidence", 0.0)

        if conf >= 0.80 or res.get("offline_mode", False) or res.get("is_cached", False):
            zero_token_count += 1

        # Check that refusal triggers properly
        if expected_intent == "investment_refusal":
            assert "not a licensed financial or investment advisor" in res["reply"].lower()

        passed += 1

    assert passed == len(EVAL_BENCHMARK)
    # At least 70% of domain questions should be caught by the 40+ zero-token intent router
    assert (zero_token_count / len(EVAL_BENCHMARK)) >= 0.70
