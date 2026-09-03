"""
Mock LLM client test harness.
Provides deterministic canned responses and tool calls for chat_completion
without requiring live Ollama or Groq services in CI.
"""
from typing import List, Dict, Any, Optional

class MockLLMClient:
    def __init__(self):
        self.canned_responses: List[Dict[str, Any]] = []
        self.call_history: List[Dict[str, Any]] = []
        self.auto_match_rules: List[Dict[str, Any]] = []

    def queue_response(self, response: Dict[str, Any]):
        """Queue a sequential response."""
        self.canned_responses.append(response)

    def add_rule(self, trigger_substr: str, tool_name: Optional[str] = None, tool_args: Optional[Dict[str, Any]] = None, content: str = ""):
        """Add a rule-based response matched on message content."""
        self.auto_match_rules.append({
            "trigger": trigger_substr.lower(),
            "tool_name": tool_name,
            "tool_args": tool_args or {},
            "content": content
        })

    def chat_completion(self, messages: List[Dict[str, Any]], tools: Any = None, temperature: float = 0.2, format: Any = None) -> Dict[str, Any]:
        self.call_history.append({"messages": messages, "tools": tools})

        # 1. Sequential queue takes priority if available
        if self.canned_responses:
            return self.canned_responses.pop(0)

        # 2. Match based on last user message
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "").lower()
                break

        for rule in self.auto_match_rules:
            if rule["trigger"] in last_user_msg:
                if rule["tool_name"]:
                    return {
                        "message": {
                            "role": "assistant",
                            "content": rule.get("content", ""),
                            "tool_calls": [{
                                "id": "mock_call_1",
                                "type": "function",
                                "function": {
                                    "name": rule["tool_name"],
                                    "arguments": rule["tool_args"]
                                }
                            }]
                        }
                    }
                return {
                    "message": {
                        "role": "assistant",
                        "content": rule.get("content", ""),
                        "tool_calls": []
                    }
                }

        # Default fallback
        return {
            "message": {
                "role": "assistant",
                "content": "I am here to assist with Kepler Tech printing equipment and supplies.",
                "tool_calls": []
            }
        }
