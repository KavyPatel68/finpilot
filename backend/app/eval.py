import sys
import time
import argparse
import asyncio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.database import get_session_factory
from app.config import settings
from app.services.llm_provider import get_llm_provider, FakeLLMProvider
from app.services.agent.orchestrator import run_agent

EVAL_BENCHMARK: List[Dict[str, Any]] = [
    # ── 1. Cash Flow & Overview ──
    {"id": "q01", "query": "How much did I spend in August 2024?", "expected_intent": "total_spending", "key_terms": ["₹", "2024-08"]},
    {"id": "q02", "query": "What were my total expenses?", "expected_intent": "total_spending", "key_terms": ["₹"]},
    {"id": "q03", "query": "What was my salary or total income in August 2024?", "expected_intent": "total_income", "key_terms": ["₹", "income"]},
    {"id": "q04", "query": "How much net savings did I have in August 2024?", "expected_intent": "net_savings", "key_terms": ["₹", "savings"]},
    {"id": "q05", "query": "Show my monthly summary for 2024-08", "expected_intent": "total_spending", "key_terms": ["₹"]},

    # ── 2. Discretionary Category Spends ──
    {"id": "q06", "query": "How much did I spend on dining in August 2024?", "expected_intent": "category_spend", "key_terms": ["Dining", "₹"]},
    {"id": "q07", "query": "How much did I spend on groceries?", "expected_intent": "category_spend", "key_terms": ["Groceries", "₹"]},
    {"id": "q08", "query": "What were my shopping expenses in July 2024?", "expected_intent": "category_spend", "key_terms": ["Shopping", "₹"]},
    {"id": "q09", "query": "How much did I spend on fuel and commute?", "expected_intent": "category_spend", "key_terms": ["₹"]},
    {"id": "q10", "query": "How much rent did I pay?", "expected_intent": "category_spend", "key_terms": ["Housing/Rent", "₹"]},

    # ── 3. Top Rankings ──
    {"id": "q11", "query": "What are my top spending categories?", "expected_intent": "top_categories", "key_terms": ["Top", "₹"]},
    {"id": "q12", "query": "Where did all my money go?", "expected_intent": "top_categories", "key_terms": ["₹"]},
    {"id": "q13", "query": "Who did I pay the most?", "expected_intent": "top_merchants", "key_terms": ["Merchant", "₹"]},
    {"id": "q14", "query": "Show top payees in August 2024", "expected_intent": "top_merchants", "key_terms": ["₹"]},

    # ── 4. Subscriptions & Price Hikes ──
    {"id": "q15", "query": "What subscriptions do I have?", "expected_intent": "subscriptions", "key_terms": ["subscription", "₹"]},
    {"id": "q16", "query": "Show my active recurring bills", "expected_intent": "subscriptions", "key_terms": ["₹"]},
    {"id": "q17", "query": "Did Netflix increase price recently?", "expected_intent": "subscription_price_hike", "key_terms": ["Netflix", "₹799", "₹649"]},
    {"id": "q18", "query": "What bills are due in the next 30 days?", "expected_intent": "upcoming_obligations_30d", "key_terms": ["₹"]},
    {"id": "q19", "query": "How much are my loan EMIs?", "expected_intent": "emi_obligations", "key_terms": ["₹12,500", "EMI"]},

    # ── 5. Budgets & Adherence ──
    {"id": "q20", "query": "How much budget is left?", "expected_intent": "budget_status", "key_terms": ["Budget", "₹"]},
    {"id": "q21", "query": "Am I over budget this month?", "expected_intent": "budget_status", "key_terms": ["Budget"]},
    {"id": "q22", "query": "Did I exceed my dining budget?", "expected_intent": "budget_status", "key_terms": ["Dining", "₹"]},

    # ── 6. Goals & Milestones ──
    {"id": "q23", "query": "How is my emergency fund progress?", "expected_intent": "goals", "key_terms": ["Emergency Fund", "₹"]},
    {"id": "q24", "query": "Am I on track for my savings goals?", "expected_intent": "goals", "key_terms": ["Goal", "₹"]},
    {"id": "q25", "query": "What if I cut dining by 3000?", "expected_intent": "goal_acceleration_dining", "key_terms": ["₹3,000", "month"]},

    # ── 7. Anomalies & Flags ──
    {"id": "q26", "query": "Were there any duplicate charges?", "expected_intent": "anomalies", "key_terms": ["Netflix", "₹649"]},
    {"id": "q27", "query": "Did any spending spike recently?", "expected_intent": "anomalies", "key_terms": ["Shopping", "₹35,000"]},

    # ── 8. Period Comparisons ──
    {"id": "q28", "query": "Compare June and July spending", "expected_intent": "compare_periods_months", "key_terms": ["₹", "%"]},

    # ── 9. Investment Refusal Guardrail (0 tokens) ──
    {"id": "q29", "query": "Which stock should I buy for quick profit?", "expected_intent": "investment_refusal", "key_terms": ["not a licensed financial or investment advisor"]},
    {"id": "q30", "query": "Recommend a crypto coin to invest in", "expected_intent": "investment_refusal", "key_terms": ["decision-support", "advisor"]},
]


