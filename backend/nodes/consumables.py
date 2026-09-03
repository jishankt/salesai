"""
Consumables Node.
Resolves and returns exact compatible genuine inks, maintenance boxes, and media.
"""
from typing import Dict, Any
from tools.handlers import get_printer_consumables
from orchestration.state import ConversationAIState

def consumables_node(printer_model: str, state: ConversationAIState) -> str:
    """Executes deterministic consumable lookup."""
    m = printer_model or state.selected_product_id or ""
    if not m:
        return "Which printer model do you need inks or consumables for? (e.g. SC-T3700DE, P9500, CX-02)"
    return get_printer_consumables(m, consumable_filter="inks")
