import json
import urllib.request
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import re
import sys

def scrape_printer_page_consumables(printer):
    pid = printer.get("_id")
    web_url = printer.get("website_url")
    if not web_url or not web_url.startswith("http"):
        return pid, []
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    consumable_links = []
    try:
        req = urllib.request.Request(web_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all links on the page pointing to /product/
            for a in soup.find_all('a'):
                href = a.get('href', '')
                if '/product/' in href and href != web_url:
                    text = a.text.strip()
                    # Check if SKU or cartridge code is present
                    sku_match = re.search(r'\b(C1[123][A-Z0-9]{7,8}|C13S[0-9]{6}|C12C[0-9]{6}|C13T[A-Z0-9]{6}|CY-[A-Z0-9]+|CZ[0-9]+-[A-Z0-9\-]+|CX[0-9]+-[A-Z0-9\-]+|T[0-9]{3}[A-Z0-9]+)\b', text + ' ' + href, re.IGNORECASE)
                    if sku_match:
                        consumable_links.append((sku_match.group(1).upper(), href, text))
    except Exception as e:
        return pid, []
        
    return pid, consumable_links

def main():
    with open('products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)
        
    product_ids = {p.get('_id', '').upper(): p for p in products}
    # Also index by SKU
    sku_map = {p.get('sku', '').upper(): p for p in products if p.get('sku')}
    # Also index by row_id
    row_map = {p.get('row_id', '').upper(): p for p in products if p.get('row_id')}
    
    printers = [p for p in products if p.get('category') in ('Printers', 'Business Printer', 'Large Format Printer', 'Photo Printer') or 'printer' in p.get('name', '').lower()]
    print(f"Total printer models to verify/enrich: {len(printers)}")
    
    printer_consumable_map = {}
    
    with ThreadPoolExecutor(max_workers=16) as executor:
        future_to_pid = {executor.submit(scrape_printer_page_consumables, pr): pr.get("_id") for pr in printers}
        
        for future in as_completed(future_to_pid):
            pid = future_to_pid[future]
            try:
                prod_id, links = future.result()
                if links:
                    valid_cons_ids = []
                    for code, href, text in links:
                        # Match to valid product ID in our database
                        matched_id = None
                        if code in product_ids:
                            matched_id = code
                        elif code in sku_map:
                            matched_id = sku_map[code]['_id']
                        else:
                            # Try finding by slug in href
                            slug = href.rstrip('/').split('/')[-1].lower()
                            for p in products:
                                p_slug = p.get('website_url', '').rstrip('/').split('/')[-1].lower()
                                if p_slug and p_slug == slug:
                                    matched_id = p['_id']
                                    break
                                    
                        if matched_id and matched_id not in valid_cons_ids and matched_id != prod_id:
                            # Verify matched product is indeed ink, consumable, paper, or maintenance box
                            target_p = product_ids.get(matched_id, {})
                            t_name = target_p.get('name', '').lower()
                            if 'ink' in t_name or 'cartridge' in t_name or 'maintenance' in t_name or 'box' in t_name or 'media' in t_name or 'ribbon' in t_name or 'roll' in t_name or 'paper' in t_name or 't49' in t_name or 't02' in t_name or 't08' in t_name or 't50' in t_name:
                                valid_cons_ids.append(matched_id)
                                
                    if valid_cons_ids:
                        printer_consumable_map[prod_id] = valid_cons_ids
            except Exception as e:
                pass
                
    print(f"\nScraped genuine live consumables for {len(printer_consumable_map)} printers!")
    
    # Enrich printer records
    updated_count = 0
    for p in products:
        pid = p.get('_id')
        if pid in printer_consumable_map:
            p['consumables'] = printer_consumable_map[pid]
            updated_count += 1
            
    print(f"Updated {updated_count} printer records in catalog.")
    
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
        
    with open('db.json', 'r', encoding='utf-8') as f:
        db = json.load(f)
        
    for p in products:
        pid = p['_id']
        if pid in db.get('products', {}):
            db['products'][pid]['consumables'] = p.get('consumables', [])
            
    with open('db.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
        
    print("Successfully synchronized all printer consumables into products.json and db.json!")

if __name__ == '__main__':
    main()