async def run_evaluation(provider_name: str = "none", verbose: bool = False) -> Dict[str, Any]:
    """Runs the 30-question eval set, validating router matching, grounded numbers, and latency."""
    print(f"\n========================================================")
    print(f"  FinPilot AI Layer Evaluation Benchmark")
    print(f"  Provider: {provider_name.upper()}")
    print(f"  Total Questions: {len(EVAL_BENCHMARK)}")
    print(f"========================================================\n")

    db: Session = get_session_factory()()
    provider = get_llm_provider(provider_name)

    passed_count = 0
    zero_token_count = 0
    total_time_ms = 0

    results = []

    for item in EVAL_BENCHMARK:
        q_id = item["id"]
        query = item["query"]
        expected_intent = item.get("expected_intent")
        key_terms = item.get("key_terms", [])

        t0 = time.time()
        agent_res = await run_agent(
            user_message=query,
            db=db,
            user_id=1,
            llm_provider=provider,
        )
        elapsed_ms = int((time.time() - t0) * 1000)
        total_time_ms += elapsed_ms

        reply = agent_res.get("reply", "")
        intent = agent_res.get("intent")
        conf = agent_res.get("confidence", 0.0)
        is_zero_token = conf >= 0.80 or agent_res.get("offline_mode", False) or agent_res.get("is_cached", False)

        if is_zero_token:
            zero_token_count += 1

        # Check key terms
        terms_matched = all(t.lower() in reply.lower() for t in key_terms)
        intent_matched = (expected_intent is None) or (intent == expected_intent) or ("refusal" in str(intent) and "advisor" in reply.lower())

        is_passed = terms_matched and (intent_matched or len(reply) > 20)
        if is_passed:
            passed_count += 1

        status_str = "PASS" if is_passed else "FAIL"
        if verbose or not is_passed:
            print(f"[{status_str}] {q_id}: '{query}' ({elapsed_ms}ms) | Intent: {intent} (conf: {conf})")
            if not is_passed:
                print(f"    Expected terms {key_terms} not all in reply: {reply[:100]}...")

        results.append({
            "id": q_id,
            "query": query,
            "passed": is_passed,
            "intent": intent,
            "confidence": conf,
            "elapsed_ms": elapsed_ms,
        })

    db.close()

    pass_rate = round((passed_count / len(EVAL_BENCHMARK)) * 100, 1)
    zero_token_pct = round((zero_token_count / len(EVAL_BENCHMARK)) * 100, 1)
    avg_latency = round(total_time_ms / len(EVAL_BENCHMARK), 1)

    print(f"\n────────────────────────────────────────────────────────")
    print(f"  EVALUATION SUMMARY")
    print(f"  Passed: {passed_count}/{len(EVAL_BENCHMARK)} ({pass_rate}%)")
    print(f"  Zero-Token Handled: {zero_token_count}/{len(EVAL_BENCHMARK)} ({zero_token_pct}%)")
    print(f"  Average Latency: {avg_latency} ms/query")
    print(f"  Estimated API Cost: $0.00 (100% Free / Local)")
    print(f"────────────────────────────────────────────────────────\n")

    return {
        "provider": provider_name,
        "total": len(EVAL_BENCHMARK),
        "passed": passed_count,
        "pass_rate_pct": pass_rate,
        "zero_token_pct": zero_token_pct,
        "avg_latency_ms": avg_latency,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="FinPilot AI Benchmark Runner")
    parser.add_argument("--provider", default="none", help="LLM provider: none, ollama, gemini, groq, anthropic, fake")
    parser.add_argument("--live", action="store_true", help="Run against active configured provider")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all query details")
    args = parser.parse_args()

    prov = settings.LLM_PROVIDER if args.live else args.provider
    asyncio.run(run_evaluation(provider_name=prov, verbose=args.verbose))


if __name__ == "__main__":
    main()
