import unittest
from orchestration.orchestrator import ConversationOrchestrator
from orchestration.state_repository import StateRepository

class TestConversationOrchestrator(unittest.TestCase):
    def setUp(self):
        StateRepository.clear_cache()

    def test_conversational_intercept(self):
        res = ConversationOrchestrator.process_message("test_orch_1", "Hello")
        self.assertIn("content", res)
        self.assertTrue(any(k in res["content"].lower() for k in ["hello", "welcome", "assist"]))

    def test_frustration_apology(self):
        res = ConversationOrchestrator.process_message("test_orch_2", "This is so frustrating and annoying!")
        self.assertIn("content", res)
        self.assertIn("sorry", res["content"].lower())

    def test_exact_consumables_lookup(self):
        res = ConversationOrchestrator.process_message("test_orch_3", "SC T3700DE just check this models inks")
        self.assertIn("content", res)
        self.assertEqual(res["orchestration"]["intent"], "consumables")
        self.assertIn("UltraChrome", res["content"])

    def test_exact_product_search(self):
        res = ConversationOrchestrator.process_message("test_orch_4", "Show me CX-02 printer")
        self.assertIn("content", res)
        self.assertIn("Citizen CX", res["content"])

    def test_one_question_qualification(self):
        res = ConversationOrchestrator.process_message("test_orch_5", "Need a printer for architecture blueprints")
        self.assertIn("content", res)
        self.assertEqual(res["orchestration"]["intent"], "product_discovery")
        self.assertEqual(res["orchestration"]["action"], "ask_qualification")
        # Exactly one question asked
        self.assertEqual(res["content"].count("?"), 1)
        self.assertIn("maximum drawing size", res["content"].lower())

    def test_quotation_intent(self):
        res = ConversationOrchestrator.process_message("test_orch_6", "Need a formal quotation for 5 units of CX-02")
        self.assertIn("content", res)
        self.assertEqual(res["orchestration"]["intent"], "quotation")
        self.assertTrue("AED" in res["content"] or "Price" in res["content"] or "Citizen" in res["content"])

if __name__ == "__main__":
    unittest.main()
