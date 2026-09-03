from datetime import datetime

from models.db import MEM_DB, USE_IN_MEMORY, get_collection, save_mem_db
from models.product import Product


class Cart:
    """A simple per-session running cart, so customers can add items across
    multiple chat turns instead of everything being a single-shot order."""

    @classmethod
    def get_collection(cls):
        return get_collection("carts")

    @classmethod
    def _empty(cls, session_id):
        return {"_id": session_id, "session_id": session_id, "items": {}, "updated_at": datetime.utcnow()}

    @classmethod
    def get(cls, session_id):
        if USE_IN_MEMORY:
            return MEM_DB["carts"].get(session_id, cls._empty(session_id))
        doc = cls.get_collection().find_one({"_id": session_id})
        return doc or cls._empty(session_id)

    @classmethod
    def get_all(cls):
        if USE_IN_MEMORY:
            return list(MEM_DB["carts"].values())
        return list(cls.get_collection().find({}))

    @classmethod
    def add_item(cls, session_id, product_id, quantity=1):
        prod = Product.find_by_id(product_id)
        if not prod:
            raise ValueError(f"Product ID '{product_id}' not found.")

        cart = cls.get(session_id)
        items = cart.get("items", {})
        items[product_id] = items.get(product_id, 0) + int(quantity)
        cart["items"] = items
        cart["updated_at"] = datetime.utcnow()
        cart["recovery_sent"] = False
        cls._save(session_id, cart)
        return cls.to_view(cart)

    @classmethod
    def remove_item(cls, session_id, product_id):
        cart = cls.get(session_id)
        cart.get("items", {}).pop(product_id, None)
        cls._save(session_id, cart)
        return cls.to_view(cart)

    @classmethod
    def clear(cls, session_id):
        cart = cls._empty(session_id)
        cls._save(session_id, cart)
        return cls.to_view(cart)

    @classmethod
    def _save(cls, session_id, cart):
        if USE_IN_MEMORY:
            MEM_DB["carts"][session_id] = cart
            save_mem_db()
        else:
            cls.get_collection().update_one({"_id": session_id}, {"$set": cart}, upsert=True)

    @classmethod
    def to_view(cls, cart):
        """Resolves product details + running total for display/checkout."""
        view_items = []
        total = 0.0
        for pid, qty in cart.get("items", {}).items():
            prod = Product.find_by_id(pid)
            if not prod:
                continue
            line_total = prod["price"] * qty
            total += line_total
            view_items.append({
                "product_id": pid,
                "name": prod["name"],
                "unit_price": prod["price"],
                "quantity": qty,
                "line_total": line_total,
                "stock": prod["stock"],
            })
        return {"session_id": cart.get("session_id"), "items": view_items, "total": total}
