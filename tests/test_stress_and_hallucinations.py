import unittest
from unittest.mock import patch
from services.agent_loop import process_chat_message
from services.response_validator import validate_ai_response
from models.chat_session import ChatSession
from tests.mock_llm import MockLLMClient

class TestHallucinationAndEdgeCases(unittest.TestCase):
    def setUp(self):
        self.session_id = "test-hallucination-suite-1"
        ChatSession.get_or_create(self.session_id)
        self.mock_client = MockLLMClient()

    # 1. Hallucination Tests
    def test_fake_hardware_model_hallucination(self):
        """Customer asks for non-existent or competitor models (e.g. Epson P999999 or Canon imagePROGRAF)"""
        with patch("services.agent_loop.chat_completion", side_effect=self.mock_client.chat_completion), \
             patch("services.ollama_client.chat_completion", side_effect=self.mock_client.chat_completion):
            self.mock_client.add_rule(
                trigger_substr="p999999",
                content="We do not carry any Epson P999999 model. We offer the Epson SureColor SC-P9500 and SC-P7500."
            )
            bubbles = process_chat_message(self.session_id, "Do you have the Epson SureColor P999999 500-inch printer?")
            self.assertTrue(bubbles)
            text = " ".join(b["text"] for b in bubbles)
            self.assertNotIn("P999999 in stock", text.lower())

    def test_free_hardware_claim_rejection(self):
        """Validator should reject claims of 0 AED free printer"""
        is_valid, reason, _ = validate_ai_response("We are offering a free printer for 0 AED with your order.")
        self.assertFalse(is_valid)
        self.assertIn("pricing_bounds_violation", reason)

    def test_prohibited_competitor_rejection(self):
        """Validator should reject competitor endorsements"""
        is_valid, reason, _ = validate_ai_response("You can buy Canon plotters or Roland cutters from Shutterfly instead.")
        self.assertFalse(is_valid)
        self.assertIn("competitor_mention_detected", reason)

    # 2. Confusing / Ambiguous / Typo Questions
    def test_gibberish_and_confusing_queries(self):
        """Customer sends random typing noise or fragmented questions"""
        with patch("services.agent_loop.chat_completion", side_effect=self.mock_client.chat_completion), \
             patch("services.ollama_client.chat_completion", side_effect=self.mock_client.chat_completion):
            self.mock_client.add_rule(
                trigger_substr="asdfghjk",
                content="Could you please clarify what printing equipment or inks you are looking for?"
            )
            bubbles = process_chat_message(self.session_id, "asdfghjk qwerty ???")
            self.assertTrue(bubbles)
            text = " ".join(b["text"] for b in bubbles)
            self.assertTrue(len(text) > 0)
            self.assertNotIn("Error:", text)

    def test_confusing_double_negative(self):
        """Customer sends confusing negative phrasing: 'no i dont want not ink'"""
        with patch("services.agent_loop.chat_completion", side_effect=self.mock_client.chat_completion), \
             patch("services.ollama_client.chat_completion", side_effect=self.mock_client.chat_completion):
            self.mock_client.add_rule(
                trigger_substr="printer",
                content="Here are our available Epson SureColor printers."
            )
            bubbles = process_chat_message(self.session_id, "no i dont want not ink, i need printer")
            self.assertTrue(bubbles)
            text = " ".join(b["text"] for b in bubbles)
            self.assertTrue(len(text) > 0)
            self.assertNotIn("Error executing tool", text)

    # 3. Multi-Turn Chat History & Context Memory Questions
    def test_multi_turn_history_recall(self):
        """Test multi-turn context retention: customer introduces their printer model first, then asks for ink"""
        session_id = "test-history-context-session"
        ChatSession.get_or_create(session_id)
        
        with patch("services.agent_loop.chat_completion", side_effect=self.mock_client.chat_completion), \
             patch("services.ollama_client.chat_completion", side_effect=self.mock_client.chat_completion):
            self.mock_client.add_rule(
                trigger_substr="sc-p9500",
                content="Great, the Epson SureColor SC-P9500 is a fantastic 44-inch photo printer. How can I help with supplies?"
            )
            self.mock_client.add_rule(
                trigger_substr="photo black",
                tool_name="get_printer_consumables",
                tool_args={"printer_query": "sc-p9500"}
            )
            
            b1 = process_chat_message(session_id, "I have an Epson SureColor SC-P9500 printer in my Dubai studio.")
            self.assertTrue(b1)
            
            b2 = process_chat_message(session_id, "What is the price of Photo Black ink for it?")
            self.assertTrue(b2)
            text2 = " ".join(b["text"] for b in b2)
            self.assertTrue(any(w in text2.lower() for w in ["black", "ink", "aed", "450", "p9500", "ultrachrome"]))

    def test_session_remembers_customer_name(self):
        """Customer introduces their name, then asks what their name is"""
        session_id = "test-name-history-session"
        ChatSession.get_or_create(session_id)
        
        with patch("services.agent_loop.chat_completion", side_effect=self.mock_client.chat_completion), \
             patch("services.ollama_client.chat_completion", side_effect=self.mock_client.chat_completion):
            self.mock_client.add_rule(
                trigger_substr="tariq",
                content="Nice to meet you Tariq! How can I assist you today?"
            )
            self.mock_client.add_rule(
                trigger_substr="hello again",
                content="Welcome back, Tariq! What can I find for you?"
            )
            process_chat_message(session_id, "My name is Tariq from Al Ain.")
            
            b2 = process_chat_message(session_id, "Hello again")
            text2 = " ".join(b["text"] for b in b2)
            self.assertIn("Tariq", text2)

    def test_customer_frustration_and_apology(self):
        """Customer expresses anger/frustration; system should apologize politely and offer assistance or escalation"""
        session_id = "test-frustration-session"
        ChatSession.get_or_create(session_id)
        bubbles = process_chat_message(session_id, "I am really frustrated and annoyed with this service!")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles).lower()
        self.assertIn("sorry", text)

if __name__ == "__main__":
    unittest.main()

