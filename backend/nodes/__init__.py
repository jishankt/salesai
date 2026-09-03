"""
Nodes Package: Specialized deterministic execution nodes for the conversational state graph.
Each node executes a single business operation without delegating tool decisions to the LLM.
"""
from .product_search import product_search_node
from .consumables import consumables_node
from .qualification import qualification_node
from .pricing import pricing_node
from .cart_checkout import cart_checkout_node
from .support import support_node

# Expose backward-compatible function signatures
run_product_search = product_search_node
run_consumables_lookup = consumables_node
run_qualification_node = qualification_node
run_pricing_quote = pricing_node
run_cart_checkout = cart_checkout_node
run_order_tracking = lambda q: support_node(q, intent_type="order")

__all__ = [
    "product_search_node",
    "consumables_node",
    "qualification_node",
    "pricing_node",
    "cart_checkout_node",
    "support_node",
    "run_product_search",
    "run_consumables_lookup",
    "run_qualification_node",
    "run_pricing_quote",
    "run_cart_checkout",
    "run_order_tracking",
]
