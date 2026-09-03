"""
Conversation Orchestrator.
Coordinates:
1. Normalization
2. Intercepts (identity, chit-chat, apologies)
3. State Loading & Entity Extraction
4. Intent Routing
5. Decision Engine
6. Deterministic Node Execution
7. Response Composition
8. Safety & Grounding Validation
9. State Persistence
"""
import logging
from typing import Dict, Any, Optional

from input.normalizer import normalize_user_input
from input.conversational_intercepts import get_conversational_intercept
from input.entity_extractor import extract_entities, resolve_subject
from orchestration.state import ConversationAIState
from orchestration.state_repository import StateRepository
from orchestration.router import IntentRouter
from orchestration.decision_engine import DecisionEngine
from sales.buying_intent import evaluate_buying_intent, evaluate_sales_stage
from services.response_validator import validate_ai_response
from services.response_composer import ResponseComposer
from nodes import (
    run_product_search,
    run_consumables_lookup,
    run_pricing_quote,
    run_qualification_node,
    run_order_tracking,
    run_cart_checkout
)

logger = logging.getLogger("salesai.orchestrator")


class ConversationOrchestrator:
    """
    State-graph conversational orchestrator for SalesAI.
    """

    @classmethod
    def process_message(cls, session_id: str, user_message: str, client_type: str = "web") -> Dict[str, Any]:
        raw_text = (user_message or "").strip()
        if not raw_text:
            return {"role": "assistant", "content": "How can I assist you with printing solutions today?"}

        # 1. Input Normalization
        normalized = normalize_user_input(raw_text)

        # 2. Conversational Intercepts (Greetings, Identity, Apologies)
        is_intercepted, intercept_reply = get_conversational_intercept(normalized)
        if is_intercepted and intercept_reply:
            state = StateRepository.load(session_id)
            state.turn_count += 1
            StateRepository.save(state)
            
            # If greeting and customer name is known from Lead record, personalize warmly
            from models.lead import Lead
            lead = Lead.get_by_session(session_id)
            if lead and lead.get("name") and any(w in normalized.lower() for w in ("hello", "hi", "hey", "morning", "afternoon", "evening")):
                intercept_reply = f"Hello {lead['name']}! Welcome back to Kepler Tech. How can I assist you today with large format printers, genuine inks, or fine art media?"

            return {"role": "assistant", "content": intercept_reply}

        # 3. Load Conversation State
        state = StateRepository.load(session_id)
        state.turn_count += 1

        # 4. Entity Extraction & Subject Resolution
        entities = extract_entities(normalized, state)
        resolved_text = resolve_subject(normalized, state)

        # Apply extracted entities to state
        if entities.get("mentioned_models"):
            state.mentioned_models = entities["mentioned_models"]
            state.selected_product_id = entities["mentioned_models"][0]
        if entities.get("quantity"):
            state.quantity = entities["quantity"]
        if entities.get("print_size"):
            state.print_size = entities["print_size"]
        if entities.get("scan_required") is not None:
            state.scan_required = entities["scan_required"]
        if entities.get("category"):
            state.category = entities["category"]
        if entities.get("budget"):
            state.budget = entities["budget"]

        # Update Sales Stage and Buying Intent
        state.buying_intent = evaluate_buying_intent(normalized, state.buying_intent)
        state.sales_stage = evaluate_sales_stage(state, normalized)

        # Extract customer contact / territory / name to keep CRM synchronized
        from services.lead_extraction import save_lead_signals_if_any
        save_lead_signals_if_any(session_id, normalized)

        # 5. Intent Routing
        route = IntentRouter.route(resolved_text, state, entities)
        state.intent = route.intent

        # 6. Decision Engine: Choose deterministic next action
        action, action_params = DecisionEngine.decide_next_action(state, route)
        state.next_action = action
        action_params = action_params or {}

        # 7. Execute Deterministic Node
        node_result = ""
        if action == "lookup_consumables":
            model = action_params.get("printer_model") or state.selected_product_id
            node_result = run_consumables_lookup(model, state)

        elif action in ("search_products", "recommend_products"):
            query = action_params.get("query") or state.category or resolved_text
            node_result = run_product_search(query, state)

        elif action in ("calculate_price", "prepare_quote"):
            pid = action_params.get("product_id") or state.selected_product_id
            qty = action_params.get("quantity") or state.quantity or 1
            node_result = run_pricing_quote(pid, qty, state)

        elif action == "ask_qualification":
            q_rule = action_params.get("question_rule", {})
            node_result = run_qualification_node(q_rule, state)

        elif action == "track_order":
            node_result = run_order_tracking(resolved_text)

        elif action in ("checkout", "cart_action"):
            pid = action_params.get("product_id") or state.selected_product_id
            qty = action_params.get("quantity") or state.quantity or 1
            node_result = run_cart_checkout(action, pid, qty, session_id)

        elif action == "human_handoff":
            node_result = "I am connecting you right now with our senior technical sales team at Kepler Tech. One of our specialists will assist you directly! 🤝"

        elif action == "support_rag":
            from nodes.support import support_node
            node_result = support_node(resolved_text)

        else:
            # Fallback catalog / consultation
            node_result = run_product_search(resolved_text, state)

        # 8. Response Composition
        composed_reply = ResponseComposer.compose(state, action, node_result, resolved_text)

        # 9. Safety & Grounding Validation
        is_valid, val_reason, sanitized_reply = validate_ai_response(
            content=composed_reply,
            last_tool_result=node_result,
            action=action
        )

        final_content = sanitized_reply if is_valid else node_result

        # 10. Persist Updated Canonical State
        StateRepository.save(state)

        return {
            "role": "assistant",
            "content": final_content,
            "orchestration": {
                "intent": state.intent,
                "sales_stage": state.sales_stage,
                "action": action,
                "selected_product": state.selected_product_id
            }
        }
