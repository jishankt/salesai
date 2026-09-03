import unittest
from services.discovery_engine import is_broad_query, get_discovery_question, compute_satisfaction_score
from tools.handlers import search_products

class TestDiscoveryEngine(unittest.TestCase):
    def test_01_broad_query_detection(self):
        self.assertTrue(is_broad_query("no i want ink")[0])
        self.assertTrue(is_broad_query("i need a printer")[0])
        self.assertTrue(is_broad_query("show me canvas")[0])
        self.assertTrue(is_broad_query("inks")[0])

    def test_02_specific_query_passthrough(self):
        self.assertFalse(is_broad_query("Epson SureColor SC-P9500")[0])
        self.assertFalse(is_broad_query("Citizen CX-02 photo printer")[0])
        self.assertFalse(is_broad_query("UltraChrome PRO12 Photo Black 700ml")[0])

    def test_03_consultative_question_returned_on_broad(self):
        res = search_products("no i want ink")
        self.assertIn("What printer model do you have?", res)
        self.assertIn("Which color(s) or cartridge size", res)

    def test_04_satisfaction_score_computation(self):
        dummy_prod = {
            "_id": "C11CH13301A3",
            "name": "Epson SureColor SC-P9500 Large Format Printer Spectro",
            "description": "High precision wide format printer for fine art",
            "price": 4500.0,
            "stock": 10
        }
        score = compute_satisfaction_score(dummy_prod, "Epson SureColor SC-P9500 fine art", budget=5000.0)
        self.assertGreaterEqual(score, 80.0)
        self.assertLessEqual(score, 100.0)

if __name__ == "__main__":
    unittest.main()
