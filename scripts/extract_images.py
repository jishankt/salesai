import json
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import sys

def extract_image_for_product(prod):
    pid = prod.get("_id")
    web_url = prod.get("website_url")
    if not web_url or not web_url.startswith("http"):
        return pid, None
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        req = urllib.request.Request(web_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. Main WooCommerce Slider / Gallery Image
            main_slider_img = soup.find('img', class_='wcgs-slider-image-tag')
            if main_slider_img:
                src = main_slider_img.get('data-image') or main_slider_img.get('src')
                if src and src.startswith('http') and not src.endswith('logo-kepler-1x.png'):
                    return pid, src
                    
            # 2. Main featured wp-post-image
            post_img = soup.find('img', class_='wp-post-image')
            if post_img:
                src = post_img.get('data-image') or post_img.get('src')
                if src and src.startswith('http') and not src.endswith('logo-kepler-1x.png'):
                    return pid, src

            # 3. Product gallery images
            gallery_imgs = soup.select('.woocommerce-product-gallery__image img, .wcgs-carousel-image-tag')
            for gimg in gallery_imgs:
                src = gimg.get('data-image') or gimg.get('src')
                if src and src.startswith('http') and not src.endswith('logo-kepler-1x.png'):
                    return pid, src
                    
            # 4. OpenGraph og:image meta tag
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content') and og_img.get('content').startswith('http'):
                content_url = og_img.get('content')
                if not content_url.endswith('logo-kepler-1x.png'):
                    return pid, content_url
                    
    except Exception as e:
        return pid, None
        
    return pid, None

def main():
    print("Loading catalog...")
    with open('products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)
        
    total = len(products)
    print(f"Total products to extract images for: {total}")
    
    image_updates = {}
    success_count = 0
    fail_count = 0
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_pid = {executor.submit(extract_image_for_product, p): p.get("_id") for p in products}
        
        done = 0
        for future in as_completed(future_to_pid):
            pid = future_to_pid[future]
            done += 1
            try:
                prod_id, img_url = future.result()
                if img_url:
                    image_updates[prod_id] = img_url
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                
            if done % 50 == 0 or done == total:
                elapsed = time.time() - start_time
                print(f"[{done}/{total}] Found: {success_count} images | Elapsed: {elapsed:.1f}s")
                
    print(f"\nFinished extracting. Successfully found {len(image_updates)} specific images out of {total} products.")
    
    # Update products.json
    for p in products:
        pid = p.get("_id")
        if pid in image_updates:
            p["image_url"] = image_updates[pid]
            
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print("Saved updated products.json")
    
    # Update db.json
    try:
        with open('db.json', 'r', encoding='utf-8') as f:
            db = json.load(f)
            
        for p in products:
            pid = p.get("_id")
            if pid in db.get("products", {}) and pid in image_updates:
                db["products"][pid]["image_url"] = image_updates[pid]
                
        with open('db.json', 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        print("Saved updated db.json")
    except Exception as e:
        print(f"Failed to update db.json: {e}")

if __name__ == '__main__':
    main()
