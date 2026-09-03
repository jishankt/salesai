import unittest
from services.pre_router import normalize_user_input, detect_multi_intents
from models.product import Product
from tools.handlers import search_products

class TestAdvancedRoutingAndConfidence(unittest.TestCase):
    def test_01_input_normalization_and_typos(self):
        # Typo correction tests
        self.assertEqual(normalize_user_input("epsn prntr"), "epson printer")
        self.assertEqual(normalize_user_input("ctzn cx-02"), "citizen cx-02")
        self.assertEqual(normalize_user_input("inva canvs roll"), "innova canvas roll")
        self.assertEqual(normalize_user_input("deliver to shajar"), "deliver to sharjah")

    def test_02_multi_intent_decomposition(self):
        # Compound inquiry: Product + Territory
        msg = "price of epsn p9500 and do you deliver to Sharjah?"
        intents = detect_multi_intents(msg)
        
        types = [i["type"] for i in intents]
        self.assertIn("PRODUCT_QUERY", types)
        self.assertIn("TERRITORY_QUERY", types)
        
        terr_intent = [i for i in intents if i["type"] == "TERRITORY_QUERY"][0]
        self.assertEqual(terr_intent["territory"], "Sharjah")

    def test_03_confidence_gating_confirmed_match(self):
        # Exact product query should yield CONFIRMED mode
        results = Product.search_products("Epson SureColor SC-P9500")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].get("_match_mode"), "CONFIRMED")
        self.assertGreaterEqual(results[0].get("_match_score", 0), 80)

    def test_04_confidence_gating_needs_confirmation(self):
        # Partial / broad search should yield confidence flag or candidate
        res_text = search_products("large format")
        self.assertIn("Epson SureColor", res_text)

    def test_05_confidence_gating_not_found(self):
        # Non-existent product query
        res_text = search_products("XYZNonExistent3000Laser")
        self.assertIn("No products found", res_text)

if __name__ == "__main__":
    unittest.main()
