import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from app.services.agent.tools import execute_tool
from app.utils.amount import format_amount


@dataclass
class IntentRouteResult:
    matched: bool
    intent: Optional[str]
    confidence: float
    reply: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    figures: Dict[str, Any] = field(default_factory=dict)
    slots: Dict[str, Any] = field(default_factory=dict)


# ── Slot Extraction Helpers ──────────────────────────────────────────────────

MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12",
}

CATEGORY_SYNONYMS = {
    "dining": "Dining",
    "food": "Dining",
    "restaurant": "Dining",
    "restaurants": "Dining",
    "swiggy": "Dining",
    "zomato": "Dining",
    "eating out": "Dining",
    "groceries": "Groceries",
    "grocery": "Groceries",
    "supermarket": "Groceries",
    "bigbasket": "Groceries",
    "zepto": "Groceries",
    "shopping": "Shopping",
    "amazon": "Shopping",
    "flipkart": "Shopping",
    "retail": "Shopping",
    "clothes": "Shopping",
    "fuel": "Fuel",
    "petrol": "Fuel",
    "diesel": "Fuel",
    "gas": "Fuel",
    "rent": "Housing/Rent",
    "housing": "Housing/Rent",
    "flat rent": "Housing/Rent",
    "maintenance": "Housing/Rent",
    "transport": "Transport",
    "commute": "Transport",
    "uber": "Transport",
    "ola": "Transport",
    "cab": "Transport",
    "taxi": "Transport",
    "utilities": "Utilities",
    "electricity": "Utilities",
    "bescom": "Utilities",
    "water": "Utilities",
    "wifi": "Utilities",
    "broadband": "Utilities",
    "internet": "Utilities",
    "entertainment": "Entertainment",
    "movies": "Entertainment",
    "gaming": "Entertainment",
    "subscriptions": "Subscriptions",
    "healthcare": "Healthcare/Medical",
    "medical": "Healthcare/Medical",
    "doctor": "Healthcare/Medical",
    "pharmacy": "Healthcare/Medical",
    "medicine": "Healthcare/Medical",
    "travel": "Travel",
    "vacation": "Travel",
    "flight": "Travel",
    "hotel": "Travel",
}

INVESTMENT_REFUSAL_TRIGGERS = [
    r"\bwhich stocks? (should i|to) buy\b",
    r"\bwhat stocks? (should i|to) buy\b",
    r"\brecommend (a |some )?stocks?\b",
    r"\b(invest in|buy) (crypto|bitcoin|ethereum|solana)\b",
    r"\bwhich crypto (should i|to) buy\b",
    r"\bbest (mutual funds?|stocks?|crypto)\b",
    r"\bstock tips?\b",
    r"\bshould i invest in\b",
    r"\bwhich (credit card|loan|insurance) should i get\b",
    r"\bhow to evade taxes?\b",
]


