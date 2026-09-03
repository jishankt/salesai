"""
Cart and Checkout Node.
Manages running cart items and generates real draft orders / payment links.
"""
from typing import Dict, Any
from tools.handlers import add_to_cart, view_cart, checkout_cart
from orchestration.state import ConversationAIState

def cart_checkout_node(action: str, product_id: str, quantity: int, session_id: str) -> str:
    """Executes cart/checkout actions."""
    from models.cart import Cart
    from models.lead import Lead
    lead = Lead.get_by_session(session_id) or {}
    cust_name = lead.get("name") or "Valued Client"
    cust_contact = lead.get("contact") or "+971-50-0000000"

    cart = Cart.get(session_id)
    if not (cart and cart.get("items")) and product_id:
        Cart.add_item(session_id, product_id, quantity or 1)

    if action == "checkout":
        return checkout_cart(session_id, customer_name=cust_name, customer_contact=cust_contact)
    elif action == "cart_action":
        if product_id:
            return add_to_cart(session_id, product_id, quantity or 1)
        return view_cart(session_id)
    return "Your cart is currently active. Would you like to proceed to checkout?"
