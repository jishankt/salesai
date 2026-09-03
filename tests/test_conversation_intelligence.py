import unittest
from services.pre_router import get_conversational_intercept
from services.agent_loop import process_chat_message

class TestConversationIntelligence(unittest.TestCase):
    def test_identity_and_name_inquiries(self):
        is_hit, reply = get_conversational_intercept("what is your name")
        self.assertTrue(is_hit)
        self.assertIn("Kepler Sales Agent", reply)

        is_hit, reply = get_conversational_intercept("who made you")
        self.assertTrue(is_hit)
        self.assertIn("Kepler Tech", reply)

    def test_chit_chat_and_feelings(self):
        is_hit, reply = get_conversational_intercept("do you have feeelings")
        self.assertTrue(is_hit)
        self.assertNotIn("No products found", reply)
        self.assertIn("Kepler", reply or "printing")

    def test_location_and_office_info(self):
        is_hit, reply = get_conversational_intercept("where you compnay ocated")
        self.assertTrue(is_hit)
        self.assertIn("Dubai", reply)

    def test_discount_policy_inquiry(self):
        is_hit, reply = get_conversational_intercept("can you give me discounts for products")
        self.assertTrue(is_hit)
        self.assertIn("10%", reply)

    def test_learning_ability_inquiry(self):
        is_hit, reply = get_conversational_intercept("can you have leaning ability from the chat")
        self.assertTrue(is_hit)
        self.assertIn("session", reply.lower() or "conversation")

    def test_end_to_end_chit_chat_in_agent_loop(self):
        bubbles = process_chat_message("test-chitchat-session-1", "are you a human")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles)
        self.assertIn("Kepler Tech", text)
        self.assertNotIn("No products found", text)

if __name__ == "__main__":
    unittest.main()
