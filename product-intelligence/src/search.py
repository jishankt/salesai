import re
import math
from typing import List, Dict, Any, Tuple, Optional
from src.models import ProductRecord, ProductSearchRequest, ProductMatchedItem, RelatedProductItem
from src.repository import ProductRepository

class HybridProductSearch:
    def __init__(self, repo: ProductRepository):
        self.repo = repo

    def parse_query_intent(self, query: str) -> Dict[str, Any]:
        q_l = query.lower()
        extracted = {
            "intent": "PRODUCT_SEARCH",
            "brand": None,
            "category": None,
            "specs": {},
            "terms": []
        }
        
        # Check brand
        for b in ["epson", "citizen", "innova", "korejet"]:
            if b in q_l:
                extracted["brand"] = b.capitalize()
                break
                
        # Check category
        if any(w in q_l for w in ["printer", "photo printer", "large format", "plotter"]):
            extracted["category"] = "Printer"
        elif "ink" in q_l or "cartridge" in q_l:
            extracted["category"] = "Ink Cartridge"
        elif "maintenance" in q_l or "tank" in q_l or "box" in q_l:
            extracted["category"] = "Maintenance Box"
        elif any(w in q_l for w in ["paper", "canvas", "luster", "matte", "glossy", "rag", "roll"]):
            extracted["category"] = "Print Media & Paper"

        # Check specs
        size_match = re.search(r'\b(a4|a3|a3\+|a2|17"|24"|44"|64"|17 inch|24 inch|44 inch)\b', q_l)
        if size_match:
            extracted["specs"]["size"] = size_match.group(1).upper()
            
        vol_match = re.search(r'\b(\d+)\s*(ml|l)\b', q_l)
        if vol_match:
            extracted["specs"]["volume"] = f"{vol_match.group(1)}{vol_match.group(2)}"
            
        # Clean terms
        stopwords = {"i", "need", "want", "looking", "for", "a", "an", "the", "do", "you", "have", "show", "me", "buy", "price", "of"}
        words = [re.sub(r'[^a-z0-9]', '', w) for w in q_l.split()]
        extracted["terms"] = [w for w in words if w and w not in stopwords]
        
        return extracted

    def search(self, req: ProductSearchRequest) -> Tuple[List[ProductMatchedItem], List[RelatedProductItem]]:
        products = self.repo.get_all_products()
        parsed = self.parse_query_intent(req.query)
        q_l = req.query.lower().strip()
        
        scored: List[Tuple[float, ProductRecord]] = []
        for p in products:
            score = 0.0
            p_name_l = p.name.lower()
            p_desc_l = (p.full_description or "").lower()
            p_sku_l = (p.sku or "").lower()
            p_cat_l = p.category.lower()

            # 1. Exact SKU / Model Match (High Priority)
            if p.sku and p_sku_l in q_l:
                score += 50.0
            if p.model and p.model.lower() in q_l:
                score += 40.0
                
            # 2. Direct Substring Match in Name
            if q_l in p_name_l:
                score += 30.0

            # 3. Keyword Term Matches
            matched_terms = 0
            for term in parsed["terms"]:
                if term in p_name_l:
                    score += 10.0
                    matched_terms += 1
                elif term in p_desc_l:
                    score += 4.0
                    matched_terms += 1
                elif term in p_sku_l:
                    score += 15.0
                    matched_terms += 1

            # 4. Category & Brand Alignment
            if parsed["brand"] and p.brand and parsed["brand"].lower() == p.brand.lower():
                score += 8.0
            if parsed["category"] and parsed["category"].lower() in p_cat_l:
                score += 12.0
            if "printer" in p_cat_l:
                score += 10.0  # Prefer whole printer machines over supplies when matching general model


            # 5. Specification Matching
            if "size" in parsed["specs"]:
                req_size = parsed["specs"]["size"].replace('"', '').replace(' INCH', '')
                if req_size.lower() in p_name_l or req_size.lower() in str(p.specifications).lower():
                    score += 15.0

            if score > 0:
                scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored[:req.limit]
        
        matched_items: List[ProductMatchedItem] = []
        related_items: List[RelatedProductItem] = []

        for score, prod in top_matches:
            # Generate smart grounded description
            smart_desc = self._generate_smart_description(prod)
            
            matched_items.append(ProductMatchedItem(
                id=prod.id,
                sku=prod.sku,
                name=prod.name,
                brand=prod.brand,
                category=prod.category,
                short_description=prod.short_description,
                specifications=prod.specifications,
                website_url=prod.website.product_url,
                image_url=prod.website.image_url,
                price=prod.pricing.amount,
                currency=prod.pricing.currency,
                stock_status=prod.availability.status,
                confidence=min(0.99, max(0.60, round(score / 50.0, 2))),
                smart_description=smart_desc
            ))

        # Retrieve verified relationships for the top product
        if top_matches:
            best_prod_id = top_matches[0][1].id
            db_rels = self.repo.get_relationships_for_product(best_prod_id)
            for r in db_rels[:4]:
                related_items.append(RelatedProductItem(
                    id=r["id"],
                    name=r["name"],
                    category=r["category"],
                    relationship_type=r["relationship_type"],
                    relationship_reason=r.get("relationship_reason"),
                    website_url=r["product_url"],
                    price=r.get("price", 0.0)
                ))

        return matched_items, related_items

    def _generate_smart_description(self, p: ProductRecord) -> str:
        """Ground description strictly on verified fields (no hallucinated claims)"""
        specs = p.specifications or {}
        parts = []
        if p.brand:
            parts.append(f"{p.brand}")
        parts.append(f"{p.name}")
        
        details = []
        if "capacity" in specs:
            details.append(f"Ink capacity: {specs['capacity']}")
        if "print_width" in specs:
            details.append(f"Max print width: {specs['print_width']}")
        if "weight_gsm" in specs:
            details.append(f"Weight: {specs['weight_gsm']}gsm")
        if "sheet_size" in specs:
            details.append(f"Format: {specs['sheet_size']}")
        if p.use_cases:
            details.append(f"Ideal for: {', '.join(p.use_cases[:2])}")
            
        desc_str = f"A high-performance {p.category.lower()}."
        if details:
            desc_str += " Highlights: " + "; ".join(details) + "."
        return desc_str
