import json
from datetime import datetime
import pytest
from app import app, BoundedLockManager
from config import Config
from models.order import Order


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_admin_routes_auth_required(client):
    # Admin route returns 401 without X-Admin-Key
    resp = client.get("/api/admin/leads")
    assert resp.status_code == 401
    assert "Unauthorized" in resp.get_json()["error"]

    # Admin route succeeds with X-Admin-Key
    headers = {"X-Admin-Key": Config.ADMIN_API_KEY}
    resp = client.get("/api/admin/leads", headers=headers)
    assert resp.status_code == 200


def test_public_products_endpoint(client):
    resp = client.get("/api/products")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_checkout_endpoint_provider_restrictions(client):
    # Setup a mock order
    order_id = "test_order_123"
    order_doc = {
        "_id": order_id,
        "session_id": "test_session",
        "customer_name": "Test Customer",
        "customer_contact": "9999999999",
        "total_amount": 100.0,
        "items": [],
        "payment_status": "unpaid",
        "created_at": datetime.utcnow()
    }
    from models.db import USE_IN_MEMORY, MEM_DB, save_mem_db
    if USE_IN_MEMORY:
        MEM_DB["orders"][order_id] = order_doc
        save_mem_db()
    else:
        Order.get_collection().insert_one(order_doc)

    # Test under PAYMENT_PROVIDER=mock (default)
    orig_provider = Config.PAYMENT_PROVIDER
    Config.PAYMENT_PROVIDER = "mock"
    resp = client.post(f"/api/checkout/{order_id}")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"

    # Test under PAYMENT_PROVIDER=razorpay
    Config.PAYMENT_PROVIDER = "razorpay"
    resp = client.post(f"/api/checkout/{order_id}")
    assert resp.status_code == 403
    assert "Forbidden" in resp.get_json()["error"]

    # Clean up
    Config.PAYMENT_PROVIDER = orig_provider


def test_razorpay_webhook_invalid_signature(client):
    resp = client.post(
        "/api/webhook/razorpay",
        headers={"X-Razorpay-Signature": "invalid-sig"},
        json={"event": "payment_link.paid"}
    )
    assert resp.status_code == 400
    assert "Invalid signature" in resp.get_json()["error"]


def test_bounded_lock_manager():
    manager = BoundedLockManager(max_locks=3)
    # Get locks for 3 senders
    l1 = manager.get_lock("sender1")
    l2 = manager.get_lock("sender2")
    l3 = manager.get_lock("sender3")

    # Get a 4th sender's lock, which should evict one of the unlocked ones
    l4 = manager.get_lock("sender4")
    assert len(manager._locks) == 3
    # Check that "sender1" was evicted since it was the oldest and unlocked
    assert "sender1" not in manager._locks

    # Lock sender2 and check that it is NOT evicted when capacity is reached
    l2.acquire()
    try:
        manager.get_lock("sender5")
        # sender3 should be evicted instead of sender2 because sender2 is locked
        assert "sender3" not in manager._locks
        assert "sender2" in manager._locks
    finally:
        l2.release()
