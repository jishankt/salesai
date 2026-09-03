import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger("salesai.product_client")

class ProductIntelligenceClient:
    """
    High-performance typed API client for Kepler Tech LLC Product Intelligence Service.
    Includes zero-downtime local fallback if the microservice is offline or initializing.
    """
    def __init__(self, base_url: str = "http://127.0.0.1:8005", timeout: int = 5):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def search(self, query: str, conversation_id: Optional[str] = None, customer_id: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        payload = {
            "query": query,
            "conversation_id": conversation_id,
            "customer_id": customer_id,
            "limit": limit
        }
        try:
            resp = requests.post(f"{self.base_url}/api/v1/products/search", json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"Product Intelligence Service returned HTTP {resp.status_code}. Using local search fallback.")
        except Exception as e:
            logger.info(f"Product Intelligence Service not reachable ({e}). Gracefully executing via direct in-process engine.")
        
        # Local direct fallback (Zero-Regression safeguard)
        return self._local_search_fallback(query, limit)

    def _local_search_fallback(self, query: str, limit: int = 5) -> Dict[str, Any]:
        from models.product import Product
        results = Product.search_products(query)
        matched = []
        for p in results[:limit]:
            matched.append({
                "id": p.get("_id"),
                "name": p.get("name"),
                "price": p.get("price", 0.0),
                "stock_status": "in_stock" if p.get("stock", 0) > 0 else "out_of_stock",
                "website_url": f"https://www.keplertechllc.com/product/{p.get('name', '').lower().replace(' ', '-')}/",
                "confidence": 0.85
            })
        return {
            "intent": "PRODUCT_SEARCH" if matched else "NO_RESULT",
            "matched_products": matched,
            "related_products": [],
            "formatted_whatsapp_message": None,
            "needs_clarification": len(matched) == 0
        }

# Global singleton client
product_client = ProductIntelligenceClient()
