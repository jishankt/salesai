from __future__ import annotations
"""
Input entity extraction and subject resolution.
Extracts models, quantities, dimensions, budgets, and resolves anaphora ("that printer").
"""
import re
from typing import Dict, Any, List, Optional
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from orchestration.state import ConversationAIState

# Known models & SKU regex patterns
MODEL_PATTERNS = [
    r'\b(?:sc-?)?(?:t[0-9]{4}[a-z0-9]*|p[0-9]{4,5}[a-z0-9]*|f[0-9]{3,4}[a-z0-9]*|v[0-9]{3,4}[a-z0-9]*|l[0-9]{4}[a-z0-9]*)\b',
    r'\b(?:wf-?[a-z0-9]{4,6}|am-?c[0-9]{3,5}|em-?c[0-9]{3,5})\b',
    r'\b(?:cx-?02|cy-?02|cz-?01|op-?900ii)\b',
    r'\b(?:c13[a-z0-9]{7,8}|c11[a-z0-9]{8,10})\b',
]

def extract_entities(text: str, state: Optional[ConversationAIState] = None) -> Dict[str, Any]:
    """
    Extracts structured entities from user message.
    Returns: dict of extracted attributes
    """
    entities = {}
    if not text:
        return entities

    t_low = text.lower()

    # 1. Models & SKUs
    found_models = []
    for pattern in MODEL_PATTERNS:
        matches = re.findall(pattern, t_low)
        for m in matches:
            clean_m = m.upper().strip()
            if clean_m not in found_models:
                found_models.append(clean_m)
    if found_models:
        entities["mentioned_models"] = found_models
        entities["selected_product_id"] = found_models[0]

    # 2. Quantity (e.g. "10 units", "5 pcs", "quantity: 3", "need 20 printers")
    qty_match = re.search(r'\b(\d+)\s*(?:units?|pcs?|pieces?|printers?|boxes?|cartridges?|rolls?|items?)\b', t_low)
    if not qty_match:
        qty_match = re.search(r'\b(?:quantity|qty)\s*[:=]?\s*(\d+)\b', t_low)
    if not qty_match:
        # e.g. "quote for 10 cx02"
        qty_match = re.search(r'\b(?:for|order|buy|need)\s+(\d{1,4})\s+(?:cx|sc|epson|citizen|[a-z0-9]{4,})\b', t_low)
    if qty_match:
        try:
            entities["quantity"] = int(qty_match.group(1))
        except (ValueError, IndexError):
            pass

    # 3. Print Sizes (e.g. A0, A1, A2, A3, A4, 24-inch, 36-inch, 44-inch, 64-inch, 4x6)
    size_match = re.search(r'\b(a[0-4]|24\s*inch|36\s*inch|44\s*inch|64\s*inch|4\s*x\s*6|6\s*x\s*8|8\s*x\s*10|8\s*x\s*12)\b', t_low)
    if size_match:
        entities["print_size"] = size_match.group(1).upper().replace(" ", "")

    # 4. Scanner requirement
    if re.search(r'\b(?:with scanner|scanner needed|need scanning|multifunction|mfp|scan required)\b', t_low):
        entities["scan_required"] = True
    elif re.search(r'\b(?:no scanner|print only|printer only|without scanner)\b', t_low):
        entities["scan_required"] = False
    elif state and getattr(state, "last_question_field", None) == "scan_required":
        if re.search(r'\b(?:yes|yeah|yep|sure|yup|affirmative|i do|we do|needed|required)\b', t_low):
            entities["scan_required"] = True
        elif re.search(r'\b(?:no|nope|nah|not needed|not required|don\'t need|dont need)\b', t_low):
            entities["scan_required"] = False

    # 5. Category detection
    if re.search(r'\b(?:cad|gis|architect|engineering|blueprints?|line drawings?|technical drawings?)\b', t_low):
        entities["category"] = "technical_cad"
    elif re.search(r'\b(?:photo booth|event photog|instant prints?|party prints?|wedding booth)\b', t_low):
        entities["category"] = "photo_booth"
    elif re.search(r'\b(?:fine art|canvas|gallery|giclee|photo studio|commercial photo)\b', t_low):
        entities["category"] = "photo_fineart"
    elif re.search(r'\b(?:sublimation|textile|apparel|mugs|t-shirts?)\b', t_low):
        entities["category"] = "sublimation"
    elif re.search(r'\b(?:signage|banners?|vehicle wrap|uv flatbed|stickers?|vinyl)\b', t_low):
        entities["category"] = "signage_uv"
    elif re.search(r'\b(?:office|workforce|business documents?|school|copier)\b', t_low):
        entities["category"] = "office_business"

    # 6. Budget
    budget_match = re.search(r'\b(?:budget|max|around|under)\s*(?:is|of|:)?\s*(\d{3,6})\s*(?:aed|dhs|dirhams)?\b', t_low)
    if budget_match:
        try:
            entities["budget"] = float(budget_match.group(1))
        except (ValueError, IndexError):
            pass

    # 7. Volume (Daily / Monthly) & Qualification values
    vol_match = re.search(r'\b(?:around|about|approx|approx\.)?\s*(\d+)\s*(?:drawings?|plans?|prints?|pages?|copies|docs?|sheets?)\b', t_low)
    if not vol_match and state and getattr(state, "last_question_field", None) in ("daily_volume", "monthly_volume"):
        vol_match = re.search(r'\b(\d+)\b', t_low)
    if vol_match:
        try:
            vol_val = int(vol_match.group(1))
            if state and getattr(state, "last_question_field", None) == "monthly_volume":
                entities["monthly_volume"] = vol_val
            else:
                entities["daily_volume"] = vol_val
        except (ValueError, IndexError):
            pass

    # 8. Use Case (e.g. canvas, fine art, apparel, mugs)
    if re.search(r'\b(?:canvas|fine art cotton|cotton rag|photo glossy|luster)\b', t_low):
        entities["use_case"] = t_clean = text.strip()
    elif re.search(r'\b(?:mugs?|gifts?|apparel|sportswear|textile|signage)\b', t_low):
        entities["use_case"] = text.strip()

    return entities

def resolve_subject(text: str, state: Optional[ConversationAIState]) -> str:
    """
    Resolves conversational pronouns/anaphora like 'that printer', 'this model', 'it'.
    Prefers canonical state before looking back.
    """
    if not text:
        return ""
    t_clean = text.strip()
    
    # Check if text contains anaphora
    if re.search(r'\b(?:that printer|this printer|that model|this model|the printer|it|them|for it|for that)\b', t_clean, re.I):
        if state and state.selected_product_id:
            # Replace anaphora with concrete selected model
            return re.sub(r'\b(that printer|this printer|that model|this model|the printer)\b', state.selected_product_id, t_clean, flags=re.IGNORECASE)
    return t_clean
