import csv
import json
import os
import re
from src.models import ProductRecord, ProductPricing, ProductAvailability, ProductWebsite, ProductSource, ProductRelationship
from src.repository import ProductRepository
from src.normalizer import normalize_product_name, extract_brand, extract_category, extract_specifications, sanitize_url

BASE_URL = "https://www.keplertechllc.com"

def slugify(text: str) -> str:
    s = text.lower().replace("'", "").replace('"', "")
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s

def build_canonical_url(name: str, sku: str) -> str:
    slug = slugify(name)
    return f"{BASE_URL}/product/{slug}/"

def ingest_from_csv_and_json(repo: ProductRepository, csv_path: str = None, json_path: str = None):
    products = []
    
    # 1. Read from products.json if available for richer prices/descriptions
    json_lookup = {}
    if json_path and os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                raw_json = json.load(f)
                for item in raw_json:
                    key = item.get("_id") or item.get("name")
                    json_lookup[key.lower()] = item
        except Exception as e:
            print(f"Error reading {json_path}: {e}")

    # 2. Read from CSV / Sheet data
    if csv_path and os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 3:
                    continue
                row_id, sku, raw_name = row[0].strip(), row[1].strip(), row[2].strip()
                if row_id.lower() == "id" or not raw_name:
                    continue
                
                name = normalize_product_name(raw_name)
                brand = extract_brand(name)
                category = extract_category(name)
                specs = extract_specifications(name)
                
                # Check price & description from JSON lookup
                price = 0.0
                desc = f"{name} available at Kepler Tech LLC."
                image_url = ""
                stock = 10
                
                matched_json = json_lookup.get(row_id.lower()) or json_lookup.get(sku.lower()) or json_lookup.get(name.lower())
                if matched_json:
                    price = float(matched_json.get("price", 0.0))
                    desc = matched_json.get("description", desc)
                    image_url = matched_json.get("image_url", "")
                    stock = int(matched_json.get("stock", 10))
                    if matched_json.get("tags"):
                        specs["tags"] = matched_json.get("tags")

                # Construct canonical verified link
                product_url = build_canonical_url(name, sku)
                
                # Generate Use Cases based on category
                use_cases = []
                if "Photo" in category or "Fine Art" in name or "Canvas" in name:
                    use_cases.extend(["Studio Photography", "Fine Art Printing", "Gallery Exhibitions"])
                elif "Large Format" in category or "Plotter" in name or "Technical" in name:
                    use_cases.extend(["CAD & Technical Drawings", "Architectural Blueprints", "Commercial Signage"])
                elif "Multifunction" in category:
                    use_cases.extend(["Corporate Office", "High-Volume Document Printing"])

                prod = ProductRecord(
                    id=f"prod_{row_id}",
                    sku=sku if sku else None,
                    name=name,
                    brand=brand,
                    category=category,
                    short_description=desc[:200],
                    full_description=desc,
                    specifications=specs,
                    tags=specs.get("tags", [brand, category]),
                    use_cases=use_cases,
                    pricing=ProductPricing(amount=price, currency="AED"),
                    availability=ProductAvailability(status="in_stock" if stock > 0 else "out_of_stock", stock_count=stock),
                    website=ProductWebsite(product_url=product_url, image_url=image_url),
                    source=ProductSource(sheet_row_id=row_id, source_type="sheet"),
                    status="active"
                )
                repo.upsert_product(prod)
                products.append(prod)

    print(f"Successfully ingested and normalized {len(products)} products into canonical repository.")
    
    # 3. Build Deterministic Relationships
    build_catalog_relationships(repo, products)

def build_catalog_relationships(repo: ProductRepository, products):
    """Build links between Printers, Inks, Maintenance boxes, and Media"""
    for p in products:
        p_name = p.name.lower()
        p_id = p.id
        
        # SC-P900 Relationships
        if "sc-p900" in p_name or "sc p900" in p_name:
            for related in products:
                r_name = related.name.lower()
                # UltraChrome Pro 10 Inks
                if "t46s" in r_name or "ultrachrome pro10" in r_name or "pro 10 ink" in r_name:
                    repo.add_relationship(ProductRelationship(
                        id=f"rel_{p_id}_{related.id}",
                        product_id=p_id,
                        related_product_id=related.id,
                        relationship_type="COMPATIBLE",
                        relationship_score=0.98,
                        relationship_reason="Official UltraChrome Pro10 Ink for SC-P900"
                    ))
                # Maintenance Tank SC-P700/SC-P900
                elif "c12c935711" in r_name or "maintenance tank - sc-p700/sc-p900" in r_name:
                    repo.add_relationship(ProductRelationship(
                        id=f"rel_{p_id}_{related.id}",
                        product_id=p_id,
                        related_product_id=related.id,
                        relationship_type="ACCESSORY",
                        relationship_score=1.0,
                        relationship_reason="Genuine Replacement Maintenance Tank"
                    ))
                # SC-P700 as alternative
                elif "sc-p700" in r_name and "printer" in r_name:
                    repo.add_relationship(ProductRelationship(
                        id=f"rel_{p_id}_{related.id}",
                        product_id=p_id,
                        related_product_id=related.id,
                        relationship_type="ALTERNATIVE",
                        relationship_score=0.90,
                        relationship_reason="13-inch compact photo printer alternative"
                    ))

        # SC-T3200 / SC-T5200 / SC-T7200 Relationships
        if any(t in p_name for t in ["sc-t3200", "sc-t5200", "sc-t7200"]):
            for related in products:
                r_name = related.name.lower()
                if "ultrachrome xd" in r_name and "t69" in r_name:
                    repo.add_relationship(ProductRelationship(
                        id=f"rel_{p_id}_{related.id}",
                        product_id=p_id,
                        related_product_id=related.id,
                        relationship_type="COMPATIBLE",
                        relationship_score=0.98,
                        relationship_reason="UltraChrome XD Ink for SureColor T-Series"
                    ))
                elif "c13t619300" in r_name or "maintenance box - c13t619300" in r_name:
                    repo.add_relationship(ProductRelationship(
                        id=f"rel_{p_id}_{related.id}",
                        product_id=p_id,
                        related_product_id=related.id,
                        relationship_type="ACCESSORY",
                        relationship_score=1.0,
                        relationship_reason="Compatible Maintenance Box"
                    ))
