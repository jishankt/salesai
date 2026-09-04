"""
Response Composer: Synthesizes clean, grounded natural language responses.
Uses the verified deterministic node results and generates natural, contextual replies via LLM.
"""
import re
import logging
from typing import Dict, Any, Optional
from orchestration.state import ConversationAIState
from services.ollama_client import chat_completion
from prompts.persona import get_system_prompt

logger = logging.getLogger("salesai.composer")

class ResponseComposer:
    """
    Composes natural conversational responses using the LLM grounded with verified action results.
    """

    @classmethod
    def compose(cls, state: ConversationAIState, action: str, node_result: str, user_text: str) -> str:
        """
        Synthesizes the response for the user with the active LLM.
        """
        if not node_result:
            return "I am checking that for you right now. Could you please specify your printer model or printing requirements?"

        # If it's a simple 1-question qualification card, return card directly
        if action == "ask_qualification" and "🎯 **Kepler" in node_result:
            return node_result

        # For search, recommendation, consumables, quotes, support, and consultation:
        # Ask LLM (gpt-oss:20b) to generate warm conversational intro and context while embedding verified facts
        prompt = (
            f"You are Kepler Tech's AI Sales Specialist in Dubai.\n"
            f"Customer Message: \"{user_text}\"\n"
            f"Active Action: {action}\n"
            f"Verified Ground-Truth Result:\n{node_result}\n\n"
            f"Task: Respond naturally, helpfully, and conversationally to the customer using the verified facts above. "
            f"Keep all product names, prices (AED), stock status, and product card blocks (━━━━━━━━━━━━━━━━━━━━) exactly intact. "
            f"Do not invent fake prices or unavailable products."
        )

        try:
            sys_prompt = get_system_prompt()
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt}
            ]
            res = chat_completion(messages, temperature=0.3)
            llm_text = res.get("message", {}).get("content", "").strip()

            # Clean any stray thinking model residue
            if "</think>" in llm_text:
                llm_text = llm_text.split("</think>")[-1].strip()
            # If the model emitted internal thoughts ending before greeting
            llm_text = re.sub(r'^(?:[A-Z][^\n]*\n+)+?(?=(?:Hello|Hi|Here|Welcome|Certainly|Sure|We stock|Great|Yes|I can|The\s+\*\*))', '', llm_text, flags=re.IGNORECASE).strip() or llm_text

            if llm_text:
                # If node_result has formatted content or pricing that LLM truncated, cleanly attach node_result
                if ("━━━━━━━━━━━━━━━━━━━━" in node_result and "━━━━━━━━━━━━━━━━━━━━" not in llm_text) or ("AED" in node_result and "AED" not in llm_text):
                    return f"{llm_text}\n\n{node_result}"
                return llm_text
        except Exception as e:
            logger.warning(f"ResponseComposer LLM generation fallback: {e}")

        # Fallback to pure node result
        return node_result

