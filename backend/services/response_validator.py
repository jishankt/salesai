"""
Multi-Stage AI Response Validator & Safety Engine.
Performs anti-hallucination checks, JSON structure leakage prevention, internal database field protection,
competitor name filtering, and commercial pricing bounds verification before message dispatch.
"""
import re
from typing import Tuple, Optional, List, Dict, Any

# Competitor or non-partner brands that should not be promoted
PROHIBITED_COMPETITORS = [
    r"\bshutterfly\b", r"\betsy\b", r"\bvbp\b", r"\bvistaprint\b",
    r"\bcanon\b", r"\bhp\s+indigo\b", r"\broland\b", r"\bmimaki\b"
]

# Internal database/system identifiers that should never be shown in chat
INTERNAL_SYSTEM_LEAKS = [
    r"\brow_id\b", r"\bmem_db\b",
    r"\bcollections?\b", r"\bsession_id\b", r"\btool_calls?\b",
    r"\bo_auth\b", r"\bapi_key\b", r"\bsystem_prompt\b"
]

def check_json_leakage(text: str) -> bool:
    """Detects raw unparsed JSON blocks or tool signature leakage."""
    if not text:
        return False
    stripped = text.strip()
    # Check for raw JSON object/array patterns
    if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
        if '"name":' in text or '"arguments":' in text or '"function":' in text:
            return True
    if '{"name":' in text or '{"product_id":' in text or '{"query":' in text:
        return True
    return False

def check_internal_leaks(text: str) -> Tuple[bool, Optional[str]]:
    """Checks if internal prompt variables or database column names leaked."""
    if not text:
        return False, None
    text_l = text.lower()
    for leak_pat in INTERNAL_SYSTEM_LEAKS:
        if re.search(leak_pat, text_l):
            return True, leak_pat
    return False, None

def check_competitor_mentions(text: str) -> Tuple[bool, Optional[str]]:
    """Checks for non-partner competitor mentions."""
    if not text:
        return False, None
    text_l = text.lower()
    for comp in PROHIBITED_COMPETITORS:
        if re.search(comp, text_l):
            return True, comp
    return False, None

def check_price_bounds(text: str) -> Tuple[bool, Optional[str]]:
    """Ensures quoted prices don't fall below minimum floor or claim unrealistic free hardware."""
    if not text:
        return False, None
    text_l = text.lower()
    # Catch phrases claiming free printers or hardware
    if re.search(r'\b(?:free\s+printer|free\s+sc-p|free\s+cx-02|0\s*aed\s+for\s+printer)\b', text_l):
        return True, "unrealistic_free_hardware"
    return False, None

def sanitize_and_clean_text(text: str) -> str:
    """Removes stray formatting artifacts and unneeded raw tags."""
    if not text:
        return ""
    cleaned = text
    # Remove raw backtick escaped database columns
    cleaned = re.sub(r'`(?:row_id|created_at|mem_db)`', '', cleaned)
    # Strip double spaces
    cleaned = re.sub(r' +', ' ', cleaned).strip()
    return cleaned

def check_chemical_compatibility(text: str) -> Tuple[bool, Optional[str]]:
    """Prevents dangerous ink chemistry mix-ups (e.g. UltraChrome PRO on SC-F Dye Sublimation printers)."""
    if not text:
        return False, None
    text_l = text.lower()
    # Check if claiming UltraChrome is compatible with SC-F series / sublimation
    if ("ultrachrome" in text_l or "pigment" in text_l) and ("sc-f" in text_l or "sc f100" in text_l or "sc f500" in text_l or "f100" in text_l or "f500" in text_l) and ("compatible" in text_l or "fit" in text_l or "works with" in text_l or "use" in text_l):
        return True, "ultrachrome_on_sublimation_mismatch"
    return False, None

def validate_ai_response(content: str) -> Tuple[bool, str, str]:
    """
    Main validator entrypoint.
    Returns:
      (is_valid: bool, reason: str, sanitized_content: str)
    """
    if not content or not content.strip():
        return True, "empty_content", content

    # 1. JSON structure leakage check
    if check_json_leakage(content):
        return False, "json_leakage_detected", ""

    # 2. Internal system leak check
    has_leak, leak_term = check_internal_leaks(content)
    if has_leak:
        return False, f"internal_leak_detected:{leak_term}", ""

    # 3. Competitor mention check
    has_comp, comp_name = check_competitor_mentions(content)
    if has_comp:
        return False, f"competitor_mention_detected:{comp_name}", ""

    # 4. Pricing sanity check
    has_price_err, price_reason = check_price_bounds(content)
    if has_price_err:
        return False, f"pricing_bounds_violation:{price_reason}", ""

    # 5. Chemical compatibility check
    has_chem_err, chem_reason = check_chemical_compatibility(content)
    if has_chem_err:
        return False, f"chemical_compatibility_violation:{chem_reason}", ""

    sanitized = sanitize_and_clean_text(content)
    return True, "valid", sanitized

class ResponseValidator:
    """Unified class wrapper for response validation functions."""
    check_json_leakage = staticmethod(check_json_leakage)
    check_internal_leaks = staticmethod(check_internal_leaks)
    check_competitor_mentions = staticmethod(check_competitor_mentions)
    check_price_bounds = staticmethod(check_price_bounds)
    check_chemical_compatibility = staticmethod(check_chemical_compatibility)
    validate_ai_response = staticmethod(validate_ai_response)
    sanitize_and_clean_text = staticmethod(sanitize_and_clean_text)

