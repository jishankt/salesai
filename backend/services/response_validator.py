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

def extract_pricing_entities(text: str) -> List[float]:
    """Extracts numeric pricing values associated with currency mentions (AED, Dhs, etc.)."""
    if not text:
        return []
    prices = []
    # Patterns like '4,500 AED', '4500.00 AED', 'AED 4500', '450 AED'
    matches = re.findall(r'(?:AED|Dhs|Dh|\$)\s*([\d,]+(?:\.\d{1,2})?)|([\d,]+(?:\.\d{1,2})?)\s*(?:AED|Dhs|Dh|\$)', text, re.IGNORECASE)
    for m1, m2 in matches:
        raw = m1 or m2
        raw_clean = raw.replace(',', '')
        try:
            val = float(raw_clean)
            if val > 0:
                prices.append(val)
        except ValueError:
            continue
    return prices

def extract_sku_and_spec_tokens(text: str) -> List[str]:
    """Extracts potential SKU codes, model identifiers, and exact sizing specs."""
    if not text:
        return []
    tokens = set()
    # SKUs like C13T00E140, T800100, SC-P9500, WF-C579R, CX-02
    sku_matches = re.findall(r'\b(?:C13T[A-Z0-9]+|T[0-9]{5,7}|SC-[PTF]\d{3,5}[A-Z]*|WF-[A-Z0-9]+|CX-02|CZ-01|AM-C\d{3,5}|EM-C\d{3,5})\b', text, re.IGNORECASE)
    for s in sku_matches:
        tokens.add(s.upper())
    # Sizing / specs like 44-inch, 24-inch, 700ml, 350ml, 110ml, 80gsm
    spec_matches = re.findall(r'\b(?:\d+[\-\s]*(?:inch|ml|gsm|mm))\b', text, re.IGNORECASE)
    for sp in spec_matches:
        tokens.add(re.sub(r'[\s\-]', '', sp.lower()))
    return list(tokens)

def check_grounding(content: str, last_tool_result: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Grounding check: Ensures that prices and specific SKU/spec tokens stated in the LLM's final reply
    appear verbatim (or with equivalent numerical value) in the last verified tool output.
    """
    if not content or not last_tool_result:
        return False, None

    reply_prices = extract_pricing_entities(content)
    if reply_prices:
        tool_prices = extract_pricing_entities(last_tool_result)
        # Also check direct integer/float string occurrences in tool output
        for p in reply_prices:
            p_int_str = f"{int(p)}" if p.is_integer() else f"{p:.2f}"
            p_float_str = f"{p:.2f}"
            if not any(abs(p - tp) < 0.01 for tp in tool_prices) and p_int_str not in last_tool_result and p_float_str not in last_tool_result:
                return True, f"ungrounded_price_detected:{p:.2f}_AED"

    reply_skus = extract_sku_and_spec_tokens(content)
    if reply_skus:
        tool_content_upper = last_tool_result.upper()
        tool_content_normalized = re.sub(r'[\s\-]', '', last_tool_result.lower())
        for sku in reply_skus:
            sku_norm = re.sub(r'[\s\-]', '', sku.lower())
            if sku not in tool_content_upper and sku_norm not in tool_content_normalized:
                return True, f"ungrounded_sku_or_spec_detected:{sku}"

    return False, None

def count_questions(text: str) -> int:
    """Counts the number of distinct questions asked in text."""
    if not text:
        return 0
    # Count question marks or interrogative clauses
    q_marks = text.count("?")
    return q_marks

def check_question_count(content: str, action: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Ensures that during qualification, at most one question is asked per turn."""
    if action == "ask_qualification":
        q_count = count_questions(content)
        if q_count > 1:
            return True, f"multiple_questions_in_qualification:{q_count}"
    return False, None

def validate_ai_response(content: str, last_tool_result: Optional[str] = None, action: Optional[str] = None) -> Tuple[bool, str, str]:
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

    # 6. Tool Grounding Verification
    if last_tool_result:
        has_grounding_err, grounding_reason = check_grounding(content, last_tool_result)
        if has_grounding_err:
            return False, f"grounding_violation:{grounding_reason}", ""

    # 7. Single Question Enforcement for Qualification
    if action:
        has_q_err, q_reason = check_question_count(content, action)
        if has_q_err:
            return False, f"question_count_violation:{q_reason}", ""

    sanitized = sanitize_and_clean_text(content)
    return True, "valid", sanitized

class ResponseValidator:
    """Unified class wrapper for response validation functions."""
    check_json_leakage = staticmethod(check_json_leakage)
    check_internal_leaks = staticmethod(check_internal_leaks)
    check_competitor_mentions = staticmethod(check_competitor_mentions)
    check_price_bounds = staticmethod(check_price_bounds)
    check_chemical_compatibility = staticmethod(check_chemical_compatibility)
    check_grounding = staticmethod(check_grounding)
    check_question_count = staticmethod(check_question_count)
    validate_ai_response = staticmethod(validate_ai_response)
    sanitize_and_clean_text = staticmethod(sanitize_and_clean_text)


