"""
JSON-to-MongoDB Database Migration Utility.

Loads in-memory database from db.json and imports all products, leads, orders,
and chat sessions into MongoDB using the MONGO_URI from .env.
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient

def datetime_parser(dct):
    for k, v in dct.items():
        if isinstance(v, str):
            try:
                # Try parsing ISO dates back to datetime objects
                if v.endswith("Z"):
                    v = v[:-1]
                dct[k] = datetime.fromisoformat(v)
            except ValueError:
                pass
    return dct

def main():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    db_name = os.getenv("DB_NAME", "sales_ai")
    db_file = os.getenv("MEM_DB_FILE", "db.json")

    if not os.path.exists(db_file):
        print(f"Error: Migration source file '{db_file}' not found.")
        return

    print(f"Reading source database '{db_file}'...")
    with open(db_file, "r") as f:
        data = json.load(f, object_hook=datetime_parser)

    print(f"Connecting to MongoDB at {mongo_uri}...")
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        db = client[db_name]
        print("Connected successfully.")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return

    # Migration mappings
    # db.json collections are structured differently (some as dicts keyed by ID)
    collections = {
        "products": "products",
        "leads": "leads",
        "orders": "orders",
        "chat_sessions": "chat_sessions"
    }

    for json_key, mongo_col in collections.items():
        source_data = data.get(json_key, {})
        
        # Source can be a dict keyed by ID or a list
        if isinstance(source_data, dict):
            documents = list(source_data.values())
        elif isinstance(source_data, list):
            documents = source_data
        else:
            documents = []

        if not documents:
            print(f"Collection '{mongo_col}' is empty in db.json. Skipping.")
            continue

        print(f"Migrating {len(documents)} documents into MongoDB '{mongo_col}' collection...")
        
        # Setup indexes first
        if mongo_col == "leads":
            db[mongo_col].create_index("session_id", unique=True)
        elif mongo_col == "orders":
            db[mongo_col].create_index("session_id")
            db[mongo_col].create_index("created_at")

        inserted_count = 0
        for doc in documents:
            if "_id" not in doc:
                continue
            # Use upsert to avoid duplicate key errors on repeated migration runs
            res = db[mongo_col].update_one(
                {"_id": doc["_id"]},
                {"$set": doc},
                upsert=True
            )
            inserted_count += 1
            
        print(f"Successfully migrated/upserted {inserted_count} documents into '{mongo_col}'.")

    print("\nMigration completed successfully! 🎉")

if __name__ == "__main__":
    main()