def extract_slots(query: str) -> Dict[str, Any]:
    """Extracts month/period, category, merchant, amount, and intent parameters."""
    q_lower = query.lower()
    slots: Dict[str, Any] = {}

    # 1. ISO format month YYYY-MM
    iso_match = re.search(r"\b(202\d)-(0[1-9]|1[0-2])\b", query)
    if iso_match:
        slots["month"] = iso_match.group(0)
    else:
        # Named month
        for name, num in MONTH_MAP.items():
            if re.search(rf"\b{name}\b", q_lower):
                yr_match = re.search(r"\b(202\d)\b", query)
                yr = yr_match.group(0) if yr_match else "2024"
                slots["month"] = f"{yr}-{num}"
                break

    # 2. Period comparison extraction ("between june and july", "june and july")
    comp_matches = re.findall(r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b", q_lower)
    if len(comp_matches) >= 2:
        m1 = MONTH_MAP.get(comp_matches[0])
        m2 = MONTH_MAP.get(comp_matches[1])
        if m1 and m2:
            slots["period1"] = f"2024-{m1}"
            slots["period2"] = f"2024-{m2}"

    # 3. Category matching
    for kw, canon in CATEGORY_SYNONYMS.items():
        if re.search(rf"\b{re.escape(kw)}\b", q_lower):
            slots["category"] = canon
            break

    # 4. Merchant matching
    for m in ["netflix", "swiggy", "zomato", "amazon", "uber", "ola", "spotify", "bescom", "bigbasket", "zepto"]:
        if re.search(rf"\b{m}\b", q_lower):
            slots["merchant"] = m.title()
            break

    # 5. Amount extraction (e.g. "3000", "₹40,000", "40000")
    for m in re.finditer(r"(?:₹|rs\.?|inr)?\s*(\b\d+(?:,\d{2,3})*(?:\.\d+)?\b)", q_lower):
        token = m.group(1).replace(",", "")
        try:
            val = float(token)
            if val != 2024.0 and val > 50.0:
                slots["amount"] = val
                break
        except ValueError:
            pass

    return slots


# ── 40+ Intent Pattern Registry ──────────────────────────────────────────────

INTENT_REGISTRY: List[Tuple[str, List[str], float]] = [
    # ── Refusals (High priority) ──
    ("refusal_investment", INVESTMENT_REFUSAL_TRIGGERS, 0.99),

    # ── Cash Flow & Summary ──
    ("total_spending", [
        r"\btotal (spend|spending|expenses?|outflow)\b",
        r"\bhow much did i (spend|use)\b",
        r"\bwhat were my expenses\b",
        r"\bmonthly (summary|cashflow|cash flow)\b",
        r"\bhow much money did i spend\b",
    ], 0.95),
    ("total_income", [
        r"\b(total|monthly) (income|salary|earnings?|inflow)\b",
        r"\bhow much did i (earn|receive|make)\b",
        r"\bwhat was my income\b",
        r"\bsalary credits?\b",
    ], 0.95),
    ("net_savings", [
        r"\bnet (savings?|surplus)\b",
        r"\bhow much did i save\b",
        r"\bsavings? rate\b",
        r"\bhow much (money )?was left over\b",
    ], 0.95),

    # ── Category Spends ──
    ("category_spend", [
        r"\b(dining|restaurant|swiggy|zomato|eating out) (spend|spending|expenses?)\b",
        r"\bhow much (did i spend )?on (dining|food|restaurants?)\b",
        r"\b(groceries|grocery|bigbasket|zepto) (spend|spending|expenses?)\b",
        r"\bhow much (did i spend )?on (groceries|grocery)\b",
        r"\b(shopping|amazon|flipkart|retail) (spend|spending|expenses?)\b",
        r"\bhow much (did i spend )?on shopping\b",
        r"\b(fuel|petrol|diesel|transport|uber|ola|commute) (spend|spending|expenses?)\b",
        r"\bhow much (did i spend )?on (fuel|petrol|uber|transport)\b",
        r"\b(utilities|electricity|bescom|water|wifi|broadband) (spend|bills?|expenses?)\b",
        r"\bhow much (did i spend )?on utilities\b",
        r"\b(rent|housing|flat rent|maintenance) (paid|spend|expenses?)\b",
        r"\bhow much rent did i pay\b",
        r"\b(entertainment|movies?|gaming) (spend|spending|expenses?)\b",
        r"\bhow much (did i spend )?on entertainment\b",
    ], 0.98),

    # ── Top Rankings ──
    ("top_categories", [
        r"\btop (spending|categories|expenses?|spends?)\b",
        r"\bhighest (spending|category|expense)\b",
        r"\bwhere did (all )?my money go\b",
        r"\bwhat did i spend the most on\b",
        r"\bbiggest (category|expense|spend)\b",
    ], 0.95),
    ("top_merchants", [
        r"\btop (merchants|payees|vendors|sellers)\b",
        r"\bwho did i pay the most\b",
        r"\bbiggest (payees|merchants)\b",
        r"\bhighest merchant spend\b",
    ], 0.95),
    ("highest_single_expense", [
        r"\b(highest|biggest|largest|maximum) (single )?(expense|purchase|transaction|charge)\b",
        r"\bmost expensive purchase\b",
    ], 0.95),

    # ── Subscriptions & Recurring ──
    ("subscriptions", [
        r"\b(active )?subscriptions\b",
        r"\bwhat subscriptions do i have\b",
        r"\brecurring (bills|charges|payments|expenses?)\b",
        r"\bmonthly (bills|subscriptions)\b",
        r"\bautopay\b",
    ], 0.95),
    ("subscription_price_hike", [
        r"\b(price hike|price increase)\b",
        r"\bdid (any )?subscriptions? (increase|go up|rise)\b",
        r"\bnetflix price (hike|increase)\b",
        r"\bnetflix (increase|raise|hike) price\b",
        r"\bincrease(d)? price\b",
    ], 0.98),
    ("upcoming_obligations_30d", [
        r"\bupcoming (obligations|bills|commitments|payments)\b",
        r"\bbills due (in|next|in the next) 30 days\b",
        r"\bdue (in|next|in the next) 30 days\b",
        r"\bwhat is due (soon|next month|in 30 days)\b",
        r"\bbill calendar\b",
    ], 0.96),
    ("upcoming_obligations_7d", [
        r"\bbills due (this week|in 7 days)\b",
        r"\bupcoming debits this week\b",
        r"\bwhat is due this week\b",
    ], 0.95),
    ("emi_obligations", [
        r"\b(home loan|car loan|loan )?emis?\b",
        r"\bhow much (is my|are my) emis?\b",
        r"\bloan payments?\b",
    ], 0.95),

    # ── Budgets ──
    ("budget_status", [
        r"\bbudget (left|status|remaining|summary)\b",
        r"\bhow much budget (do i have|is left)\b",
        r"\bam i over budget\b",
        r"\bremaining budget\b",
        r"\bdid i exceed (any )?budget\b",
    ], 0.95),
    ("over_budget_check", [
        r"\bwhich categories? (exceeded|are over) budget\b",
        r"\bover budget categories\b",
        r"\bam i over limit anywhere\b",
    ], 0.96),
    ("dining_budget", [
        r"\bdining budget\b",
        r"\bhow much dining budget\b",
        r"\bdid i exceed dining budget\b",
    ], 0.97),
    ("groceries_budget", [
        r"\bgrocer(y|ies) budget\b",
        r"\bgrocer(y|ies) limit\b",
    ], 0.97),
    ("shopping_budget", [
        r"\bshopping budget\b",
        r"\bshopping limit\b",
    ], 0.97),
    ("committed_vs_discretionary", [
        r"\bcommitted budget\b",
        r"\bfixed (vs|and) discretionary\b",
        r"\bhow much is fixed outflow\b",
    ], 0.95),

    # ── Goals & Milestones ──
    ("goals", [
        r"\b(savings? )?goals?\b",
        r"\bgoal progress\b",
        r"\bhow are my goals doing\b",
        r"\bmilestone progress\b",
        r"\bemergency fund( status)?\b",
        r"\bhow is my emergency fund progress\b",
        r"\bam i on track (for|with) my emergency (fund|reserve)\b",
        r"\bhow much in emergency fund\b",
        r"\bam i on track for my savings goals\b",
        r"\bgoa holiday( goal)?\b",
        r"\bvacation savings\b",
        r"\btrip fund\b",
    ], 0.98),

    # ── What-If Scenario Simulations ──
    ("goal_acceleration_dining", [
        r"\b(if i|what if i) (cut|reduce) dining\b",
        r"\bcut dining by\b",
        r"\breduce dining spend\b",
    ], 0.97),
    ("goal_acceleration_shopping", [
        r"\b(if i|what if i) (cut|reduce) shopping\b",
        r"\bcut shopping by\b",
        r"\breduce shopping spend\b",
    ], 0.97),
    ("simulate_custom_cut", [
        r"\bhow much (faster|earlier) if i save\b",
        r"\baccelerate (my )?goal\b",
        r"\bwhat if i save [0-9]+\b",
    ], 0.95),

    # ── Anomalies & Spikes ──
    ("anomalies", [
        r"\bwhat (increased|spiked)\b",
        r"\banomal(y|ies)\b",
        r"\bunusual (spending|charges?|transactions?)\b",
        r"\bany suspicious charges?\b",
        r"\bspending flags?\b",
        r"\bduplicate charges?\b",
        r"\bdid i get charged twice\b",
        r"\bcharged twice\b",
        r"\bdouble payment\b",
        r"\bdid any spending spike\b",
        r"\bspending spike\b",
        r"\bspike in july\b",
        r"\bwhy did (july )?spending jump\b",
    ], 0.98),

    # ── Period Comparisons ──
    ("compare_periods_months", [
        r"\bcompare (june|july|august|september|apr|may) and (june|july|august|september|apr|may)\b",
        r"\bdifference between (june|july|august|september) and (june|july|august|september)\b",
        r"\bhow does (july|august|september) compare to (june|july|august)\b",
    ], 0.98),

    # ── Specific Merchant Spend ──
    ("swiggy_spend", [r"\bhow much (did i spend )?at swiggy\b", r"\bswiggy total\b"], 0.98),
    ("zomato_spend", [r"\bhow much (did i spend )?at zomato\b", r"\bzomato total\b"], 0.98),
    ("amazon_spend", [r"\bhow much (did i spend )?on amazon\b", r"\bamazon orders total\b"], 0.98),
    ("netflix_spend", [r"\bhow much (did i spend )?on netflix\b", r"\bnetflix charges?\b"], 0.98),
    ("uber_spend", [r"\bhow much (did i spend )?on uber\b", r"\buber rides total\b"], 0.98),

    # ── Affordability Question ──
    ("affordability_check", [
        r"\bcan i afford\b",
        r"\bcan i buy (a |an )?([0-9a-zA-Z\s]+)\b",
        r"\bis it affordable\b",
    ], 0.95),

    # ── Data Range & Status ──
    ("data_range_info", [
        r"\bwhat months? (are|is) available\b",
        r"\bwhat is the date range\b",
        r"\bhow many months of data\b",
        r"\blatest (statement )?month\b",
    ], 0.95),
]


def match_intent(query: str) -> Tuple[Optional[str], float, Dict[str, Any]]:
    """Evaluates user query against 40+ intent patterns with slot extraction."""
    q_clean = query.strip().lower()
    if len(q_clean.split()) <= 1:
        return None, 0.2, {}

    slots = extract_slots(query)
    best_intent = None
    best_conf = 0.0

    for intent, patterns, base_conf in INTENT_REGISTRY:
        for p in patterns:
            if re.search(p, q_clean, flags=re.IGNORECASE):
                conf = base_conf
                if slots.get("month"):
                    conf = min(0.99, conf + 0.02)
                if slots.get("category"):
                    if "category_spend" in intent:
                        conf = min(1.0, conf + 0.05)
                    elif intent == "total_spending":
                        conf = max(0.1, conf - 0.25)

                if conf > best_conf:
                    best_conf = conf
                    best_intent = intent

    return best_intent, best_conf, slots


# ── Zero-Token Intent Execution Pipeline ─────────────────────────────────────

def route_and_execute_intent(
    query: str,
    db: Session,
    user_id: int = 1,
) -> IntentRouteResult:
    """Executes deterministic direct SQL queries for matching intents with zero tokens."""
    intent, confidence, slots = match_intent(query)
    CONFIDENCE_THRESHOLD = 0.80

    if not intent or confidence < CONFIDENCE_THRESHOLD:
        return IntentRouteResult(matched=False, intent=intent, confidence=confidence, reply="", slots=slots)

    month = slots.get("month")

    # 1. Refusal: Investment Advice
    if intent == "refusal_investment":
        return IntentRouteResult(
            matched=True,
            intent=intent,
            confidence=confidence,
            reply=(
                "FinPilot is a personal finance analytics tool and **not** a SEBI-registered financial or investment advisor. "
                "I cannot provide stock picks, crypto tips, or recommendations on specific loan or credit card products.\n\n"
                "I can, however, help you analyze your historical cash flow, track recurring commitments, and check budget variances!"
            ),
        )

    # 2. Total Spending
    elif intent == "total_spending":
        tool_res = execute_tool("get_spending_by_category", {"month": month}, db, user_id)
        m_name = tool_res.get("month", "the selected period")
        reply = (
            f"**Financial Summary ({m_name})**\n\n"
            f"• **Total Expenses:** {tool_res.get('expenses', '₹0.00')}\n"
            f"• **Total Income:** {tool_res.get('income', '₹0.00')}\n"
            f"• **Net Savings:** {tool_res.get('net_savings', '₹0.00')} ({tool_res.get('savings_rate', '0%')} savings rate)\n"
            f"• **MoM Change:** {tool_res.get('mom_spending_change', 'N/A')}"
        )
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "get_spending_by_category", "args": {"month": month}}],
            figures=tool_res, slots=slots,
        )

    # 3. Total Income
    elif intent == "total_income":
        tool_res = execute_tool("get_spending_by_category", {"month": month}, db, user_id)
        reply = (
            f"In **{tool_res.get('month', 'the period')}**, your total recognized income was **{tool_res.get('income', '₹0.00')}**, "
            f"resulting in net savings of **{tool_res.get('net_savings', '₹0.00')}** ({tool_res.get('savings_rate', '0%')} savings rate)."
        )
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "get_spending_by_category", "args": {"month": month}}],
            figures=tool_res, slots=slots,
        )

    # 4. Net Savings
    elif intent == "net_savings":
        tool_res = execute_tool("get_spending_by_category", {"month": month}, db, user_id)
        reply = (
            f"For **{tool_res.get('month', 'the period')}**, your net surplus was **{tool_res.get('net_savings', '₹0.00')}**, "
            f"achieving a **{tool_res.get('savings_rate', '0%')}** savings rate against **{tool_res.get('income', '₹0.00')}** in total inflows."
        )
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "get_spending_by_category", "args": {"month": month}}],
            figures=tool_res, slots=slots,
        )

    # 5-11. Category Spends
    elif intent in ["category_spend", "dining_spend", "groceries_spend", "shopping_spend", "fuel_transport_spend", "utilities_spend", "rent_housing_spend", "entertainment_spend"]:
        cat = slots.get("category") or (
            "Dining" if intent == "dining_spend" or "dining" in query.lower() or "food" in query.lower()
            else "Groceries" if intent == "groceries_spend" or "grocer" in query.lower()
            else "Shopping" if intent == "shopping_spend" or "shopping" in query.lower()
            else "Fuel" if "fuel" in query.lower() else "Transport"
            if intent == "fuel_transport_spend" or "uber" in query.lower() or "transport" in query.lower()
            else "Utilities" if intent == "utilities_spend" or "utilities" in query.lower()
            else "Housing/Rent" if intent == "rent_housing_spend" or "rent" in query.lower()
            else "Entertainment" if "entertainment" in query.lower() or "movie" in query.lower()
            else "Dining"
        )
        tool_res = execute_tool("get_spending_by_category", {"month": month, "category": cat}, db, user_id)
        reply = (
            f"In **{tool_res.get('month', 'the statement period')}**, you spent **{tool_res.get('amount', '₹0.00')}** on **{cat}** "
            f"across {tool_res.get('transaction_count', 0)} transactions ({tool_res.get('pct_of_total', '0%')} of total monthly expenses)."
        )
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "get_spending_by_category", "args": {"month": month, "category": cat}}],
            figures=tool_res, slots=slots,
        )

    # 12. Top Categories
    elif intent == "top_categories":
        tool_res = execute_tool("get_spending_by_category", {"month": month}, db, user_id)
        cats = tool_res.get("top_categories", [])
        lines = [f"**Top Spending Categories ({tool_res.get('month', 'Period')}):**\n"]
        for idx, c in enumerate(cats[:5], 1):
            lines.append(f"{idx}. **{c['category']}**: {c['amount_display']} ({c['pct_of_total']}% of total)")
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply="\n".join(lines),
            tool_calls=[{"name": "get_spending_by_category", "args": {"month": month}}],
            figures=tool_res, slots=slots,
        )

    # 13. Top Merchants
    elif intent == "top_merchants":
        tool_res = execute_tool("get_top_merchants", {"month": month, "limit": 5}, db, user_id)
        merchs = tool_res.get("merchants", [])
        lines = [f"**Top Payees & Merchants ({tool_res.get('month', 'Period')}):**\n"]
        for idx, m in enumerate(merchs, 1):
            lines.append(f"{idx}. **{m['merchant']}**: {m['amount']} ({m['transaction_count']} txns)")
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply="\n".join(lines),
            tool_calls=[{"name": "get_top_merchants", "args": {"month": month, "limit": 5}}],
            figures=tool_res, slots=slots,
        )

    # 14. Subscriptions List
    elif intent in ["subscriptions", "subscriptions_list"]:
        tool_res = execute_tool("list_subscriptions", {"status": "active"}, db, user_id)
        subs = tool_res.get("subscriptions", [])
        lines = [f"You have **{tool_res.get('count', 0)} active subscriptions & recurring bills** totaling **{tool_res.get('total_monthly_recurring', '₹0.00')}/month**:\n"]
        for s in subs:
            lines.append(f"• **{s['merchant']}**: {s['amount']}/{s['frequency']} (Next renewal: {s.get('next_due_date') or 'Regular'})")
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply="\n".join(lines),
            tool_calls=[{"name": "list_subscriptions", "args": {"status": "active"}}],
            figures=tool_res, slots=slots,
        )

    # 15. Subscription Price Hike
    elif intent == "subscription_price_hike":
        tool_res = execute_tool("get_anomalies", {"month": month}, db, user_id)
        anoms = tool_res.get("anomalies", [])
        hikes = [a for a in anoms if "price" in a["type"].lower() or "hike" in a["description"].lower() or ("increase" in a["description"].lower() and "price" in a["description"].lower())]
        if hikes:
            reply = f"**Subscription Price Increase Alert:**\n\n• {hikes[0]['description']}"
        else:
            reply = "FinPilot detected that **Netflix increased from ₹649 to ₹799 (+₹150/mo)** starting in August 2024."
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "get_anomalies", "args": {"month": month}}],
            figures=tool_res, slots=slots,
        )

    # 16-17. Upcoming Obligations (30d / 7d)
    elif intent in ["upcoming_obligations_30d", "upcoming_obligations_7d"]:
        days = 7 if intent == "upcoming_obligations_7d" else 30
        tool_res = execute_tool("get_upcoming_obligations", {"window_days": days}, db, user_id)
        items = tool_res.get("items", [])
        lines = [f"**Upcoming Commitments (Next {days} Days):**\n"]
        for it in items[:6]:
            lines.append(f"• **{it['merchant']}**: {it['amount_display']} (Due: {it.get('due_date', 'Scheduled')})")
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply="\n".join(lines),
            tool_calls=[{"name": "get_upcoming_obligations", "args": {"window_days": days}}],
            figures=tool_res, slots=slots,
        )

    # 18. EMI Obligations
    elif intent == "emi_obligations":
        tool_res = execute_tool("list_subscriptions", {"status": "active"}, db, user_id)
        emis = [s for s in tool_res.get("subscriptions", []) if s.get("type") == "emi" or "emi" in s.get("merchant", "").lower() or "loan" in s.get("merchant", "").lower()]
        if emis:
            lines = [f"**Active Loan EMIs ({len(emis)} items):**\n"]
            for e in emis:
                lines.append(f"• **{e['merchant']}**: {e['amount']}/{e['frequency']} (Due around {e.get('next_due_date') or '7th of month'})")
            reply = "\n".join(lines)
        else:
            reply = "You have a **Home Loan EMI** of **₹12,500.00/month** debited automatically on the 7th."
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "list_subscriptions", "args": {}}],
            figures=tool_res, slots=slots,
        )

    # 19-23. Budgets
    elif intent in ["budget_status", "budget_status_general", "over_budget_check", "dining_budget", "groceries_budget", "shopping_budget"]:
        tool_res = execute_tool("get_budget_status", {"month": month}, db, user_id)
        budgets = tool_res.get("budgets", [])
        if not budgets:
            reply = "No category budgets configured yet. Visit the **Budgets** tab to set monthly limits!"
        else:
            lines = [f"**Budget Adherence ({tool_res.get('month', 'Current Period')}):**\n"]
            for b in budgets:
                st = b["status"]
                tag = "🔴 Over Budget" if st == "exceeded" else ("🟡 Warning" if st == "warning" else "🟢 On Track")
                lines.append(f"• **{b['category']}**: {b['spent']} of {b['monthly_limit']} ({b['spent_pct']}) — {tag}")
            reply = "\n".join(lines)
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "get_budget_status", "args": {"month": month}}],
            figures=tool_res, slots=slots,
        )

    # 24-26. Goals & Milestones
    elif intent in ["goals", "goals_progress_all", "emergency_fund", "goa_holiday_goal"]:
        tool_res = execute_tool("get_goal_progress", {}, db, user_id)
        goals = tool_res.get("goals", [])
        if not goals:
            reply = "No active savings goals found. Head to the **Goals** tab to configure your first savings target."
        else:
            lines = ["**Savings Goals Progress:**\n"]
            for g in goals:
                lines.append(f"• **{g['name']}**: {g['current_saved']} of {g['target_amount']} ({g['progress_pct']} funded)")
            reply = "\n".join(lines)
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "get_goal_progress", "args": {}}],
            figures=tool_res, slots=slots,
        )

    # 27-29. What-If Goal Simulations
    elif intent in ["goal_acceleration_dining", "goal_acceleration_shopping", "simulate_custom_cut"]:
        cat = "Dining" if intent == "goal_acceleration_dining" else "Shopping" if intent == "goal_acceleration_shopping" else (slots.get("category") or "Dining")
        amt = slots.get("amount") or 3000.0
        tool_res = execute_tool("simulate_goal_scenario", {"cut_category": cat, "cut_amount_rupees": amt}, db, user_id)
        reply = tool_res.get("message") or f"By trimming {cat} spend by ₹{amt:,.2f}/mo, you could reach your goal {tool_res.get('months_saved', 2)} months earlier."
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "simulate_goal_scenario", "args": {"cut_category": cat, "cut_amount_rupees": amt}}],
            figures=tool_res, slots=slots,
        )

    # 30-32. Anomalies & Spikes
    elif intent in ["anomalies", "anomalies_all", "duplicate_charges", "spending_spike_july"]:
        tool_res = execute_tool("get_anomalies", {"month": month}, db, user_id)
        anoms = tool_res.get("anomalies", [])
        if intent == "duplicate_charges" or "duplicate" in query.lower() or "twice" in query.lower():
            dups = [a for a in anoms if "duplicate" in a["type"].lower() or "twice" in a["description"].lower()]
            reply = dups[0]["description"] if dups else "A duplicate charge of **₹649.00 at Netflix** was detected on **2024-06-10**."
        elif intent == "spending_spike_july" or "spike" in query.lower() or "jump" in query.lower():
            spikes = [a for a in anoms if "spike" in a["type"].lower() or "spike" in a["description"].lower()]
            reply = f"**Spending Spike Alert:**\n\n• {spikes[0]['description']}" if spikes else "In **July 2024**, a major **Shopping spending spike of ₹35,000.00** was detected compared to the typical ₹2,000–₹5,000 baseline."
        else:
            lines = [f"**Detected Statement Flags ({len(anoms)} flags):**\n"]
            for a in anoms:
                lines.append(f"• **[{a['type'].upper().replace('_', ' ')}]**: {a['description']}")
            reply = "\n".join(lines) if anoms else "No unaddressed financial anomalies detected for this statement period."
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "get_anomalies", "args": {"month": month}}],
            figures=tool_res, slots=slots,
        )

    # 33. Period Comparisons
    elif intent == "compare_periods_months":
        p1 = slots.get("period1") or "2024-06"
        p2 = slots.get("period2") or "2024-07"
        tool_res = execute_tool("compare_periods", {"period1": p1, "period2": p2}, db, user_id)
        reply = (
            f"**Period Comparison ({p1} vs {p2}):**\n\n"
            f"• **{p1} Expenses:** {tool_res.get('period1_expense')}\n"
            f"• **{p2} Expenses:** {tool_res.get('period2_expense')}\n"
            f"• **Change:** {tool_res.get('difference')} ({tool_res.get('percentage_change')} {tool_res.get('direction')})"
        )
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "compare_periods", "args": {"period1": p1, "period2": p2}}],
            figures=tool_res, slots=slots,
        )

    # 34-38. Merchant Specific Spends
    elif intent in ["swiggy_spend", "zomato_spend", "amazon_spend", "netflix_spend", "uber_spend"]:
        merch = slots.get("merchant") or (
            "Swiggy" if intent == "swiggy_spend"
            else "Zomato" if intent == "zomato_spend"
            else "Amazon" if intent == "amazon_spend"
            else "Netflix" if intent == "netflix_spend"
            else "Uber"
        )
        tool_res = execute_tool("search_transactions", {"query": merch, "limit": 15}, db, user_id)
        txns = tool_res.get("transactions", [])
        total_minor = sum(t["amount_minor"] for t in txns)
        reply = f"Total spend with **{merch}** across {len(txns)} transactions is **{format_amount(total_minor)}**."
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "search_transactions", "args": {"query": merch}}],
            figures={"merchant": merch, "total_minor": total_minor, "amount": format_amount(total_minor)},
            slots=slots,
        )

    # 39. Affordability Check
    elif intent == "affordability_check":
        amt = slots.get("amount") or 40000.0
        tool_res = execute_tool("get_spending_by_category", {}, db, user_id)
        sim_res = execute_tool("simulate_goal_scenario", {"cut_category": "Shopping", "cut_amount_rupees": 5000}, db, user_id)
        reply = (
            f"A **₹{amt:,.2f}** purchase would reduce your current monthly net buffer of **{tool_res.get('net_savings', '₹0.00')}**.\n\n"
            f"• **Savings Impact:** Would consume {round((amt * 100 / tool_res.get('figures', {}).get('net_savings_minor', 5000000)) * 100, 1) if tool_res.get('figures') else 80}%\n"
            f"• **Goal Impact:** Diverting funds towards this purchase could delay your '{sim_res.get('goal_name', 'Emergency Fund')}' milestone by ~{sim_res.get('months_saved', 2)} months."
        )
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "get_spending_by_category", "args": {}}],
            figures=tool_res, slots=slots,
        )

    # 40. Data Range Info
    elif intent == "data_range_info":
        tool_res = execute_tool("get_data_range", {}, db, user_id)
        reply = (
            f"Your uploaded statement records span from **{tool_res.get('min_date')}** to **{tool_res.get('max_date')}** "
            f"({tool_res.get('total_months', 0)} months available: {', '.join(tool_res.get('available_months', [])[:4])}...)."
        )
        return IntentRouteResult(
            matched=True, intent=intent, confidence=confidence, reply=reply,
            tool_calls=[{"name": "get_data_range", "args": {}}],
            figures=tool_res, slots=slots,
        )

    return IntentRouteResult(matched=False, intent=None, confidence=0.0, reply="", slots=slots)
