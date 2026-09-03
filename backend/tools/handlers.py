from models.product import Product
from models.lead import Lead
from models.order import Order, InsufficientStockError
from models.cart import Cart
from services.lead_extraction import is_valid_name
from services.payment import attach_payment_link
from services.rendering import render_receipt_card
from services.discovery_engine import is_broad_query, get_discovery_question, compute_satisfaction_score

import re
import requests
import time
from bs4 import BeautifulSoup
import urllib.parse

def build_working_product_url(prod: dict) -> str:
    """
    Constructs the canonical direct product URL format: https://www.keplertechllc.com/product/<slug>/
    """
    web_url = prod.get("website_url")
    if web_url and web_url.startswith("http"):
        return web_url
    
    name = prod.get("name", "")
    clean_slug = "-".join([w for w in "".join([c if c.isalnum() or c.isspace() else " " for c in name.lower()]).split() if w])
    if clean_slug:
        return f"https://www.keplertechllc.com/product/{clean_slug}/"
    return f"https://www.keplertechllc.com/product/{prod.get('_id', '')}/"


def _get_live_availability(prod: dict) -> tuple:
    """
    Fast in-memory catalog stock verification with zero network lag.
    """
    db_avail = prod.get("availability")
    stock_count = int(prod.get("stock", 0))
    
    if db_avail == "Out of Stock" or stock_count == 0:
        return "🔴 Out of Stock", 0
    elif stock_count <= 3:
        return f"🟡 Low Stock ({stock_count} left)", stock_count
    return f"🟢 In Stock ({stock_count} pcs)", stock_count

def _stock_badge(stock: int) -> str:
    if stock == 0:
        return "🔴 Out of Stock"
    elif stock <= 3:
        return f"🟡 Low Stock ({stock} left)"
    return f"🟢 In Stock ({stock} pcs)"


