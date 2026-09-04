"""
Pricing and Quotation Node.
Calculates discounts, unit pricing, and prepares official drafts.
"""
from typing import Dict, Any
from tools.handlers import get_price, search_products
from orchestration.state import ConversationAIState

def pricing_node(product_id: str, quantity: int, state: ConversationAIState, raw_query: str = "") -> str:
    """Executes deterministic pricing calculation or quote draft."""
    pid = product_id or state.selected_product_id or ""
    qty = quantity or state.quantity or 1
    
    # If no exact product_id is known, try searching catalog with raw query (e.g. "Korejet canvas")
    if not pid and raw_query:
        from models.product import Product
        found = Product.search_products(raw_query)
        if found:
            pid = found[0]["_id"]
            state.selected_product_id = pid

    if not pid:
        if qty >= 5:
            return f"At Kepler Tech, we offer a **10% bulk discount** on orders of 5 or more units. Which specific printer model, ink pack, or media roll would you like me to prepare an official quote for?"
        return "Which product would you like pricing or an official quote for?"
        
    return get_price(pid, qty)

