import json
import os
import re
from typing import Optional, Tuple, List, Dict, Any

DEFAULT_RULES_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "seed", "rules_dict.json"
)
USER_RULES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "user_rules"
)


def _get_user_rules_file(user_id: int) -> str:
    os.makedirs(USER_RULES_DIR, exist_ok=True)
    return os.path.join(USER_RULES_DIR, f"user_{user_id}_rules.json")


def load_user_rules(user_id: int) -> List[Dict[str, Any]]:
    path = _get_user_rules_file(user_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("rules", [])
    except Exception:
        return []


def add_user_rule(
    user_id: int,
    keyword: str,
    category: str,
    subcategory: Optional[str] = None,
    direction: Optional[str] = None,
) -> None:
    path = _get_user_rules_file(user_id)
    rules = load_user_rules(user_id)

    kw_clean = keyword.strip().lower()
    if not kw_clean:
        return

    # Update if keyword already exists
    updated = False
    for r in rules:
        if kw_clean in [k.lower() for k in r.get("keywords", [])]:
            r["category"] = category
            r["subcategory"] = subcategory
            if direction:
                r["direction"] = direction
            updated = True
            break

    if not updated:
        rules.insert(
            0,
            {
                "keywords": [kw_clean],
                "category": category,
                "subcategory": subcategory,
                "direction": direction,
            },
        )

    with open(path, "w", encoding="utf-8") as f:
        json.dump({"rules": rules}, f, indent=2)


def load_default_rules() -> List[Dict[str, Any]]:
    if not os.path.exists(DEFAULT_RULES_FILE):
        return []
    try:
        with open(DEFAULT_RULES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("rules", [])
    except Exception:
        return []


def match_rule(
    raw_description: str,
    merchant_hint: Optional[str] = None,
    user_id: int = 1,
) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
    """Matches raw description or merchant hint against user rules, then default rules.

    Returns (category, subcategory, direction) or None.
    """
    targets = []
    if merchant_hint:
        targets.append(merchant_hint.strip().lower())
    if raw_description:
        targets.append(raw_description.strip().lower())

    if not targets:
        return None

    # 1. User rules take highest precedence
    user_rules = load_user_rules(user_id)
    for rule in user_rules:
        for kw in rule.get("keywords", []):
            kw_low = kw.strip().lower()
            for text in targets:
                if re.search(r"\b" + re.escape(kw_low) + r"\b", text):
                    return (
                        rule["category"],
                        rule.get("subcategory"),
                        rule.get("direction"),
                    )

    # 2. Default taxonomy rules
    default_rules = load_default_rules()
    for rule in default_rules:
        for kw in rule.get("keywords", []):
            kw_low = kw.strip().lower()
            for text in targets:
                if re.search(r"\b" + re.escape(kw_low) + r"\b", text):
                    return (
                        rule["category"],
                        rule.get("subcategory"),
                        rule.get("direction"),
                    )

    return None