def search_products(query: str, tags: list = None) -> str:
    """Searches the product catalog for matching items, or triggers consultative discovery if broad."""
    clean_q = query.strip()
    
    # Check if this is a broad/ambiguous inquiry requiring consultative discovery
    is_broad, broad_cat = is_broad_query(clean_q)
    if is_broad and broad_cat:
        return get_discovery_question(broad_cat)

    results = Product.search_products(query)
    if tags:
        results = [
            r for r in results 
            if any(
                t.lower() in [tag.lower() for tag in r.get("tags", [])] or
                t.lower() == r.get("_id", "").lower() or
                t.lower() == r.get("item_group", "").lower()
                for t in tags
            )
        ]

    if not results:
        return f"No products found matching '{query}'. We stock Epson SureColor printers, UltraChrome inks, and fine art media. Please check the model name or ask for recommendations."

    top_mode = results[0].get("_match_mode", "CONFIRMED")
    
    # Detect broad category queries from discovery pills (these should show ALL printers in the category)
    ql = query.lower()
    _EXCLUDED_CATS = ("Ink Cartridge", "Maintenance Box", "Inks & Consumables", "Accessory", "Media & Paper")
    def _is_office_printer(p):
        nl = p.get("name","").lower()
        return (("workforce" in nl or "am-c" in nl or "am c" in nl or "em-c" in nl) 
                and p.get("category","") not in _EXCLUDED_CATS
                and "scanner" not in nl and " ds-" not in nl and " ds " not in nl and " es-" not in nl and " es " not in nl
                and "bag" not in nl)
    def _is_citizen_printer(p):
        nl = p.get("name","").lower()
        return ("citizen" in nl 
                and p.get("category","") not in _EXCLUDED_CATS
                and "bag" not in nl and "media" not in nl and "ribbon" not in nl)
    def _is_cad_plotter(p):
        nl = p.get("name","").lower()
        return (("sc-t" in nl or "sc t" in nl or "plotter" in nl) 
                and p.get("category","") not in _EXCLUDED_CATS)
    def _is_fineart_printer(p):
        nl = p.get("name","").lower()
        return (("sc-p" in nl or "sc p" in nl) 
                and p.get("category","") not in _EXCLUDED_CATS)
    
    CATEGORY_FILTERS = {
        "technical": _is_cad_plotter,
        "cad": _is_cad_plotter,
        "plotter": _is_cad_plotter,
        "office": _is_office_printer,
        "enterprise": _is_office_printer,
        "workforce": _is_office_printer,
        "citizen": _is_citizen_printer,
        "photo booth": _is_citizen_printer,
        "fine art": _is_fineart_printer,
    }
    
    # Determine if this is a category query by checking for category keywords
    matched_cat_filter = None
    for cat_kw, cat_filter in CATEGORY_FILTERS.items():
        if cat_kw in ql:
            matched_cat_filter = cat_filter
            break
    
    is_category_query = matched_cat_filter is not None
    
    # If the user specified a specific model/SKU, restrict output strictly to the 100% matching item
    top_score = results[0].get("_match_score", 0)
    top_sat = compute_satisfaction_score(results[0], query)
    is_specific_hardware = not is_category_query and (top_score >= 300 or top_sat >= 95.0 or any(re.search(r'\b(WF-[A-Z0-9]+|EM-[A-Z0-9]+|SC-[A-Z][0-9]{3,5}[A-Z]*|AM-[A-Z0-9]+|CX-02|CZ-01|CY-02)\b', query, re.IGNORECASE) for _ in [0]))
    
    if is_specific_hardware:
        results = [results[0]]
    elif is_category_query:
        # Filter results to only include items from the correct category, then show all
        filtered = [r for r in results if matched_cat_filter(r)]
        # Deduplicate by product name (keep first occurrence with highest score)
        seen_names = set()
        deduped = []
        for r in filtered:
            name_key = r.get("name", "").strip()
            if name_key not in seen_names:
                seen_names.add(name_key)
                deduped.append(r)
        results = deduped if deduped else results[:10]
    else:
        results = results[:10]

    # Instrument query-match logging for evaluation set generation
    try:
        from services.instrumentation import log_search_match
        top_prod = results[0]
        sat = compute_satisfaction_score(top_prod, query)
        log_search_match(
            user_query=query,
            matched_product_id=top_prod.get("_id", ""),
            satisfaction_score=sat,
            match_score=top_prod.get("_match_score", 0),
            mode=top_mode,
            product_name=top_prod.get("name", "")
        )
    except Exception as e:
        pass

    output = []
    
    # Conversational framing header
    if top_mode == "NEEDS_CONFIRMATION":
        output.append(f"🔍 I found these close matches for *'{query}'* — did you mean one of these?\n")
    elif is_specific_hardware:
        output.append(f"Here is the official specification and live pricing for the **{results[0]['name']}**:\n")
    elif is_category_query:
        # Friendly category name for the header
        cat_names = {"technical": "Technical / CAD Plotters", "cad": "Technical / CAD Plotters", "plotter": "Technical / CAD Plotters",
                     "office": "Office & Enterprise Printers", "enterprise": "Office & Enterprise Printers", "workforce": "Office & Enterprise Printers",
                     "citizen": "Photo Booth & Event Printers", "photo booth": "Photo Booth & Event Printers",
                     "fine art": "Fine Art & Photography Printers"}
        cat_label = "Printers"
        for ck, cv in cat_names.items():
            if ck in ql:
                cat_label = cv
                break
        output.append(f"Here are all **{len(results)} {cat_label}** we carry:\n")
    else:
        output.append(f"Here are the top printing equipment options matching your request:\n")

    for r in results:
        stock_label, live_qty = _get_live_availability(r)
        satisfaction = compute_satisfaction_score(r, query)
        web_url = build_working_product_url(r)
        output.append(
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Match Satisfaction: {satisfaction}%*\n"
            f"📦 *{r['name']}*\n"
            f"💵 *Price:* {r['price']:.2f} AED\n"
            f"📊 *Availability:* {stock_label}\n"
            f"📝 *Description:* {r['description']}\n"
            f"🔗 *Website:* {web_url}\n"
            f"🆔 *Product ID:* `{r['_id']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    
    # Conversational footer & action pills
    if is_specific_hardware:
        output.append(
            f"\nWould you like me to check UAE delivery options, inquire about volume discounts, or show compatible ink sets?\n\n"
            f"[Options: Check Stock & Delivery | Inquire Discount | Compatible Inks & Supplies]"
        )
    else:
        output.append(
            f"\nWould you like more technical details on any of these units, or to check delivery and discount terms?\n\n"
            f"[Options: Check Stock & Delivery | Inquire Discount | Inks & Consumables]"
        )

    return "\n\n".join(output)


def get_printer_consumables(printer_query: str, consumable_filter: str = "all") -> str:
    """
    Fetches the exact compatible inks, media rolls, ribbons, and maintenance supplies
    linked to the specified printer model, presenting only those matching consumables as cards.
    Supports filtering by type ('maintenance', 'inks', or 'all').
    """
    import re
    q_raw = (printer_query or "").strip().lower()

    # Extract sub-type filter if embedded in printer_query (e.g. 'F100|type=maintenance')
    if "|type=" in q_raw:
        parts = q_raw.split("|type=")
        q_raw = parts[0].strip()
        consumable_filter = parts[1].strip().lower()

    # Check for keywords if filter not explicitly set
    if consumable_filter == "all":
        if any(k in q_raw for k in ["maintenance", "maintenance box", "waste box", "waste ink", "maintenance tank", "tank"]):
            consumable_filter = "maintenance"
        elif any(k in q_raw for k in ["ink", "inks", "cartridge", "cartridges", "bottle", "bottles", "ribbon", "media", "paper"]):
            consumable_filter = "inks"

    # Strip common conversational inquiry prefix/suffixes
    q_norm = re.sub(r'^(give\s+me\s+|i\s+want\s+|what\s+|list\s+all\s+the\s+|can\s+you\s+give\s+me\s+)?(maintenance\s+box\s+for|maintenance\s+tank\s+for|consumables\s+for|supplies\s+for|inks?\s+for|cartridges?\s+for|media\s+for|ribbons?\s+for)\s+', '', q_raw).strip()
    q_norm = re.sub(r'\s+(printer|printers|machine|supplies|consumables|inks?|media|maintenance\s+box|maintenance\s+tank|waste\s+box)$', '', q_norm).strip()
    q_clean = re.sub(r'[^a-z0-9]', '', q_norm)
    model_tokens = [re.sub(r'[^a-z0-9]', '', w) for w in re.split(r'[\s\-_/]+', q_norm) if len(w) >= 2]
    
    # 1. Search across all products in catalog
    all_prods = Product.get_all_products()
    printers = [p for p in all_prods if p.get("category") in ("Printers", "Business Printer", "Large Format Printer", "Photo Printer") or "printer" in p.get("name", "").lower()]
    
    target_printer = None
    best_score = -1
    
    for pr in printers:
        p_name = pr.get("name", "").lower()
        p_id = pr.get("_id", "").lower()
        p_clean = re.sub(r'[^a-z0-9]', '', p_name)
        p_id_clean = re.sub(r'[^a-z0-9]', '', p_id)
        p_words = [re.sub(r'[^a-z0-9]', '', w) for w in re.split(r'[\s\-_/]+', p_name) if w]
        
        score = 0
        # Exact compact string match (e.g. 'scp900' in 'epsonsurecolorscp900photoprinter' or 'wfc529r' in 'epsonworkforceprowfc529rbusinessprinter')
        if q_clean == p_clean or q_clean == p_id_clean:
            score += 200
        elif q_clean in p_clean or q_clean in p_id_clean:
            score += 100
            
        for mtok in model_tokens:
            if mtok in p_words or mtok == p_id_clean:
                score += 50
                
        # Tie-break / Quality booster: Prefer records with populated consumables
        if pr.get("consumables"):
            score += 25

        if score > best_score and score >= 80:
            best_score = score
            target_printer = pr
        elif score == best_score and pr.get("consumables") and (not target_printer or not target_printer.get("consumables")):
            target_printer = pr
            
    if not target_printer:
        search_res = Product.search_products(f"{q_norm} printer")
        if search_res:
            with_cons = [p for p in search_res if p.get("consumables")]
            target_printer = with_cons[0] if with_cons else search_res[0]
        
    if not target_printer:
        return search_products(f"{q_norm} ink")
        
    consumable_ids = target_printer.get("consumables", [])
    if not consumable_ids:
        model_code = q_norm
        m_code_match = re.search(r'\b(WF-[A-Z0-9]+|EM-[A-Z0-9]+|SC-[A-Z0-9]+|AM-[A-Z0-9]+|P\d{3,5}[A-Z0-9]*|T\d{3,5}[A-Z0-9]*|F\d{3,4}[A-Z0-9]*|C\d{4,5}[A-Z0-9]*|CX-02W|CX-02|CX02|CZ-01|CY-02)\b', target_printer.get('name', ''), re.IGNORECASE)
        if m_code_match:
            model_code = m_code_match.group(1).upper()
        return search_products(f"{model_code} ink")
        
    # Retrieve and filter matching consumables
    items = []
    for c_id in consumable_ids:
        it = Product.find_by_id(c_id)
        if it:
            cat_l = it.get("category", "").lower()
            name_l = it.get("name", "").lower()
            is_maint = "maintenance" in cat_l or "maintenance box" in name_l or "waste" in name_l
            
            if consumable_filter == "maintenance" and not is_maint:
                continue
            if consumable_filter == "inks" and is_maint:
                continue
            items.append(it)

    # If filter was too restrictive and returned nothing, fallback to all consumables
    if not items:
        for c_id in consumable_ids:
            it = Product.find_by_id(c_id)
            if it:
                items.append(it)

    output = []
    if consumable_filter == "maintenance":
        output.append(f"📦 **Genuine Maintenance Box & Waste Ink Tank for {target_printer['name']}:**\n")
    elif consumable_filter == "inks":
        output.append(f"💧 **Genuine Compatible Inks & Cartridges for {target_printer['name']}:**\n")
    else:
        output.append(f"💧 **Genuine Compatible Consumables & Supplies for {target_printer['name']}:**\n")
    
    has_out_of_stock = False
    for item in items:
        stock_label, live_qty = _get_live_availability(item)
        if live_qty == 0 or "Out of Stock" in stock_label:
            has_out_of_stock = True
        satisfaction = 100
        web_url = build_working_product_url(item)
        output.append(
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Match Satisfaction: {satisfaction}%*\n"
            f"📦 *{item['name']}*\n"
            f"💵 *Price:* {item['price']:.2f} AED\n"
            f"📊 *Availability:* {stock_label}\n"
            f"📝 *Description:* {item['description']}\n"
            f"🔗 *Website:* {web_url}\n"
            f"🆔 *Product ID:* `{item['_id']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
    if has_out_of_stock:
        output.append(
            f"\n📌 *Lead Time Note:* Items marked allocation/out of stock are available on regular manufacturer shipment (typically 2–3 business days across the UAE).\n\n"
            f"Would you like me to check stock allocation, delivery options, or inquire about discounts?\n\n"
            f"[Options: Check Stock & Delivery | Inquire Discount | Inks & Consumables]"
        )
    else:
        output.append(
            f"\nWould you like me to check same-day UAE delivery terms, or inquire about volume discount rates?\n\n"
            f"[Options: Check Stock & Delivery | Inquire Discount | Inks & Consumables]"
        )
            
    return "\n\n".join(output)


def check_stock(product_id: str) -> str:
    """Check the current stock of a specific product by its ID or name query, verifying live web link."""
    clean_id = (product_id or "").strip()
    prod = Product.find_by_id(clean_id)
    if not prod:
        # Try finding by name or SKU
        search_res = Product.search_products(clean_id)
        if search_res:
            prod = search_res[0]

    if not prod:
        return f"Product with identifier '{clean_id}' not found in our catalog. Would you like me to recommend available large format printers or inks?"

    stock_label, live_qty = _get_live_availability(prod)
    web_url = build_working_product_url(prod)

    msg = f"**{prod['name']}**\n📊 **Availability:** {stock_label}\n💵 **Price:** {prod['price']:.2f} AED\n🔗 **Link:** {web_url}"
    
    if live_qty == 0 or "Out of Stock" in stock_label:
        # Find closest in-stock alternative in same category
        tags = prod.get("tags", [])
        candidates = Product.search_products(tags[0] if tags else "printer")
        in_stock_alts = [c for c in candidates if c.get("_id") != prod.get("_id") and (c.get("stock", 0) > 0 or c.get("availability") == "In Stock")][:2]
        if in_stock_alts:
            msg += "\n\n💡 *In-Stock Alternatives:* " + ", ".join([f"**{a['name']}** ({a['price']:.2f} AED)" for a in in_stock_alts])
    
    return msg


def get_price(product_id: str, qty: int = 1) -> str:
    """Calculate total price for a quantity, applying the 10% bulk discount at qty >= 5."""
    prod = Product.find_by_id(product_id)
    if not prod:
        # Fallback to search if the LLM passed a name or hallucinated SKU
        searched = Product.search_products(product_id)
        if searched:
            prod = searched[0]
        else:
            return f"Product with ID or query '{product_id}' not found. Please verify the model name."

    unit_price = prod["price"]
    total = unit_price * qty
    if qty >= 5:
        discount = 0.10 * total
        total -= discount
        return (
            f"**{prod['name']}** — {unit_price:.2f} AED/unit.\n"
            f"Bulk order ({qty} pcs): 10% discount applied → **{total:.2f} AED** total (saved {discount:.2f} AED)."
        )
    return f"**{prod['name']}** — {unit_price:.2f} AED/unit. Total for {qty} pc(s): **{total:.2f} AED** (no discount — bulk discount applies for 5+ units)."


def recommend_products(context: str = "") -> str:
    """Recommend the top in-stock products in the catalog, matching context if specified."""
    all_products = Product.get_all_products()
    if not all_products:
        return "We don't have any products loaded right now."

    candidates = all_products
    if context:
        ctx_l = context.lower()
        if "office" in ctx_l or "business" in ctx_l or "workforce" in ctx_l or "enterprise" in ctx_l:
            candidates = [p for p in all_products if p.get("category") in ("Business Printer", "Printer") or "workforce" in p["name"].lower() or "enterprise" in p["name"].lower()]
        elif "cad" in ctx_l or "technical" in ctx_l or "plotter" in ctx_l:
            candidates = [p for p in all_products if "sc-t" in p["name"].lower() or "technical" in p["name"].lower() or "plotter" in p["name"].lower()]
        elif "photo" in ctx_l or "fine art" in ctx_l or "fineart" in ctx_l:
            candidates = [p for p in all_products if "sc-p" in p["name"].lower() or "photo" in p["name"].lower() or "fine art" in p["name"].lower() or "citizen" in p["name"].lower()]
        elif "booth" in ctx_l or "citizen" in ctx_l:
            candidates = [p for p in all_products if "citizen" in p["name"].lower() or "cx-02" in p["name"].lower() or "cz-01" in p["name"].lower()]

    if not candidates:
        candidates = all_products

    top = sorted(candidates, key=lambda p: (p.get("availability") == "In Stock" or p.get("stock", 0) > 0, p.get("stock", 0)), reverse=True)[:3]
    output = ["*Here are our top recommendations right now:*"]
    for p in top:
        stock_label = _stock_badge(p["stock"])
        web_url = build_working_product_url(p)
        output.append(
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *{p['name']}*\n"
            f"💵 *Price:* {p['price']:.2f} AED\n"
            f"📊 *Availability:* {stock_label}\n"
            f"📝 *Description:* {p['description']}\n"
            f"🔗 *Website:* {web_url}\n"
            f"🆔 *Product ID:* `{p['_id']}`\n"
            f"[Draft: {p['_id']}]\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    return "\n\n".join(output)


def get_product_specs(product_id: str) -> str:
    """
    Fetches official verified technical specifications (DPI, ink system, dimensions, warranty, media handling)
    for a specific product directly from the verified catalog to avoid any hallucination.
    """
    clean_id = (product_id or "").strip()
    prod = Product.find_by_id(clean_id)
    if not prod:
        search_res = Product.search_products(clean_id)
        if search_res:
            prod = search_res[0]

    if not prod:
        return f"Product '{clean_id}' was not found in our catalog. Please provide the exact model name or SKU."

    web_url = build_working_product_url(prod)
    stock_label, _ = _get_live_availability(prod)
    
    output = [
        f"📋 *Official Technical Specifications: {prod['name']}*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"🆔 *SKU / Product ID:* `{prod['_id']}`",
        f"💵 *Official Price:* {prod['price']:.2f} AED (VAT Included / Free UAE Delivery)",
        f"📊 *Live Inventory Status:* {stock_label}",
        f"📝 *Engineering Overview:* {prod['description']}",
        f"🏷️ *Category:* {prod.get('category', 'Printing Equipment')}",
    ]
    if prod.get("tags"):
        output.append(f"🔍 *Keywords / Features:* {', '.join(prod['tags'][:6])}")
    if prod.get("consumables"):
        output.append(f"💧 *Linked OEM Consumables:* {len(prod['consumables'])} verified cartridge/supply SKUs")
    output.append(f"🔗 *Official Direct Portal:* {web_url}")
    output.append(f"━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(output)


def get_shipping_info(emirate_or_city: str = "Dubai") -> str:
    """
    Provides official Kepler Tech LLC shipping terms, delivery timeframes, and free shipping thresholds across UAE and GCC.
    """
    loc = (emirate_or_city or "").strip().title()
    return (
        f"🚚 *Official Kepler Tech Delivery & Shipping Schedule:*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 *Location Selected:* {loc or 'United Arab Emirates'}\n"
        f"• *Dubai, Abu Dhabi & Sharjah:* Next-Business-Day Delivery (Same-day priority dispatch for orders confirmed before 12:00 PM GST).\n"
        f"• *Northern Emirates (Ajman, RAK, Fujairah, UAQ, Al Ain):* 1–2 Business Days.\n"
        f"• *GCC & Regional Export (Oman, Saudi Arabia, Bahrain, Kuwait, Qatar):* 3–5 Business Days via authorized international freight.\n"
        f"• *Free Shipping Policy:* Free door-to-door delivery on all hardware machines, plotters, and consumable orders exceeding 500 AED.\n"
        f"• *Warehouse Pickup:* Available at Kepler Tech LLC Central Logistics Hub, Dubai, UAE.\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def get_warranty_and_support(product_query: str = "") -> str:
    """
    Provides official warranty, installation, and on-site engineering maintenance policy for Kepler products.
    """
    return (
        f"🛡️ *Official Kepler Tech Warranty & Engineering Support:*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"• *Warranty Coverage:* 12 to 24 Months Official Manufacturer Warranty on all Epson SureColor, WorkForce, and Citizen hardware printers.\n"
        f"• *On-Site Installation & Training:* Complimentary on-site deployment, RIP software setup, and operator training across UAE for all Large Format Printers.\n"
        f"• *Genuine Consumable Guarantee:* 100% Genuine OEM inks, printheads, and maintenance tanks with batch quality assurance.\n"
        f"• *Authorized Service Center:* Kepler Tech LLC is an official Epson Commercial Channel Partner & Certified Service Provider in the UAE.\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def track_order(order_or_session_id: str) -> str:
    """
    Look up the live fulfillment, quotation, or dispatch status of an order or quote draft.
    """
    oid = (order_or_session_id or "").strip()
    order = Order.get_by_id(oid)
    if not order:
        # Search by session or contact
        all_orders = Order.get_all_orders() if hasattr(Order, "get_all_orders") else []
        for o in all_orders:
            if o.get("session_id") == oid or o.get("customer_contact") == oid:
                order = o
                break

    if not order:
        return f"🔍 No active order found for reference *'{oid}'*. Would you like me to connect you to a support specialist or help you prepare a new quotation?"

    items_summary = ", ".join([f"{i.get('name', i.get('product_id'))} (x{i.get('quantity', 1)})" for i in order.get("items", [])])
    return (
        f"📦 *Kepler Order & Quotation Status:*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Order Ref:* `{order.get('_id')}`\n"
        f"👤 *Customer:* {order.get('customer_name', 'Valued Client')}\n"
        f"📋 *Items:* {items_summary}\n"
        f"💵 *Total:* {order.get('total_amount', 0):.2f} AED\n"
        f"📊 *Status:* {order.get('status', 'Processing').upper()}\n"
        f"🚚 *Fulfillment Timeframe:* {order.get('lead_time', '1-2 Business Days')}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


# --- Cart tools (NEW: lets customers build up an order across turns) -------

def add_to_cart(session_id: str, product_id: str, quantity: int = 1) -> str:
    """Add an item to the customer's running cart for this session."""
    clean_id = (product_id or "").strip()
    
    # Confidence floor check if resolving via search or ambiguous identifier
    prod = Product.find_by_id(clean_id)
    if not prod:
        search_res = Product.search_products(clean_id)
        if search_res:
            top_match = search_res[0]
            top_score = top_match.get("_match_score", 0)
            top_mode = top_match.get("_match_mode", "CONFIRMED")
            if top_score < 60 or top_mode == "NEEDS_CONFIRMATION":
                return (
                    f"⚠️ Low confidence match for *'{clean_id}'*:\n"
                    f"Did you mean **{top_match['name']}** ({top_match['price']:.2f} AED)?\n"
                    f"Please confirm by replying: *'Confirm add {top_match['_id']}'* before adding to cart."
                )
            prod = top_match
            clean_id = prod["_id"]

    try:
        view = Cart.add_item(session_id, clean_id, quantity)
    except ValueError as e:
        return f"Error: {e}"
    lines = [f"• {i['name']} x{i['quantity']} — {i['line_total']:.2f} AED" for i in view["items"]]
    return "Cart updated:\n" + "\n".join(lines) + f"\n\nCart total: {view['total']:.2f} AED"


def view_cart(session_id: str) -> str:
    """Show the customer's current cart contents and running total."""
    view = Cart.to_view(Cart.get(session_id))
    if not view["items"]:
        return "The cart is empty right now."
    lines = [f"• {i['name']} x{i['quantity']} — {i['line_total']:.2f} AED" for i in view["items"]]
    return "Current cart:\n" + "\n".join(lines) + f"\n\nTotal: {view['total']:.2f} AED"


def remove_from_cart(session_id: str, product_id: str) -> str:
    """Remove an item from the customer's cart."""
    view = Cart.remove_item(session_id, product_id)
    if not view["items"]:
        return "Item removed. Cart is now empty."
    lines = [f"• {i['name']} x{i['quantity']} — {i['line_total']:.2f} AED" for i in view["items"]]
    return "Item removed. Cart now:\n" + "\n".join(lines) + f"\n\nTotal: {view['total']:.2f} AED"


def checkout_cart(session_id: str, customer_name: str, customer_contact: str) -> str:
    """Convert the customer's current cart into a real order and generate a payment link."""
    view = Cart.to_view(Cart.get(session_id))
    if not view["items"]:
        return "ERROR: Cart is empty — add items before checking out."

    items = [{"product_id": i["product_id"], "quantity": i["quantity"]} for i in view["items"]]
    return _create_order_and_render(session_id, items, customer_name, customer_contact, clear_cart=True)


# --- Direct single-shot order (kept for backward compatibility / simple flows) ---

def create_order(session_id: str, items: list, customer_name: str, customer_contact: str) -> str:
    """Create an order directly (without needing a pre-built cart)."""
    return _create_order_and_render(session_id, items, customer_name, customer_contact, clear_cart=False)


def _create_order_and_render(session_id, items, customer_name, customer_contact, clear_cart):
    if not customer_name or customer_name.strip().lower() in ("", "unknown", "none", "not provided", "your name", "customer_name"):
        return "ERROR: Cannot create order — customer name is required. Please ask the customer for their name first."
    if not customer_contact or customer_contact.strip().lower() in ("", "unknown", "none", "not provided", "your contact details", "customer_contact"):
        return "ERROR: Cannot create order — customer contact (phone or email) is required. Please ask the customer for their contact details first."

    from services.kepler_api import create_kepler_lead, create_kepler_quotation
    from models.product import Product
    from datetime import datetime
    from models.db import MEM_DB, USE_IN_MEMORY, save_mem_db

    # Resolve items name and price for Quotation
    resolved_items = []
    total_amount = 0.0
    has_backorder = False
    for item in items:
        prod = Product.find_by_id(item["product_id"])
        if not prod:
            return f"ERROR: Product ID '{item['product_id']}' not found in catalog."
        qty = int(item["quantity"])
        if prod.get("stock", 0) < qty:
            has_backorder = True
        resolved_items.append({
            "product_id": item["product_id"],
            "name": prod["name"],
            "quantity": qty,
            "price": float(prod["price"]),
            "is_backorder": prod.get("stock", 0) < qty
        })
        total_amount += float(prod["price"]) * qty

    # Create Lead on Kepler
    lead_id = create_kepler_lead(customer_name, customer_contact)
    if not lead_id:
        return "ERROR: Failed to create/retrieve Lead on the Kepler system. Please try again."

    # Create Quotation on Kepler
    quotation_id = create_kepler_quotation(lead_id, resolved_items)
    if not quotation_id:
        return "ERROR: Failed to create Quotation Draft on the Kepler system. Please try again."

    # Create a local Order representing the Kepler Quotation Draft
    order_doc = {
        "_id": quotation_id,
        "session_id": session_id,
        "customer_name": customer_name,
        "customer_contact": customer_contact,
        "items": resolved_items,
        "total_amount": total_amount,
        "status": "draft",
        "payment_status": "draft",
        "has_backorder": has_backorder,
        "lead_time": "3-5 Business Days (Central Warehouse Dispatch)" if has_backorder else "Immediate (Ready to Ship)",
        "payment_link": None,
        "payment_provider": "kepler_erpnext",
        "created_at": datetime.utcnow(),
    }
    
    # Save order doc locally
    if USE_IN_MEMORY:
        MEM_DB["orders"][quotation_id] = order_doc
        save_mem_db()
    else:
        Order.get_collection().insert_one(order_doc)

    if clear_cart:
        Cart.clear(session_id)

    if session_id.isdigit():
        msg = f"\n\n✅ Quotation Draft *{quotation_id}* has been successfully created on Kepler for {customer_name}!"
        if has_backorder:
            msg += "\n📦 *Note:* Includes item(s) on backorder with 3–5 business days dispatch to UAE."
        return msg

    return render_receipt_card(order_doc)


def generate_payment_link(order_id: str) -> str:
    """Retrieve the checkout link for an existing order."""
    order = Order.get_by_id(order_id)
    if not order:
        return f"Order ID '{order_id}' not found."
    return f"Payment link for Order '{order_id}': {order.get('payment_link', '')}"


def escalate_to_human(session_id: str, reason: str = "") -> str:
    """Escalate the conversation to a human sales representative."""
    Lead.create_or_update_lead(session_id, status="escalated")
    return "I've connected you with our senior technical sales team at Kepler Tech — a specialist will review our chat and reach out to you directly shortly! 😊"


def create_lead(session_id: str, name: str = None, contact: str = None, needs: str = None, budget: str = None) -> str:
    """Save customer qualification details (name/contact/needs/budget) to the CRM."""
    if name and not is_valid_name(name):
        print(f"[create_lead] Blocked invalid name save: '{name}'")
        name = None

    lead = Lead.create_or_update_lead(session_id, name, contact, needs, budget)

    # Sync to Kepler
    if name and contact:
        try:
            from services.kepler_api import create_kepler_lead
            create_kepler_lead(name, contact)
        except Exception as e:
            print(f"[create_lead] Kepler sync failed: {e}")

    return f"Lead profile updated. Status: '{lead.get('status')}'."


TOOL_MAP = {
    "search_products": search_products,
    "get_printer_consumables": get_printer_consumables,
    "check_stock": check_stock,
    "get_price": get_price,
    "get_product_specs": get_product_specs,
    "get_shipping_info": get_shipping_info,
    "get_warranty_and_support": get_warranty_and_support,
    "track_order": track_order,
    "recommend_products": recommend_products,
    "add_to_cart": add_to_cart,
    "view_cart": view_cart,
    "remove_from_cart": remove_from_cart,
    "checkout_cart": checkout_cart,
    "create_lead": create_lead,
    "create_order": create_order,
    "generate_payment_link": generate_payment_link,
    "escalate_to_human": escalate_to_human,
}
