"""
Pricing and Quotation Node.
Calculates discounts, unit pricing, and prepares official drafts.
"""
from typing import Dict, Any
from tools.handlers import get_price
from orchestration.state import ConversationAIState

def pricing_node(product_id: str, quantity: int, state: ConversationAIState) -> str:
    """Executes deterministic pricing calculation or quote draft."""
    pid = product_id or state.selected_product_id or ""
    qty = quantity or state.quantity or 1
    if not pid:
        return "Which product would you like pricing or an official quote for?"
    return get_price(pid, qty)
