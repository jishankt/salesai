import unittest
from services.response_validator import (
    check_json_leakage,
    check_internal_leaks,
    check_competitor_mentions,
    check_price_bounds,
    validate_ai_response
)

class TestResponseValidator(unittest.TestCase):
    def test_json_leakage_detection(self):
        leak_1 = '{"name": "search_products", "arguments": {"query": "ink"}}'
        self.assertTrue(check_json_leakage(leak_1))
        
        normal_text = "Here is the Epson SureColor SC-P9500 for 4500 AED."
        self.assertFalse(check_json_leakage(normal_text))

    def test_internal_leaks_detection(self):
        leak_text = "Checking database row_id and collections in session_id"
        has_leak, term = check_internal_leaks(leak_text)
        self.assertTrue(has_leak)
        self.assertIn("row_id", term)

        safe_text = "We have genuine Epson OEM UltraChrome inks in stock."
        has_leak, _ = check_internal_leaks(safe_text)
        self.assertFalse(has_leak)

    def test_competitor_detection(self):
        comp_text = "You can also check Shutterfly or Etsy for options."
        has_comp, comp = check_competitor_mentions(comp_text)
        self.assertTrue(has_comp)

        safe_text = "We specialize in Citizen photo printers and Innova media."
        has_comp, _ = check_competitor_mentions(safe_text)
        self.assertFalse(has_comp)

    def test_price_bounds_detection(self):
        invalid_text = "We are offering a free printer with every order!"
        has_err, reason = check_price_bounds(invalid_text)
        self.assertTrue(has_err)

        valid_text = "The Citizen CX-02 is available for 3200 AED."
        has_err, _ = check_price_bounds(valid_text)
        self.assertFalse(has_err)

    def test_validate_ai_response_end_to_end(self):
        valid_res, _, sanitized = validate_ai_response("The Epson SC-P9500 is 4500 AED. Would you like a quotation?")
        self.assertTrue(valid_res)
        self.assertIn("4500 AED", sanitized)

        invalid_res, reason, _ = validate_ai_response('{"name": "checkout_cart"}')
        self.assertFalse(invalid_res)
        self.assertEqual(reason, "json_leakage_detected")

if __name__ == "__main__":
    unittest.main()
