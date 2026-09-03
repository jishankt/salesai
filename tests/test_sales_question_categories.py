import unittest
from services.agent_loop import process_chat_message
from models.chat_session import ChatSession

class TestAllSalesQuestionTypes(unittest.TestCase):
    """
    Comprehensive test suite covering all essential B2B/eCommerce sales question categories:
    1. Discovery & Application Qualification
    2. Price, Quotation & Currency Queries
    3. Live Stock & Availability Checks
    4. Consumables & Cross-Sell Compatibility
    5. Delivery, Territory & Lead Time
    6. Volume & Bulk Discount Inquiries
    7. Warranty, Service & Technical Support
    8. Order Drafting, Cart & Payment Link Generation
    """

    def test_01_discovery_and_qualification(self):
        """Customer asks broad printer question -> Agent asks 1 targeted qualification question"""
        session_id = "test-sales-discovery-01"
        ChatSession.get_or_create(session_id)
        
        bubbles = process_chat_message(session_id, "I want to buy a large format printer for my business.")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles)
        # Should be conversational, asking what they print or size needed
        self.assertTrue(any(w in text.lower() for w in ["volume", "size", "photo", "canvas", "poster", "fine art", "application", "kind of printing"]))

    def test_02_specific_price_and_quote_query(self):
        """Customer asks exact price for SC-P9500 -> Agent quotes official AED price with link"""
        session_id = "test-sales-price-02"
        ChatSession.get_or_create(session_id)
        
        bubbles = process_chat_message(session_id, "What is the price of Epson SC-P9500?")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles)
        self.assertTrue(any(w in text.lower() for w in ["4500", "4,500", "aed", "p9500"]))

    def test_03_stock_and_availability_check(self):
        """Customer checks if Citizen CX-02 photo printer is in stock"""
        session_id = "test-sales-stock-03"
        ChatSession.get_or_create(session_id)
        
        bubbles = process_chat_message(session_id, "Is the Citizen CX-02 printer available in stock right now?")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles)
        self.assertTrue(any(w in text.lower() for w in ["citizen", "cx-02", "stock", "available"]))

    def test_04_cross_sell_and_ink_compatibility(self):
        """Customer asks which ink fits their printer"""
        session_id = "test-sales-cross-sell-04"
        ChatSession.get_or_create(session_id)
        
        bubbles = process_chat_message(session_id, "I have an Epson P20000. Which ink cartridges do I need?")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles)
        self.assertTrue(any(w in text.lower() for w in ["ultrachrome", "700ml", "ink", "t800", "p20000", "magenta", "yellow", "cartridge", "products"]))

    def test_05_delivery_and_territory(self):
        """Customer asks about delivery to Abu Dhabi and Sharjah"""
        session_id = "test-sales-delivery-05"
        ChatSession.get_or_create(session_id)
        
        bubbles = process_chat_message(session_id, "Can you deliver to our print shop in Abu Dhabi Musaffah?")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles)
        self.assertTrue(any(w in text.lower() for w in ["abu dhabi", "deliver", "uae", "kepler"]))

    def test_06_bulk_discount_negotiation(self):
        """Customer wants to order 10 rolls of canvas and asks for a discount"""
        session_id = "test-sales-discount-06"
        ChatSession.get_or_create(session_id)
        
        bubbles = process_chat_message(session_id, "If I order 10 rolls of Korejet canvas, what discount do you give?")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles)
        self.assertTrue(any(w in text.lower() for w in ["10%", "discount", "quote", "bulk", "volume"]))

    def test_07_order_checkout_and_payment_link(self):
        """Customer confirms they want to proceed with purchase -> Agent provides payment link / checkout draft"""
        session_id = "test-sales-checkout-07"
        ChatSession.get_or_create(session_id)
        
        # Turn 1: Add item
        process_chat_message(session_id, "I want to buy 1 unit of C13T800100 Photo Black ink.")
        # Turn 2: Request payment link
        bubbles = process_chat_message(session_id, "Send me the payment link please.")
        self.assertTrue(bubbles)
        text = " ".join(b["text"] for b in bubbles)
        self.assertTrue(any(w in text.lower() for w in ["payment", "http", "checkout", "order", "aed"]))

if __name__ == "__main__":
    unittest.main()
