"""
Conversation Decision Engine.
Decides the single deterministic next action based on canonical state and route decision,
removing prompt-based branching and unpredictable multi-tool calls.
"""
from typing import Tuple, Dict, Any, Optional
from orchestration.state import ConversationAIState
from orchestration.router import RouteDecision
from sales.qualification_rules import get_next_qualification_question

class DecisionEngine:
    """
    Evaluates state and determines the next mandatory action node to execute.
    """

    @classmethod
    def decide_next_action(cls, state: ConversationAIState, route: RouteDecision) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Returns: (action_name: str, action_params: Optional[dict])
        """
        # 1. Human handoff
        if state.needs_human or route.intent == "human_handoff":
            return "human_handoff", {"reason": "User requested human agent or repeated difficulty"}

        # 2. Order Tracking
        if route.intent == "order_tracking":
            return "track_order", {}

        # 3. Checkout / Payment
        if route.intent == "checkout":
            return "checkout", {"product_id": state.selected_product_id, "quantity": state.quantity or 1}

        # 4. Cart actions
        if route.intent == "cart":
            return "cart_action", {"product_id": state.selected_product_id, "quantity": state.quantity or 1}

        # 5. Quotation / Proforma
        if route.intent == "quotation":
            return "prepare_quote", {
                "product_id": state.selected_product_id,
                "quantity": state.quantity or 1,
                "models": route.mentioned_models
            }

        # 6. Inks & Consumables
        if route.intent == "consumables":
            model = route.mentioned_models[0] if route.mentioned_models else state.selected_product_id
            return "lookup_consumables", {"printer_model": model}

        # 7. Comparison
        if route.intent == "product_comparison":
            return "compare_products", {"models": route.mentioned_models}

        # 8. Pricing & Discount Inquiry
        if route.intent == "pricing":
            model = route.mentioned_models[0] if route.mentioned_models else state.selected_product_id
            return "calculate_price", {"product_id": model, "quantity": state.quantity or 1}

        # 9. Exact Product Search
        if route.intent == "product_search":
            model = route.mentioned_models[0] if route.mentioned_models else None
            return "search_products", {"query": model, "exact": True}

        # 10. Broad Product Discovery / Qualification
        if route.intent == "product_discovery":
            # Check if there is a missing qualification question
            next_q = get_next_qualification_question(state)
            if next_q:
                state.last_question_field = next_q["field"]
                if next_q["field"] not in state.asked_fields:
                    state.asked_fields.append(next_q["field"])
                return "ask_qualification", {"question_rule": next_q}

            # If all qualification answers collected or category has candidates: recommend products
            return "recommend_products", {
                "category": state.category,
                "print_size": state.print_size,
                "scan_required": state.scan_required
            }

        # 11. Support / FAQ / RAG
        if route.intent == "support":
            return "support_rag", {}

        # 12. General fallback
        return "general_chat", {}
