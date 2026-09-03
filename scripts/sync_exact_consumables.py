import requests
from bs4 import BeautifulSoup
import json
import time

with open('products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

sku_by_slug = {}
for p in products:
    url = p.get('website_url', '').strip()
    if '/product/' in url:
        slug = url.split('/product/')[1].strip('/')
        if slug:
            sku_by_slug[slug] = p['_id']

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

updated_count = 0
for idx, p in enumerate(products):
    if p.get('category') != 'Printers':
        p['consumables'] = []
        continue
        
    url = p.get('website_url')
    if not url or not url.startswith('http'):
        continue
        
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            continue
            
        soup = BeautifulSoup(r.text, 'html.parser')
        
        tab_content = soup.find(id='tab-accessories') or soup.find(id=lambda x: x and 'consumable' in x.lower())
        
        matched_skus = []
        
        if tab_content:
            links = tab_content.find_all('a', href=True)
            for a in links:
                href = a['href'].strip()
                if '/product/' in href and href.rstrip('/') != url.rstrip('/'):
                    slug = href.split('/product/')[1].strip('/')
                    matched_id = sku_by_slug.get(slug)
                    if matched_id and matched_id != p['_id']:
                        matched_skus.append(matched_id)
        
        # Deduplicate
        p['consumables'] = list(dict.fromkeys(matched_skus))
        clean_id = p['_id'].encode('ascii', 'ignore').decode('ascii')
        print(f"[{idx+1}/801] {clean_id} -> {len(p['consumables'])} exact website consumables: {p['consumables']}")
        updated_count += 1
        time.sleep(0.15)
    except Exception as e:
        print(f"Error scraping {p.get('_id')}: {e}")

with open('products.json', 'w', encoding='utf-8') as f:
    json.dump(products, f, indent=2)

print(f"Finished scraping. Total printers updated: {updated_count}")
