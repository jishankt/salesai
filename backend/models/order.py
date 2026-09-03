import uuid
from datetime import datetime

from models.db import MEM_DB, USE_IN_MEMORY, get_collection, save_mem_db
from models.product import Product


class InsufficientStockError(Exception):
    pass


class Order:
    @classmethod
    def get_collection(cls):
        return get_collection("orders")

    @classmethod
    def create_order(cls, session_id, items, customer_name, customer_contact):
        """
        Validates stock, decrements it, and creates the order record.
        Payment link is NOT set here — call payment.attach_payment_link(order)
        afterward so the payment provider stays swappable.
        """
        # Validate everything first so we never partially decrement stock.
        resolved = []
        for item in items:
            prod = Product.find_by_id(item["product_id"])
            if not prod:
                raise ValueError(f"Product ID '{item['product_id']}' not found.")
            qty = int(item["quantity"])
            if prod["stock"] < qty:
                raise InsufficientStockError(
                    f"'{prod['name']}' only has {prod['stock']} units left. Cannot order {qty}."
                )
            resolved.append((prod, qty))

        total_amount = 0.0
        order_items = []
        for prod, qty in resolved:
            total_amount += prod["price"] * qty
            order_items.append({
                "product_id": prod["_id"],
                "name": prod["name"],
                "quantity": qty,
                "price": prod["price"],
            })
            Product.update_stock(prod["_id"], -qty)

        order_id = "SO-" + str(uuid.uuid4())[:8].upper()
        order_doc = {
            "_id": order_id,
            "session_id": session_id,
            "customer_name": customer_name,
            "customer_contact": customer_contact,
            "items": order_items,
            "total_amount": total_amount,
            "status": "pending",
            "payment_status": "unpaid",
            "payment_link": None,
            "payment_provider": None,
            "created_at": datetime.utcnow(),
        }

        if USE_IN_MEMORY:
            MEM_DB["orders"][order_id] = order_doc
            save_mem_db()
        else:
            cls.get_collection().insert_one(order_doc)
        return order_doc

    @classmethod
    def set_payment_link(cls, order_id, link, provider):
        if USE_IN_MEMORY:
            order = MEM_DB["orders"].get(order_id)
            if order:
                order["payment_link"] = link
                order["payment_provider"] = provider
                save_mem_db()
            return order
        cls.get_collection().update_one(
            {"_id": order_id},
            {"$set": {"payment_link": link, "payment_provider": provider}},
        )
        return cls.get_by_id(order_id)

    @classmethod
    def set_payment_status(cls, order_id, payment_status, status=None):
        status = status or ("completed" if payment_status == "paid" else "pending")
        if USE_IN_MEMORY:
            order = MEM_DB["orders"].get(order_id)
            if order:
                order["payment_status"] = payment_status
                order["status"] = status
                save_mem_db()
            return order
        cls.get_collection().update_one(
            {"_id": order_id},
            {"$set": {"payment_status": payment_status, "status": status}},
        )
        return cls.get_by_id(order_id)

    @classmethod
    def get_by_id(cls, order_id):
        if USE_IN_MEMORY:
            return MEM_DB["orders"].get(order_id)
        return cls.get_collection().find_one({"_id": order_id})

    @classmethod
    def get_all(cls):
        if USE_IN_MEMORY:
            result = []
            for o in MEM_DB["orders"].values():
                safe = dict(o)
                if isinstance(safe.get("created_at"), datetime):
                    safe["created_at"] = safe["created_at"].isoformat() + "Z"
                elif isinstance(safe.get("created_at"), str) and not safe["created_at"].endswith("Z"):
                    safe["created_at"] += "Z"
                result.append(safe)
            return result
        return list(cls.get_collection().find({}))

    @classmethod
    def get_by_session(cls, session_id):
        if USE_IN_MEMORY:
            return [o for o in MEM_DB["orders"].values() if o.get("session_id") == session_id]
        return list(cls.get_collection().find({"session_id": session_id}))
