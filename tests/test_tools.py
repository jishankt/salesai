import pytest

from app import app as flask_app
from models.product import Product
from models.cart import Cart
from models.order import Order
from tools.handlers import add_to_cart, view_cart, remove_from_cart, checkout_cart, create_order


@pytest.fixture(autouse=True)
def app_context():
    with flask_app.app_context():
        yield


@pytest.fixture
def sample_product_id():
    products = Product.get_all_products()
    assert products, "products.json should have seeded at least one product"
    pid = products[0]["_id"]
    Product.update_stock(pid, 50)
    return pid


def test_add_and_view_cart(sample_product_id):
    session_id = "test-session-cart-1"
    Cart.clear(session_id)

    result = add_to_cart(session_id, sample_product_id, 2)
    assert "Cart updated" in result

    view = view_cart(session_id)
    assert "Cart total" not in view or "Current cart" in view  # sanity: view_cart uses its own wording
    assert "Current cart" in view


def test_remove_from_cart(sample_product_id):
    session_id = "test-session-cart-2"
    Cart.clear(session_id)
    add_to_cart(session_id, sample_product_id, 1)
    result = remove_from_cart(session_id, sample_product_id)
    assert "empty" in result.lower()


def test_checkout_cart_requires_items():
    session_id = "test-session-cart-empty"
    Cart.clear(session_id)
    result = checkout_cart(session_id, "Test User", "0501234567")
    assert result.startswith("ERROR")


def test_checkout_cart_happy_path(sample_product_id):
    session_id = "test-session-cart-checkout"
    Cart.clear(session_id)
    add_to_cart(session_id, sample_product_id, 1)

    result = checkout_cart(session_id, "Test User", "0501234567")
    # Should render the receipt card HTML, not an error
    assert "ERROR" not in result
    assert "ORDER PLACED" in result or "order-receipt-card" in result

    # Cart should be cleared after checkout
    view = view_cart(session_id)
    assert "empty" in view.lower()


def test_create_order_requires_name_and_contact(sample_product_id):
    session_id = "test-session-order-1"
    items = [{"product_id": sample_product_id, "quantity": 1}]
    result = create_order(session_id, items, "", "")
    assert result.startswith("ERROR")


def test_create_order_supports_backorder_quotation(sample_product_id):
    session_id = "test-session-order-2"
    prod = Product.find_by_id(sample_product_id)
    items = [{"product_id": sample_product_id, "quantity": prod["stock"] + 1000}]
    result = create_order(session_id, items, "Test User", "0501234567")
    assert "order-receipt-card" in result
    assert "QUOTATION" in result
