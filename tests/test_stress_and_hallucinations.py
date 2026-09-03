import unittest
from services.agent_loop import process_chat_message
from services.response_validator import validate_ai_response
from models.chat_session import ChatSession

class TestHallucinationAndEdgeCases(unittest.TestCase):
    def setUp(self):
        self.session_id = "test-hallucination-suite-1"
        ChatSession.get_or_create(self.session_id)

    # 1. Hallucination Tests
    def test_fake_hardware_model_hallucination(self):
        """Customer asks for non-existent or competitor models (e.g. Epson P999999 or Canon imagePROGRAF)"""
        bubbles = process_chat_message(self.session_id, "Do you have the Epson SureColor P999999 500-inch printer?")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles)
        # Should not claim we have a P999999 in stock or give fake prices
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
        bubbles = process_chat_message(self.session_id, "asdfghjk qwerty ???")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles)
        # Should politely ask for clarification without crashing
        self.assertTrue(len(text) > 0)
        self.assertNotIn("Error:", text)

    def test_confusing_double_negative(self):
        """Customer sends confusing negative phrasing: 'no i dont want not ink'"""
        bubbles = process_chat_message(self.session_id, "no i dont want not ink, i need printer")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles)
        self.assertTrue(len(text) > 0)
        self.assertNotIn("Error executing tool", text)

    # 3. Multi-Turn Chat History & Context Memory Questions
    def test_multi_turn_history_recall(self):
        """Test multi-turn context retention: customer introduces their printer model first, then asks for ink"""
        session_id = "test-history-context-session"
        
        # Turn 1: Customer mentions their model
        b1 = process_chat_message(session_id, "I have an Epson SureColor SC-P9500 printer in my Dubai studio.")
        self.assertTrue(b1)
        
        # Turn 2: Customer asks follow-up referencing previous turn without repeating the full name
        b2 = process_chat_message(session_id, "What is the price of Photo Black ink for it?")
        self.assertTrue(b2)
        text2 = " ".join(b["text"] for b in b2)
        # Should understand it's for the P9500 (Photo Black / T800100 / 700ml / UltraChrome)
        self.assertTrue(any(w in text2.lower() for w in ["black", "ink", "aed", "450", "p9500", "ultrachrome"]))

    def test_session_remembers_customer_name(self):
        """Customer introduces their name, then asks what their name is"""
        session_id = "test-name-history-session"
        
        # Turn 1: Name given
        process_chat_message(session_id, "My name is Tariq from Al Ain.")
        
        # Turn 2: Follow-up
        b2 = process_chat_message(session_id, "Hello again")
        text2 = " ".join(b["text"] for b in b2)
        self.assertIn("Tariq", text2)

if __name__ == "__main__":
    unittest.main()
