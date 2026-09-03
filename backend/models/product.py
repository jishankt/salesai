import uuid
import re
from datetime import datetime

from models.db import MEM_DB, USE_IN_MEMORY, get_collection, save_mem_db

STOPWORDS = {
    "what", "wat", "is", "the", "of", "do", "you", "have", "any", "price", "cost",
    "in", "stock", "need", "want", "buy", "to", "for", "a", "an", "please", "check",
    "about", "availability", "availablity", "details", "how", "much", "find", "get",
    "are", "there", "can", "could", "would", "tell", "me", "show", "search", "lookup", "some",
    "order", "i", "like", "purchase", "give", "place", "want", "also", "just", "one",
    "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "wanna", "wan", "gonna", "gon", "need", "get",
}


def _stem(word: str) -> str:
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("es") and not word.endswith("press"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and word != "canvas":
        return word[:-1]
    return word


import json
import os

_MATCHER_BOOSTS_CONFIG = None

def _get_matcher_boosts_config():
    global _MATCHER_BOOSTS_CONFIG
    if _MATCHER_BOOSTS_CONFIG is not None:
        return _MATCHER_BOOSTS_CONFIG
    # Check default config path in backend/matcher_boosts.json or local root
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "matcher_boosts.json"),
        os.path.join(os.path.dirname(__file__), "matcher_boosts.json"),
        os.path.join(os.path.abspath(os.getcwd()), "backend", "matcher_boosts.json")
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    _MATCHER_BOOSTS_CONFIG = json.load(f)
                    return _MATCHER_BOOSTS_CONFIG
            except Exception as e:
                pass
    _MATCHER_BOOSTS_CONFIG = {"intents": {}, "boost_rules": {}}
    return _MATCHER_BOOSTS_CONFIG

