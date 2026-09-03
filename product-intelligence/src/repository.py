import json
import sqlite3
import os
from typing import List, Dict, Optional, Any
from src.models import ProductRecord, ProductRelationship

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "product_intelligence.db")

class ProductRepository:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    sku TEXT UNIQUE,
                    name TEXT NOT NULL,
                    brand TEXT,
                    model TEXT,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    product_type TEXT,
                    short_description TEXT,
                    full_description TEXT,
                    specifications TEXT,
                    tags TEXT,
                    use_cases TEXT,
                    price REAL DEFAULT 0.0,
                    currency TEXT DEFAULT 'AED',
                    stock INT DEFAULT 10,
                    product_url TEXT NOT NULL,
                    image_url TEXT,
                    brochure_url TEXT,
                    status TEXT DEFAULT 'active',
                    source_type TEXT DEFAULT 'sheet',
                    source_reference TEXT,
                    last_synced_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_relationships (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    related_product_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    relationship_score REAL DEFAULT 1.0,
                    relationship_reason TEXT,
                    created_at TEXT,
                    UNIQUE(product_id, related_product_id, relationship_type)
                )
            """)
            conn.commit()

    def upsert_product(self, product: ProductRecord):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (
                    id, sku, name, brand, model, category, subcategory, product_type,
                    short_description, full_description, specifications, tags, use_cases,
                    price, currency, stock, product_url, image_url, brochure_url,
                    status, source_type, source_reference, last_synced_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    sku=excluded.sku,
                    name=excluded.name,
                    brand=excluded.brand,
                    model=excluded.model,
                    category=excluded.category,
                    subcategory=excluded.subcategory,
                    product_type=excluded.product_type,
                    short_description=excluded.short_description,
                    full_description=excluded.full_description,
                    specifications=excluded.specifications,
                    tags=excluded.tags,
                    use_cases=excluded.use_cases,
                    price=excluded.price,
                    currency=excluded.currency,
                    stock=excluded.stock,
                    product_url=excluded.product_url,
                    image_url=excluded.image_url,
                    brochure_url=excluded.brochure_url,
                    status=excluded.status,
                    source_type=excluded.source_type,
                    last_synced_at=excluded.last_synced_at,
                    updated_at=excluded.updated_at
            """, (
                product.id,
                product.sku,
                product.name,
                product.brand,
                product.model,
                product.category,
                product.subcategory,
                product.product_type,
                product.short_description,
                product.full_description,
                json.dumps(product.specifications),
                json.dumps(product.tags),
                json.dumps(product.use_cases),
                product.pricing.amount,
                product.pricing.currency,
                product.availability.stock_count,
                product.website.product_url,
                product.website.image_url,
                product.website.brochure_url,
                product.status,
                product.source.source_type,
                product.source.sheet_row_id or product.source.website_url,
                product.source.last_synced_at,
                product.created_at,
                product.updated_at
            ))
            conn.commit()

    def get_product(self, product_id: str) -> Optional[ProductRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id = ? OR sku = ?", (product_id, product_id))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def get_all_products(self) -> List[ProductRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE status = 'active'")
            rows = cursor.fetchall()
            return [self._row_to_record(r) for r in rows]

    def add_relationship(self, rel: ProductRelationship):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO product_relationships (
                    id, product_id, related_product_id, relationship_type,
                    relationship_score, relationship_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                rel.id,
                rel.product_id,
                rel.related_product_id,
                rel.relationship_type,
                rel.relationship_score,
                rel.relationship_reason
            ))
            conn.commit()

    def get_relationships_for_product(self, product_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.relationship_type, r.relationship_reason, r.relationship_score,
                       p.id, p.name, p.category, p.product_url, p.price, p.image_url
                FROM product_relationships r
                JOIN products p ON r.related_product_id = p.id
                WHERE r.product_id = ?
                ORDER BY r.relationship_score DESC
            """, (product_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def _row_to_record(self, row) -> ProductRecord:
        specs = json.loads(row["specifications"]) if row["specifications"] else {}
        tags = json.loads(row["tags"]) if row["tags"] else []
        use_cases = json.loads(row["use_cases"]) if row["use_cases"] else []
        
        return ProductRecord(
            id=row["id"],
            sku=row["sku"],
            name=row["name"],
            brand=row["brand"],
            model=row["model"],
            category=row["category"],
            subcategory=row["subcategory"],
            product_type=row["product_type"],
            short_description=row["short_description"],
            full_description=row["full_description"],
            specifications=specs,
            tags=tags,
            use_cases=use_cases,
            pricing={"amount": row["price"], "currency": row["currency"]},
            availability={"status": "in_stock" if row["stock"] > 0 else "out_of_stock", "stock_count": row["stock"]},
            website={"product_url": row["product_url"], "image_url": row["image_url"], "brochure_url": row["brochure_url"]},
            source={"source_type": row["source_type"], "last_synced_at": row["last_synced_at"] or ""},
            status=row["status"],
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or ""
        )
