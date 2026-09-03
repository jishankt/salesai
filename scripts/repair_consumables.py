import json

with open('products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# 1. Fix Citizen CX-02 & CX-02W consumables to use existing DB IDs: CX2.4x6 and CX2.6X8
for p in products:
    pid = p.get('_id')
    if pid in ('CX-02', 'CX-02W'):
        p['consumables'] = ['CX2.4x6', 'CX2.6X8']
    elif pid in ('Citizen CX-02 Bag', 'CZ01 Carry Bag'):
        p['category'] = 'Accessory'
        p['consumables'] = []

# 2. Add missing CZ01-MEDIA-4X6 to catalog
cz01_media = next((p for p in products if p['_id'] == 'CZ01-MEDIA-4X6'), None)
if not cz01_media:
    products.append({
        '_id': 'CZ01-MEDIA-4X6',
        'sku': 'CZ01-MEDIA-4X6',
        'row_id': 'CZ01-4X6',
        'name': 'Citizen CZ-01 4x6 inch Dye-Sub Photo Media Set',
        'price': 450.0,
        'stock': 10,
        'availability': 'In Stock',
        'description': 'Genuine OEM Citizen CZ-01 4x6 inch Dye-Sublimation Photo Paper and Ribbon Set (2 rolls, 300 prints).',
        'tags': ['Citizen', 'CZ-01', 'Media', 'Paper', 'Dye-Sub', 'Photo'],
        'image_url': 'https://www.keplertechllc.com/wp-content/uploads/2023/05/citizen-consumables.webp',
        'website_url': 'https://www.keplertechllc.com/product/citizen-cz01-photo-printer/',
        'category': 'Media & Paper',
        'consumables': []
    })

# 3. Add missing WF-C5290 / WF-C5790 color ink SKUs (C13T946240, C13T946340, C13T946440)
wf_c5290_colors = [
    ('C13T946240', 'Cyan', 'https://www.keplertechllc.com/wp-content/uploads/2018/04/Ink-300x300.jpg'),
    ('C13T946340', 'Magenta', 'https://www.keplertechllc.com/wp-content/uploads/2018/04/Ink-300x300.jpg'),
    ('C13T946440', 'Yellow', 'https://www.keplertechllc.com/wp-content/uploads/2018/04/Ink-300x300.jpg')
]
for cid, color, img in wf_c5290_colors:
    if not any(p['_id'] == cid for p in products):
        products.append({
            '_id': cid,
            'sku': cid,
            'row_id': cid.replace('C13', ''),
            'name': f'{cid} Epson WF-C5290/WF-C5790 Series XXL {color} Ink Cartridge',
            'price': 380.0,
            'stock': 10,
            'availability': 'In Stock',
            'description': f'Genuine OEM {cid} Epson WorkForce Pro WF-C5290 / WF-C5790 XXL {color} Ink Cartridge (5,000 pages).',
            'tags': ['Epson', 'WorkForce', 'WF-C5290', 'WF-C5790', color, 'Ink'],
            'image_url': img,
            'website_url': f'https://www.keplertechllc.com/product/{cid.lower()}/',
            'category': 'Ink Cartridge',
            'consumables': []
        })

with open('products.json', 'w', encoding='utf-8') as f:
    json.dump(products, f, indent=2, ensure_ascii=False)

with open('db.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

for p in products:
    pid = p['_id']
    db['products'][pid] = p

with open('db.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=2, ensure_ascii=False)

print('Successfully repaired Citizen & WF-C5290 consumable entries in database!')