class Product:
    @classmethod
    def get_collection(cls):
        return get_collection("products")

    @classmethod
    def insert_product(cls, name, price, stock, description, tags=None, product_id=None, image_url=None, website_url=None):
        pid = product_id or str(uuid.uuid4())
        clean_slug = "-".join([w for w in "".join([c if c.isalnum() or c.isspace() else " " for c in name.lower()]).split() if w])
        default_url = f"https://www.keplertechllc.com/product/{clean_slug}/"
        doc = {
            "_id": pid,
            "name": name,
            "price": float(price),
            "stock": int(stock),
            "description": description,
            "tags": tags or [],
            "image_url": image_url or "",
            "website_url": website_url or default_url,
            "created_at": datetime.utcnow(),
        }
        if USE_IN_MEMORY:
            MEM_DB["products"][pid] = doc
            save_mem_db()
        else:
            cls.get_collection().insert_one(doc)
        return doc

    @classmethod
    def find_by_id(cls, product_id):
        if not product_id:
            return None
        pid_clean = str(product_id).strip()
        if USE_IN_MEMORY:
            p = MEM_DB["products"].get(pid_clean)
            if not p:
                # Case-insensitive / SKU / partial search fallback
                pid_l = pid_clean.lower()
                for item in MEM_DB["products"].values():
                    if item.get("_id", "").lower() == pid_l or item.get("sku", "").lower() == pid_l or pid_l in item.get("name", "").lower():
                        p = item
                        break
        else:
            p = cls.get_collection().find_one({"_id": pid_clean})
            if not p:
                p = cls.get_collection().find_one({"$or": [{"_id": {"$regex": f"^{pid_clean}$", "$options": "i"}}, {"sku": pid_clean}, {"name": {"$regex": pid_clean, "$options": "i"}}]})
        if p and not p.get("website_url"):
            clean_slug = "-".join([w for w in "".join([c if c.isalnum() or c.isspace() else " " for c in p.get("name", "").lower()]).split() if w])
            p["website_url"] = f"https://www.keplertechllc.com/product/{clean_slug}/"
        return p

    @classmethod
    def search_products(cls, query_str):
        raw_words = [w.lower().strip("?,.!\";:") for w in query_str.split()]
        words = []
        for w in raw_words:
            if not w:
                continue
            stemmed = _stem(w)
            if (len(stemmed) > 2 and stemmed not in STOPWORDS) or stemmed in ("xd", "ink"):
                words.append(stemmed)

        generic_search = False
        generic_words = {"product", "products", "item", "items", "catalog", "stock", "have", "we", "list", "show"}
        if not words or all(w in generic_words for w in words):
            generic_search = True

        if USE_IN_MEMORY:
            if generic_search:
                return list(MEM_DB["products"].values())
            scored_results = []
            clean_query = query_str.strip().lower()
            
            # Load boost configuration tables
            cfg = _get_matcher_boosts_config()
            intents = cfg.get("intents", {})
            boost_rules = cfg.get("boost_rules", {})

            consumable_kws = intents.get("consumable_query_keywords", ["ink", "cartridge", "consumable", "ribbon", "media", "roll", "waste box", "maintenance box", "cleaning", "tank"])
            printer_kws = intents.get("printer_intent_keywords", ["printer", "plotter", "machine", "device", "c400", "c550", "p900", "p700", "p9500", "t5700", "t3100", "cx-02", "cz-01"])
            office_kws = intents.get("office_keywords", ["office", "workforce", "business", "enterprise", "document", "a4", "a3", "dwf", "multifunction", "copier", "scanner", "scan", "copy"])
            photo_kws = intents.get("photo_keywords", ["photo", "studio", "event", "passport", "booth", "citizen", "lab"])
            fineart_kws = intents.get("fineart_keywords", ["fine art", "art", "gallery", "canvas", "museum", "photography", "p9500", "p7500", "p900", "p700", "p20000", "p20500", "p5300", "p8500", "p6500"])
            cad_kws = intents.get("cad_keywords", ["cad", "gis", "blueprint", "technical", "engineering", "architect", "sc-t", "t3200", "t5200", "t7200", "t3100", "t5100", "t7700", "t5700", "t5400", "t3700"])
            hw_disc_kws = intents.get("hardware_discovery_keywords", ["loking", "looking", "want", "need", "printer", "plotter", "machine", "category", "fine art", "technical", "cad", "office"])

            is_consumable_query = any(k in clean_query for k in consumable_kws)
            is_printer_intent = any(k in clean_query for k in printer_kws) and not is_consumable_query
            is_office_query = any(k in clean_query for k in office_kws)
            is_photo_query = any(k in clean_query for k in photo_kws)
            is_fineart_query = any(k in clean_query for k in fineart_kws)
            is_cad_query = any(k in clean_query for k in cad_kws)
            is_hardware_discovery = any(k in clean_query for k in hw_disc_kws) and not any(k in clean_query for k in ["ink", "cartridge", "consumable", "ribbon"])
            
            for p in MEM_DB["products"].values():
                name_l = p["name"].lower()
                desc_l = p["description"].lower()
                tags_l = [t.lower() for t in p.get("tags", [])]
                pid_l = p["_id"].lower()
                sku_l = p.get("sku", "").lower()
                cat = p.get("category", "")
                
                # If user specifically asked for ink/consumables, exclude hardware machines from ranking top
                if is_consumable_query and cat == "Printers" and not any(k in clean_query for k in ["printer", "machine", "device", "model"]):
                    continue

                # Exact SKU / Product ID / full name match
                if clean_query == pid_l or clean_query == sku_l or clean_query == name_l:
                    if is_printer_intent and cat in ("Ink Cartridge", "Maintenance Box", "Inks & Consumables"):
                        pass # Let the actual printer unit take priority
                    else:
                        p_copy = dict(p)
                        p_copy["_match_score"] = 100
                        p_copy["_match_mode"] = "CONFIRMED"
                        scored_results.append((100, p_copy))
                        continue

                if clean_query in name_l:
                    if is_printer_intent and cat in ("Ink Cartridge", "Maintenance Box", "Inks & Consumables"):
                        pass # Don't boost maintenance boxes with printer name in their title
                    else:
                        p_copy = dict(p)
                        p_copy["_match_score"] = 90
                        p_copy["_match_mode"] = "CONFIRMED"
                        scored_results.append((90, p_copy))
                        continue
                
                score = 0
                for w in words:
                    if w in name_l:
                        score += 30
                    elif w in pid_l or w in sku_l:
                        score += 35
                    elif any(w in t for t in tags_l):
                        score += 15
                    elif w in desc_l:
                        score += 10
                
                # Apply data-driven boost rules
                if is_hardware_discovery:
                    rule = boost_rules.get("hardware_discovery", {})
                    if cat in rule.get("match_categories", []) or any(k in name_l for k in rule.get("match_name_keywords", [])):
                        score += rule.get("boost", 80)
                    elif cat in rule.get("penalty_categories", []):
                        score -= rule.get("penalty", 50)

                if is_office_query:
                    rule = boost_rules.get("office", {})
                    if any(k in name_l for k in rule.get("match_name_keywords", [])):
                        score += rule.get("boost", 60)
                    elif any(k in name_l for k in rule.get("penalty_name_keywords", [])):
                        score -= rule.get("penalty", 40)

                if is_consumable_query:
                    rule = boost_rules.get("consumables", {})
                    if cat in rule.get("match_categories", []) or any(k in name_l for k in rule.get("match_name_keywords", [])):
                        score += rule.get("boost", 120)
                    elif cat in rule.get("penalty_categories", []):
                        score -= rule.get("penalty", 90)
                else:
                    # Penalize inks and maintenance boxes when user is searching for printers/hardware
                    if cat in ("Ink Cartridge", "Maintenance Box", "Inks & Consumables", "Accessory") or "maintenance box" in name_l:
                        score -= 80

                    if is_photo_query:
                        rule = boost_rules.get("photo", {})
                        if (cat in rule.get("match_categories", []) or "printer" in name_l) and any(k in name_l for k in rule.get("match_name_keywords", [])):
                            score += rule.get("boost", 70)
                        elif any(k in name_l for k in rule.get("penalty_name_keywords", [])):
                            score -= rule.get("penalty", 80)

                    if is_fineart_query:
                        rule = boost_rules.get("fineart", {})
                        if (cat in rule.get("match_categories", []) or "printer" in name_l) and any(k in name_l for k in rule.get("match_name_keywords", [])):
                            score += rule.get("boost", 80)
                        elif any(k in name_l for k in rule.get("penalty_name_keywords", [])):
                            score -= rule.get("penalty", 80)

                # Budget / Under <price> filtering
                under_match = re.search(r'\b(?:under|below|less than|max|budget|within)\s*(\d{2,6})\b', clean_query)
                if under_match:
                    max_budget = float(under_match.group(1))
                    if p.get("price", 0) > max_budget:
                        continue

                # In-stock readiness booster (only apply if the product matched keyword / category intent)
                if score > 0 and p.get("stock", 0) > 0:
                    score += 15

                if score > 0:
                    p_copy = dict(p)
                    p_copy["_match_score"] = score
                    p_copy["_match_mode"] = "CONFIRMED" if score >= 60 else "NEEDS_CONFIRMATION"
                    scored_results.append((score, p_copy))
            
            scored_results.sort(key=lambda x: x[0], reverse=True)
            return [p for score, p in scored_results]

        if generic_search:
            return list(cls.get_collection().find({}))
        or_conditions = []
        for w in words:
            regex_query = {"$regex": w, "$options": "i"}
            or_conditions.append({"name": regex_query})
            or_conditions.append({"description": regex_query})
            or_conditions.append({"tags": regex_query})
            or_conditions.append({"_id": regex_query})
        return list(cls.get_collection().find({"$or": or_conditions}))

    @classmethod
    def get_all_products(cls):
        if USE_IN_MEMORY:
            return [dict(p) for p in MEM_DB["products"].values()]
        return list(cls.get_collection().find({}))

    @classmethod
    def delete_all(cls):
        if USE_IN_MEMORY:
            MEM_DB["products"].clear()
            save_mem_db()
        else:
            cls.get_collection().delete_many({})

    @classmethod
    def update_stock(cls, product_id, quantity_change):
        if USE_IN_MEMORY:
            if product_id in MEM_DB["products"]:
                MEM_DB["products"][product_id]["stock"] += quantity_change
                save_mem_db()
            return
        cls.get_collection().update_one({"_id": product_id}, {"$inc": {"stock": quantity_change}})
