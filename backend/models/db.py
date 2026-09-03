"""
Shared database layer.

Tries MongoDB first; if unavailable, falls back to an in-memory store that is
persisted to db.json on every write so a restart doesn't lose demo data.

NOTE: the JSON-file fallback is fine for local development / demos. It is not
safe for concurrent multi-process deployment (no locking) — point MONGO_URI
at a real MongoDB instance for anything beyond a single-process demo.
"""
import json
import os
import threading
from datetime import datetime

from pymongo import MongoClient

from config import Config

import logging

logger = logging.getLogger(__name__)

_lock = threading.Lock()

USE_IN_MEMORY = False
client = None
db = None

try:
    client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=1500)
    client.admin.command("ping")
    db = client[Config.DB_NAME]
    logger.info("MongoDB connection SUCCESS. Using live database.")
    # Create indexes for optimal performance
    db["leads"].create_index("session_id", unique=True)
    db["orders"].create_index("session_id")
    db["orders"].create_index("created_at")
    logger.info("MongoDB indexes created successfully.")
except Exception as e:
    USE_IN_MEMORY = True
    db = None
    logger.warning("=" * 70)
    logger.warning("WARNING: MongoDB connection FAILED (%s).", e)
    logger.warning("CRITICAL NOTICE: Falling back to IN-MEMORY DATABASE (db.json).")
    logger.warning("This mode is suitable ONLY for local single-process development/demos.")
    logger.warning("Do NOT use db.json in production multi-process deployments!")
    logger.warning("=" * 70)

MEM_DB = {
    "products": {},
    "leads": {},
    "orders": {},
    "chat_sessions": {},
    "carts": {},
    "match_logs": {},
}

DB_FILE = os.getenv("MEM_DB_FILE", "db.json")


def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


def datetime_parser(dct):
    for k, v in dct.items():
        if isinstance(v, str):
            try:
                dct[k] = datetime.fromisoformat(v)
            except ValueError:
                pass
    return dct


def save_mem_db():
    if not USE_IN_MEMORY:
        return
    with _lock:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(MEM_DB, f, default=json_serial, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save in-memory database to file: {e}")


def load_mem_db():
    global MEM_DB
    if not USE_IN_MEMORY:
        return

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f, object_hook=datetime_parser)
                for key in MEM_DB:
                    if key in loaded:
                        MEM_DB[key] = loaded[key]
            print(f"Loaded database from '{DB_FILE}' successfully.")
        except Exception as e:
            print(f"Failed to load database from '{DB_FILE}': {e}.")

    # Always reload and sync products from products.json to prevent stale catalog data
    try:
        with open("products.json", "r", encoding="utf-8") as f:
            products_list = json.load(f)
            for p in products_list:
                pid = p.get("_id")
                existing = MEM_DB["products"].get(pid, {})
                created_at = existing.get("created_at") or datetime.utcnow()
                MEM_DB["products"][pid] = {
                    "_id": pid,
                    "sku": p.get("sku", pid),
                    "row_id": p.get("row_id", ""),
                    "name": p["name"],
                    "price": float(p["price"]),
                    "stock": int(p.get("stock", 10)),
                    "availability": p.get("availability", "In Stock" if int(p.get("stock", 10)) > 0 else "Out of Stock"),
                    "description": p["description"],
                    "tags": p.get("tags", []),
                    "image_url": p.get("image_url", ""),
                    "website_url": p.get("website_url", ""),
                    "web_url": p.get("web_url", ""),
                    "category": p.get("category", "Printers" if "printer" in p["name"].lower() else "Inks & Consumables"),
                    "consumables": p.get("consumables", []),
                    "created_at": created_at,
                }
                if "item_group" in p:
                    MEM_DB["products"][pid]["item_group"] = p["item_group"]
        save_mem_db()
        print(f"Synced {len(MEM_DB['products'])} products from products.json into active database.")
    except Exception as e:
        print(f"Failed to sync products from products.json: {e}")


if USE_IN_MEMORY:
    load_mem_db()


def get_collection(name):
    """Returns a Mongo collection, or None when running in-memory."""
    return db[name] if db is not None else None
