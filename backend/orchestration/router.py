"""
Structured Intent Router.
Classifies incoming normalized user queries into a typed RouteDecision
without relying on raw LLM judgment.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional
from orchestration.state import Intent, BuyingIntent, ConversationAIState

@dataclass
class RouteDecision:
    intent: Intent
    mentioned_models: List[str] = field(default_factory=list)
    category: Optional[str] = None
    buying_intent: BuyingIntent = "none"

    requires_catalog: bool = False
    requires_pricing: bool = False
    requires_consumables: bool = False
    requires_quote: bool = False
    requires_order_tracking: bool = False
    requires_cart: bool = False
    requires_rag: bool = False


class IntentRouter:
    """
    High-precision deterministic router that inspects normalized input + session state.
    """

    @classmethod
    def route(cls, text: str, state: ConversationAIState, extracted_entities: dict) -> RouteDecision:
        t_low = text.lower().strip()
        models = extracted_entities.get("mentioned_models", []) or state.mentioned_models
        category = extracted_entities.get("category") or state.category

        # 1. Human Handoff / Escalation
        if re.search(r'\b(?:talk to a human|human agent|human support|connect me to someone|call me|speak with human|real person|manager)\b', t_low):
            return RouteDecision(intent="human_handoff")

        # 2. Order Tracking
        if re.search(r'\b(?:track order|order status|where is my order|check order|order tracking)\b', t_low) or (
            re.search(r'\border\b', t_low) and re.search(r'\b(?:ord_[a-z0-9]+|[0-9]{5,})\b', t_low)
        ):
            return RouteDecision(intent="order_tracking", requires_order_tracking=True)

        # 3. Checkout / Payment
        if re.search(r'\b(?:checkout|pay now|payment link|send.*payment|pay link|proceed to (?:pay|buy)|buy now|ready to pay)\b', t_low):
            return RouteDecision(intent="checkout", buying_intent="high", requires_cart=True)

        # 4. Cart management
        if re.search(r'\b(?:add to cart|my cart|show cart|view cart|remove from cart|clear cart)\b', t_low):
            return RouteDecision(intent="cart", requires_cart=True)

        # 5. Quotation / Proforma Invoice
        if re.search(r'\b(?:quote|quotation|proforma|formal quotation|official quote|prepare a quote|send invoice)\b', t_low):
            return RouteDecision(
                intent="quotation",
                mentioned_models=models,
                category=category,
                buying_intent="high",
                requires_quote=True,
                requires_pricing=True
            )

        # 6. Inks & Consumables Lookup
        # (e.g. "SC T3700DE just check this models inks", "ink for that printer", "maintenance box for cx02")
        is_consumable_keyword = bool(re.search(r'\b(?:inks?|cartridges?|maintenance box|waste box|ribbons?|media roll|paper roll|toner|printhead)\b', t_low))
        if is_consumable_keyword:
            return RouteDecision(
                intent="consumables",
                mentioned_models=models,
                requires_consumables=True
            )

        # 7. Comparison
        if re.search(r'\b(?:compare|difference between|versus|vs\.?)\b', t_low) or len(models) >= 2:
            return RouteDecision(
                intent="product_comparison",
                mentioned_models=models,
                requires_catalog=True
            )

        # 8. Pricing & Discount Inquiry
        if re.search(r'\b(?:price|cost|how much|rate|discount|any discount|bulk discount|best offer)\b', t_low):
            return RouteDecision(
                intent="pricing",
                mentioned_models=models,
                category=category,
                requires_pricing=True,
                requires_catalog=True
            )

        # 9. Support / FAQ / Shipping / Delivery
        if re.search(r'\b(?:deliver|delivery|shipping|ship to|ship|deliver to|warranty|install|service|error|problem|manual|driver|troubleshoot|setup)\b', t_low):
            return RouteDecision(
                intent="support",
                requires_rag=True
            )

        # 10. Exact Product Search / Lookup
        if extracted_entities.get("mentioned_models"):
            # Model or SKU explicitly identified in this turn
            return RouteDecision(
                intent="product_search",
                mentioned_models=extracted_entities["mentioned_models"],
                requires_catalog=True
            )

        # 11. Broad Product Discovery / Qualification Continuity
        is_qualification_answer = bool(
            extracted_entities.get("print_size") or 
            extracted_entities.get("scan_required") is not None or 
            extracted_entities.get("daily_volume") or
            (state.category and state.last_question_field)
        )
        if category or is_qualification_answer or re.search(r'\b(?:recommend|looking for|need a printer|printer for|which printer|best printer|plotter|photo printer|cad printer)\b', t_low):
            return RouteDecision(
                intent="product_discovery",
                category=category or state.category,
                requires_catalog=True
            )

        # 12. General fallback
        return RouteDecision(
            intent="general",
            requires_catalog=False
        )
