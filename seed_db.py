"""One-off CLI script to seed MongoDB directly (bypasses the Flask app/admin
auth — use this for initial local setup only)."""
import json
from datetime import datetime

from pymongo import MongoClient

from config import Config


def seed():
    client = MongoClient(Config.MONGO_URI)
    db = client[Config.DB_NAME]
    products_col = db["products"]

    products_col.delete_many({})

    try:
        with open("products.json", "r") as f:
            sample_products = json.load(f)

        for p in sample_products:
            p["created_at"] = datetime.utcnow()

        products_col.insert_many(sample_products)
        print(f"Database seeded successfully with {len(sample_products)} products from products.json!")
    except Exception as e:
        print(f"Error seeding database from JSON file: {e}")


if __name__ == "__main__":
    seed()
