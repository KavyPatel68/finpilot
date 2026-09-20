import re
from dataclasses import dataclass
from typing import Optional

@dataclass  
class NarrationInfo:
    payment_method: Optional[str]  # UPI, NEFT, IMPS, RTGS, ATM, POS, NACH, ACH, ECS, ENACH
    merchant_hint: Optional[str]   # extracted merchant name from narration
    reference_number: Optional[str]
    is_likely_transfer: bool       # NEFT/RTGS between accounts = likely transfer
    
def classify_narration(raw: str) -> NarrationInfo:
    raw_upper = raw.upper()
    
    method = None
    merchant = None
    ref = None
    is_transfer = False
    
    # Check for likely transfer
    if any(x in raw_upper for x in ["NEFT", "RTGS"]):
        is_transfer = True

    # UPI
    if "UPI" in raw_upper:
        method = "UPI"
        # pattern like UPI/DR/123456789/Swiggy or UPI/123456789/Swiggy
        parts = raw.split('/')
        for part in parts:
            if part.isdigit() and len(part) >= 6:
                ref = part
            elif part.upper() not in ("UPI", "DR", "CR") and not (part.isdigit() and len(part) >= 6):
                if merchant is None:
                    merchant = part.strip()
    
    # IMPS
    elif "IMPS" in raw_upper:
        method = "IMPS"
        parts = raw.split('/')
        for part in parts:
            if part.isdigit() and len(part) >= 6:
                ref = part
            elif part.upper() not in ("IMPS", "DR", "CR"):
                if merchant is None:
                    merchant = part.strip()
                    
    # NEFT / RTGS
    elif "NEFT" in raw_upper or "RTGS" in raw_upper:
        method = "NEFT" if "NEFT" in raw_upper else "RTGS"
        parts = re.split(r'[-/:]', raw)
        for part in parts:
            if "REF" in part.upper():
                ref_match = re.search(r'\d+', part)
                if ref_match:
                    ref = ref_match.group(0)
            elif part.upper() not in ("NEFT", "RTGS", "INWARD", "OUTWARD") and "REF" not in part.upper():
                if merchant is None and part.strip():
                    merchant = part.strip()

    # ATM
    elif "ATM" in raw_upper:
        method = "ATM"
        parts = raw.split('/')
        for part in parts:
            if part.isdigit() and len(part) >= 6:
                ref = part
        merchant = None

    # POS
    elif "POS" in raw_upper:
        method = "POS"
        parts = raw.split('/')
        for part in parts:
            if part.isdigit() and len(part) >= 4:
                ref = part
            elif part.upper() not in ("POS",):
                if merchant is None and part.strip():
                    merchant = part.strip()
                    
    # NACH / ACH
    elif "NACH" in raw_upper or "ACH" in raw_upper:
        method = "NACH" if "NACH" in raw_upper else "ACH"
        parts = re.split(r'[-/:]', raw)
        for part in parts:
            if part.isdigit() and len(part) >= 4:
                ref = part
            elif part.strip().upper() not in ("NACH", "ACH", "DR", "CR", "ECS"):
                if merchant is None and part.strip():
                    merchant = part.strip()

    if merchant:
        merchant = merchant.strip()
        if not merchant:
            merchant = None

    return NarrationInfo(
        payment_method=method,
        merchant_hint=merchant,
        reference_number=ref,
        is_likely_transfer=is_transfer
    )
