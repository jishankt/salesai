"""
Product Search Node.
Handles mandatory catalog execution without delegating the search decision to the LLM.
"""
from typing import Dict, Any
from tools.handlers import search_products
from orchestration.state import ConversationAIState

def product_search_node(query: str, state: ConversationAIState) -> str:
    """Executes deterministic catalog lookup."""
    q = query or state.selected_product_id or state.category or "Epson"
    return search_products(q)
