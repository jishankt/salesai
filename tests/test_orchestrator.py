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

    def test_multi_turn_cad_qualification_state_machine(self):
        """
        Validates the step-by-step CAD printer qualification state machine:
        Turn 1: "I need a CAD printer" -> category: technical_cad, asks print_size
        Turn 2: "A0" -> updates print_size: A0, asks scan_required
        Turn 3: "yes" -> updates scan_required: True, asks daily_volume
        Turn 4: "around 50 drawings" -> qualification complete, recommends products
        """
        session_id = "test_cad_multi_turn_flow"
        
        # Turn 1
        res1 = ConversationOrchestrator.process_message(session_id, "I need a CAD printer")
        self.assertEqual(res1["orchestration"]["intent"], "product_discovery")
        self.assertEqual(res1["orchestration"]["action"], "ask_qualification")
        self.assertIn("drawing size", res1["content"].lower())
        
        # Turn 2
        res2 = ConversationOrchestrator.process_message(session_id, "A0")
        self.assertEqual(res2["orchestration"]["intent"], "product_discovery")
        self.assertEqual(res2["orchestration"]["action"], "ask_qualification")
        self.assertIn("scanning", res2["content"].lower())
        
        # Turn 3
        res3 = ConversationOrchestrator.process_message(session_id, "yes")
        self.assertEqual(res3["orchestration"]["intent"], "product_discovery")
        self.assertEqual(res3["orchestration"]["action"], "ask_qualification")
        self.assertIn("drawings or plans", res3["content"].lower())
        
        # Turn 4
        res4 = ConversationOrchestrator.process_message(session_id, "around 50 drawings per day")
        self.assertEqual(res4["orchestration"]["intent"], "product_discovery")
        self.assertEqual(res4["orchestration"]["action"], "recommend_products")
        self.assertTrue("Epson SureColor" in res4["content"] or "SC-" in res4["content"] or "📦" in res4["content"])

if __name__ == "__main__":
    unittest.main()
