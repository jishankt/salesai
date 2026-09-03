"""
Payment provider abstraction.

Two providers are supported out of the box:
  - "mock" (default): generates a local /checkout/<order_id> page. No real
    money moves. This is what the project ships with so it runs anywhere
    with zero setup.
  - "razorpay": creates a real Razorpay order via their REST API and returns
    a hosted payment link, IF RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET are set.

Swapping providers is a one-line env var change (PAYMENT_PROVIDER), no code
changes needed elsewhere in the app.
"""
import hmac
import hashlib
import logging
import requests
from requests.auth import HTTPBasicAuth

from config import Config
from models.order import Order
from services.notifications import notify_order_event

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    pass


def verify_razorpay_signature(raw_body: bytes, signature: str) -> bool:
    """Verifies Razorpay HMAC SHA256 webhook signature against RAZORPAY_WEBHOOK_SECRET or RAZORPAY_KEY_SECRET."""
    secret = Config.RAZORPAY_WEBHOOK_SECRET or Config.RAZORPAY_KEY_SECRET
    if not secret or not signature:
        return False
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


def _mock_create_link(order: dict) -> str:
    return f"/checkout/{order['_id']}"


def _razorpay_create_link(order: dict) -> str:
    if not Config.RAZORPAY_KEY_ID or not Config.RAZORPAY_KEY_SECRET:
        raise PaymentError(
            "PAYMENT_PROVIDER=razorpay but RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET are not set."
        )

    # Razorpay Payment Links API — amount is in the smallest currency unit (paise/fils).
    amount_minor_units = int(round(order["total_amount"] * 100))
    payload = {
        "amount": amount_minor_units,
        "currency": Config.CURRENCY,
        "description": f"Order {order['_id']}",
        "customer": {
            "name": order.get("customer_name", ""),
            "contact": order.get("customer_contact", ""),
        },
        "notify": {"sms": True, "email": False},
        "reference_id": order["_id"],
    }
    try:
        res = requests.post(
            "https://api.razorpay.com/v1/payment_links",
            json=payload,
            auth=HTTPBasicAuth(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET),
            timeout=10,
        )
        res.raise_for_status()
        return res.json()["short_url"]
    except requests.exceptions.RequestException as e:
        raise PaymentError(f"Razorpay link creation failed: {e}") from e


PROVIDERS = {
    "mock": _mock_create_link,
    "razorpay": _razorpay_create_link,
}


def attach_payment_link(order: dict) -> dict:
    """Generates a payment link for a freshly created order, saves it, and
    fires an order-created notification. Falls back to the mock link if the
    configured provider errors out, so checkout never hard-fails."""
    provider_name = Config.PAYMENT_PROVIDER
    provider_fn = PROVIDERS.get(provider_name, _mock_create_link)

    try:
        link = provider_fn(order)
    except PaymentError as e:
        logger.warning("[payment] %s failed, falling back to mock link: %s", provider_name, e)
        provider_name = "mock"
        link = _mock_create_link(order)

    updated = Order.set_payment_link(order["_id"], link, provider_name)
    notify_order_event("order_created", updated or order)
    return updated or {**order, "payment_link": link, "payment_provider": provider_name}
