from flask import render_template, has_app_context

from config import Config


def render_receipt_card(order: dict) -> str:
    if has_app_context():
        try:
            return render_template("partials/receipt_card.html", order=order, currency=Config.CURRENCY)
        except Exception:
            pass
    # Fallback when executed outside Flask application context or on template error
    order_id = order.get("_id", "SO-DRAFT")
    total = order.get("total_amount", 0)
    link = order.get("payment_link", "")
    return f"\n\n🧾 *Quotation Draft {order_id}*\nTotal: **{total:.2f} AED**\nPayment/Checkout: {link}"


def render_payment_button(order_id: str, link: str) -> str:
    if has_app_context():
        try:
            return render_template("partials/payment_button.html", order_id=order_id, link=link)
        except Exception:
            pass
    return f"\n\n💳 Payment Link for {order_id}: {link}"


def render_payment_text(order_id: str, link: str) -> str:
    """Plain-text payment prompt for WhatsApp — no HTML, just a tappable link.

    Converts relative paths (e.g. /checkout/SO-XXXX) to absolute URLs using
    BASE_URL so the link works outside the local network.
    """
    base = Config.BASE_URL.rstrip("/")
    full_link = f"{base}{link}" if link.startswith("/") else link
    return f"\n\n✅ Order *{order_id}* confirmed!\nTap to pay: {full_link}"

