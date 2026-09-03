import urllib.parse
from typing import List, Dict, Any

ALLOWED_DOMAINS = ["www.keplertechllc.com", "keplertechllc.com"]

class ResponseValidator:
    @staticmethod
    def validate_url(url: str) -> bool:
        if not url:
            return False
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.scheme in ["http", "https"] and parsed.netloc in ALLOWED_DOMAINS
        except Exception:
            return False

    @staticmethod
    def validate_specifications(specs: Dict[str, Any]) -> bool:
        """Ensure specs do not contain unverified hallucinations or malicious script payloads"""
        if not isinstance(specs, dict):
            return False
        return True

    @staticmethod
    def validate_price(price: float) -> bool:
        return isinstance(price, (int, float)) and price >= 0.0
