"""
Response Composer: Synthesizes clean, grounded natural language responses.
Uses the verified deterministic node results and adheres strictly to persona formatting.
"""
from typing import Dict, Any, Optional
from orchestration.state import ConversationAIState

class ResponseComposer:
    """
    Composes natural responses from action results.
    """

    @classmethod
    def compose(cls, state: ConversationAIState, action: str, node_result: str, user_text: str) -> str:
        """
        Synthesizes the response for the user.
        """
        if not node_result:
            return "I am checking that for you right now. Could you please specify your model or printing requirement?"

        # If the node already produced a well-formatted structured card (catalog, consumables, quote, qualification),
        # return it directly with minimal framing to avoid LLM distortion.
        if any(marker in node_result for marker in ("📦 *", "💧 **Genuine", "🎯 **Kepler", "💵 *Price:*", "🧾 **PROFORMA", "🚚 **Kepler")):
            return node_result

        # Standard clean fallback
        return node_result
