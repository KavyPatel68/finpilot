import re
from typing import Any, Dict, List, Union

# Indian PAN: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F)
PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", re.IGNORECASE)

# Indian IFSC: 4 letters, 0, 6 alphanumeric (e.g. HDFC0001234)
IFSC_REGEX = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", re.IGNORECASE)

# Indian Bank Account Number: 9 to 18 contiguous digits
ACCOUNT_REGEX = re.compile(r"\b\d{9,18}\b")

# Phone numbers: 10 digits starting with 6-9, optional +91 prefix
PHONE_REGEX = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")

# Email addresses
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def anonymize_text(text: str) -> str:
    """Strips PII (PAN, IFSC, Bank Accounts, Phone, Email) from text before sending to LLMs."""
    if not text:
        return text

    sanitized = PAN_REGEX.sub("[PAN_REDACTED]", text)
    sanitized = IFSC_REGEX.sub("[IFSC_REDACTED]", sanitized)
    sanitized = PHONE_REGEX.sub("[PHONE_REDACTED]", sanitized)
    sanitized = ACCOUNT_REGEX.sub("[ACCOUNT_REDACTED]", sanitized)
    sanitized = EMAIL_REGEX.sub("[EMAIL_REDACTED]", sanitized)
    return sanitized


def sanitize_tool_result(data: Any) -> Any:
    """Recursively anonymizes and strips sensitive transaction narration and account info

    from tool outputs before passing to any cloud LLM context.
    """
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if k in ("account_number", "account_number_masked", "user_id", "id", "document_id"):
                continue
            if k == "raw_description":
                # Only keep merchant_normalized or generic sanitized description
                cleaned["description"] = anonymize_text(str(v))[:60] if v else ""
                continue
            cleaned[k] = sanitize_tool_result(v)
        return cleaned
    elif isinstance(data, list):
        return [sanitize_tool_result(item) for item in data]
    elif isinstance(data, str):
        return anonymize_text(data)
    else:
        return data
