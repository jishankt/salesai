import unittest
from orchestration.state import ConversationAIState
from orchestration.state_repository import StateRepository

class TestConversationState(unittest.TestCase):
    def setUp(self):
        StateRepository.clear_cache()

    def test_state_creation_and_defaults(self):
        state = ConversationAIState(session_id="test_sess_1")
        self.assertEqual(state.session_id, "test_sess_1")
        self.assertEqual(state.intent, "general")
        self.assertEqual(state.sales_stage, "discovery")
        self.assertEqual(state.buying_intent, "none")
        self.assertIsNone(state.selected_product_id)

    def test_state_serialization(self):
        state = ConversationAIState(
            session_id="test_sess_2",
            intent="consumables",
            sales_stage="recommendation",
            category="technical_cad",
            selected_product_id="SC-T3700DE",
            buying_intent="high"
        )
        d = state.to_dict()
        self.assertEqual(d["session_id"], "test_sess_2")
        self.assertEqual(d["selected_product_id"], "SC-T3700DE")
        self.assertEqual(d["buying_intent"], "high")

        restored = ConversationAIState.from_dict(d)
        self.assertEqual(restored.session_id, state.session_id)
        self.assertEqual(restored.selected_product_id, state.selected_product_id)
        self.assertEqual(restored.buying_intent, "high")

    def test_repository_save_and_load(self):
        state = StateRepository.load("session_repo_test")
        self.assertEqual(state.session_id, "session_repo_test")
        self.assertIsNone(state.category)

        state.category = "photo_booth"
        state.selected_product_id = "CX-02"
        state.quantity = 5
        StateRepository.save(state)

        # Clear memory cache to verify persistence loading
        StateRepository.clear_cache()
        loaded = StateRepository.load("session_repo_test")
        self.assertEqual(loaded.category, "photo_booth")
        self.assertEqual(loaded.selected_product_id, "CX-02")
        self.assertEqual(loaded.quantity, 5)

if __name__ == "__main__":
    unittest.main()
