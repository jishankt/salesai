import json
import os
import sys
import io
from typing import Dict, List, Any

# Ensure UTF-8 output on Windows terminals
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

def audit_catalog(products_path: str = "products.json"):
    if not os.path.exists(products_path):
        print(f"Error: {products_path} not found.")
        return

    with open(products_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    print(f"Loaded {len(products)} products from {products_path}.\n")

    # 1. Duplicates check by normalized product name
    name_map: Dict[str, List[Dict[str, Any]]] = {}
    for p in products:
        name_clean = p.get("name", "").strip().lower()
        name_map.setdefault(name_clean, []).append(p)

    duplicates = {k: v for k, v in name_map.items() if len(v) > 1}
    print(f"=== DUPLICATE PRODUCT GROUPS ({len(duplicates)}) ===")
    for name, items in list(duplicates.items())[:10]:
        print(f"  • '{name}':")
        for it in items:
            print(f"      - ID: {it.get('_id')} | Price: {it.get('price')} AED | Consumables: {len(it.get('consumables', []))} items | Stock: {it.get('stock')}")
    if len(duplicates) > 10:
        print(f"    ... and {len(duplicates) - 10} more duplicate groups.\n")

    # 2. Missing consumables on printers
    printers = [
        p for p in products 
        if p.get("category") in ("Printers", "Large Format Printer", "Business Printer", "Photo Printer") 
        or "printer" in p.get("name", "").lower()
    ]
    missing_cons = [p for p in printers if not p.get("consumables")]
    print(f"\n=== PRINTERS WITHOUT CONSUMABLES ({len(missing_cons)} / {len(printers)}) ===")
    for p in missing_cons[:10]:
        print(f"  • [{p.get('_id')}] {p.get('name')}")
    if len(missing_cons) > 10:
        print(f"    ... and {len(missing_cons) - 10} more printers.")

    print("\nAudit completed successfully.")

if __name__ == "__main__":
    audit_catalog()
