"""
Buying intent and sales stage evaluation.
Detects urgency, purchasing readiness, and manages commercial state transitions.
"""
import re
from typing import Tuple
from orchestration.state import ConversationAIState, SalesStage, BuyingIntent

def evaluate_buying_intent(text: str, current_intent: BuyingIntent) -> BuyingIntent:
    """Detects buying signals and upgrades buying intent level."""
    t_low = text.lower()

    # High buying signals: explicit quote, purchase, checkout, payment, LPO, tender
    if re.search(r'\b(?:quotation|formal quote|proforma|invoice|buy now|ready to buy|purchase order|lpo|payment link|wire transfer|checkout|order now|deliver today|dispatch immediately)\b', t_low):
        return "high"

    # Medium buying signals: price inquiry, discount request, stock availability, warranty
    if re.search(r'\b(?:price|pricing|cost|how much|discount|stock|available|in stock|warranty|lead time|shipping cost)\b', t_low):
        if current_intent in ("none", "low"):
            return "medium"
        return current_intent

    # Low buying signals: looking, exploring, browsing
    if re.search(r'\b(?:looking|exploring|browsing|checking options|comparing)\b', t_low):
        if current_intent == "none":
            return "low"

    return current_intent

def evaluate_sales_stage(state: ConversationAIState, user_text: str) -> SalesStage:
    """Updates sales stage smoothly based on user text and collected state."""
    t_low = user_text.lower()

    # Closing stage
    if re.search(r'\b(?:checkout|pay|payment link|order now|finalize order)\b', t_low) or state.intent == "checkout":
        return "closing"

    # Quotation stage
    if re.search(r'\b(?:quotation|quote|proforma|invoice|official price)\b', t_low) or state.intent == "quotation":
        return "quotation"

    # Pricing stage
    if re.search(r'\b(?:how much|price|cost|rate|discount)\b', t_low) or state.intent == "pricing":
        return "pricing"

    # Evaluation stage (comparing products or verifying specs)
    if state.intent in ("product_comparison", "product_details") or re.search(r'\b(?:compare|versus|difference between|specs|datasheet)\b', t_low):
        return "evaluation"

    # Recommendation stage (candidate models found or category requirements specified)
    if state.selected_product_id or state.print_size:
        return "recommendation"

    # Qualification stage (broad category known, determining requirements)
    if state.category:
        return "qualification"

    return state.sales_stage or "discovery"
