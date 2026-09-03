"""
Fire-and-forget order notifications. Ships as a console-log stub; if
ORDER_WEBHOOK_URL is set, also POSTs the event there (e.g. a Slack incoming
webhook, a WhatsApp Business API bridge, or your own CRM endpoint).

Never raises — a broken notification should never break the chat flow.
"""
import json

import requests

from config import Config


def notify_order_event(event: str, order: dict):
    payload = {
        "event": event,
        "order_id": order.get("_id"),
        "customer_name": order.get("customer_name"),
        "customer_contact": order.get("customer_contact"),
        "total_amount": order.get("total_amount"),
        "payment_status": order.get("payment_status"),
        "payment_link": order.get("payment_link"),
    }

    print(f"[notify] {event}: {json.dumps(payload, default=str)}")

    if not Config.ORDER_WEBHOOK_URL:
        return

    try:
        requests.post(Config.ORDER_WEBHOOK_URL, json=payload, timeout=5)
    except requests.exceptions.RequestException as e:
        print(f"[notify] webhook delivery failed (non-fatal): {e}")
