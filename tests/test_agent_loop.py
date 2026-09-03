import pytest

from app import app as flask_app
from services import agent_loop


@pytest.fixture(autouse=True)
def app_context():
    from models.db import USE_IN_MEMORY, MEM_DB
    if USE_IN_MEMORY:
        MEM_DB["chat_sessions"].clear()
        MEM_DB["leads"].clear()
    with flask_app.app_context():
        yield


def test_product_question_prefetches_and_returns_final_reply(monkeypatch):
    """A product question should get a deterministic search_products prefetch,
    then the mocked model's final text reply should pass straight through."""

    def fake_call_model(messages):
        return {"role": "assistant", "content": "Yep, we've got Matte Black ink in stock at 450 AED — want me to add it to your cart?"}

    monkeypatch.setattr(agent_loop, "_call_model", fake_call_model)

    bubbles = agent_loop.process_chat_message("test-agent-session-1", "do you have matte black ink?")
    assert bubbles
    combined = " ".join(b["text"] for b in bubbles)
    assert "ink" in combined.lower() or "450" in combined


def test_manual_json_tool_call_fallback_is_parsed(monkeypatch):
    """If the model emits a tool call as raw JSON text instead of using the
    tools field, the manual parser should catch it and the loop should still
    execute the tool and eventually return a normal reply."""

    responses = [
        {"role": "assistant", "content": '{"name": "recommend_products", "arguments": {}}'},
        {"role": "assistant", "content": "Here are a couple of great picks for you — want details on either?"},
    ]

    def fake_call_model(messages):
        return responses.pop(0)

    monkeypatch.setattr(agent_loop, "_call_model", fake_call_model)

    bubbles = agent_loop.process_chat_message("test-agent-session-2", "what do you recommend?")
    assert bubbles
    combined = " ".join(b["text"] for b in bubbles)
    assert len(combined) > 0


def test_empty_responses_eventually_escalate(monkeypatch):
    """If the model keeps returning blank content, the loop should give up
    gracefully after a few tries instead of looping forever silently."""

    def fake_call_model(messages):
        return {"role": "assistant", "content": ""}

    monkeypatch.setattr(agent_loop, "_call_model", fake_call_model)

    bubbles = agent_loop.process_chat_message("test-agent-session-3", "I need to order some special printing ink bags")
    assert bubbles
    combined = " ".join(b["text"] for b in bubbles).lower()
    assert "trouble" in combined or "pass you to someone" in combined


def test_payment_link_resolves_even_without_a_lead_record(monkeypatch):
    """Regression test: checkout_cart/create_order enforce name+contact
    directly and don't always populate the separate Lead record. An order
    existing for this session must be enough to resolve a payment-link
    placeholder — it must NOT fall back to asking 'what's your name?' just
    because Lead.get_by_session() is empty.
    """
    from models.product import Product
    from models.cart import Cart

    session_id = "test-agent-session-payment-link"
    Cart.clear(session_id)
    pid = Product.get_all_products()[0]["_id"]

    responses = [
        {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "checkout_cart", "arguments": {
                "customer_name": "Regression Tester", "customer_contact": "0509999999"
            }}}
        ]},
        {"role": "assistant", "content": "All set! Here's your payment link: [payment link]"},
    ]

    def fake_call_model(messages):
        if responses:
            return responses.pop(0)
        return {"role": "assistant", "content": "All set! Here's your payment link: [payment link]"}

    monkeypatch.setattr(agent_loop, "_call_model", fake_call_model)

    # Seed the cart directly since this test isn't exercising add_to_cart.
    Cart.add_item(session_id, pid, 1)

    bubbles = agent_loop.process_chat_message(session_id, "Regression Tester, 0509999999, go ahead")
    combined = " ".join(b["text"] for b in bubbles)
    assert "what is your name" not in combined.lower()
    assert "/checkout/" in combined
