import os
import sys
import unittest

# Add product-intelligence to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.repository import ProductRepository
from src.ingest import ingest_from_csv_and_json
from src.search import HybridProductSearch
from src.models import ProductSearchRequest
from src.validator import ResponseValidator
from src.formatter import format_whatsapp_response

class TestProductIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = os.path.join(os.path.dirname(__file__), "test_products.db")
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
        cls.repo = ProductRepository(cls.db_path)
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "catalog.csv")
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "products.json")
        ingest_from_csv_and_json(cls.repo, csv_path, json_path)
        cls.searcher = HybridProductSearch(cls.repo)

    def test_01_exact_sku_search(self):
        req = ProductSearchRequest(query="C11CH37402DA")
        matched, related = self.searcher.search(req)
        self.assertTrue(len(matched) > 0)
        self.assertEqual(matched[0].sku, "C11CH37402DA")
        self.assertIn("P900", matched[0].name)
        print("\n[PASS] Exact SKU search: SC-P900 retrieved.")

    def test_02_use_case_and_category_search(self):
        req = ProductSearchRequest(query="I need a professional photo printer for studio use")
        matched, related = self.searcher.search(req)
        self.assertTrue(len(matched) > 0)
        self.assertIn("Photo", matched[0].category)
        print(f"\n[PASS] Use case search retrieved: {matched[0].name}")

    def test_03_compatible_recommendation_resolution(self):
        req = ProductSearchRequest(query="Epson SC P900")
        matched, related = self.searcher.search(req)
        self.assertTrue(len(matched) > 0)
        self.assertTrue(len(related) > 0)
        # SC-P900 should recommend UltraChrome Pro10 or Maintenance Tank
        rel_names = [r.name for r in related]
        self.assertTrue(any("UltraChrome" in n or "Maintenance" in n for n in rel_names))
        print(f"\n[PASS] Compatible supplies recommended for SC-P900: {rel_names}")

    def test_04_website_url_routing_integrity(self):
        req = ProductSearchRequest(query="Korejet Artistic Polycotton Canvas")
        matched, related = self.searcher.search(req)
        self.assertTrue(len(matched) > 0)
        url = matched[0].website_url
        self.assertTrue(ResponseValidator.validate_url(url))
        self.assertTrue(url.startswith("https://www.keplertechllc.com"))
        print(f"\n[PASS] Verified Website URL: {url}")

    def test_05_whatsapp_formatter(self):
        req = ProductSearchRequest(query="SC-P900")
        matched, related = self.searcher.search(req)
        msg = format_whatsapp_response(matched, related)
        self.assertIn("Recommended Product", msg)
        self.assertIn("P900", msg)
        self.assertIn("keplertechllc.com", msg)
        print("\n[PASS] Formatted WhatsApp message generated successfully.")


if __name__ == "__main__":
    unittest.main()
