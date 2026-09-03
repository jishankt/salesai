"""
Support and FAQ Node.
Provides official policy on warranty, shipping, and technical services.
"""
from typing import Dict, Any
from tools.handlers import get_shipping_info, get_warranty_and_support, track_order

def support_node(query: str, intent_type: str = "warranty") -> str:
    """Executes deterministic support lookup."""
    q_low = (query or "").lower()
    if "shipping" in q_low or "delivery" in q_low or "deliver" in q_low:
        if any(place in q_low for place in ("london", "uk", "usa", "europe", "america", "canada", "australia", "germany", "france")):
            return (
                "📍 **International Delivery Notice:**\n\n"
                "Kepler Tech LLC operates primarily across the **United Arab Emirates (Dubai, Abu Dhabi, Sharjah, etc.)** and **GCC countries (Saudi Arabia, Oman, Qatar, Bahrain, Kuwait)** with door-to-door delivery.\n\n"
                "For deliveries outside the GCC (such as the UK or Europe), we can arrange export shipments or airport-to-airport freight upon request! Would you like me to connect you with our export logistics team?"
            )
        return get_shipping_info("Dubai")
    elif "order" in q_low or "track" in q_low:
        return track_order(query)
    return get_warranty_and_support(query)
