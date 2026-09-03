"""
Qualification Node.
Executes the single-question qualification card step.
"""
from typing import Dict, Any
from orchestration.state import ConversationAIState

def qualification_node(question_rule: dict, state: ConversationAIState) -> str:
    """Renders the single qualification question card."""
    q_text = question_rule.get("question", "")
    options = question_rule.get("options", [])
    opt_str = " | ".join(options) if options else ""
    card = f"🎯 **Kepler Product Consultation:**\n\n{q_text}"
    if opt_str:
        card += f"\n\n[Options: {opt_str}]"
    return card
