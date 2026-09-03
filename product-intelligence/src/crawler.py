import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import urllib.parse
from src.normalizer import sanitize_url, normalize_product_name, extract_specifications, extract_category, extract_brand

logger = logging.getLogger("kepler_crawler")

BASE_URL = "https://www.keplertechllc.com"

class KeplerCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 KeplerBot/1.0"
        })

    def crawl_product_page(self, url: str) -> Optional[Dict]:
        """Fetch and extract structured product details from Kepler Tech LLC product page"""
        clean_url = sanitize_url(url)
        try:
            resp = self.session.get(clean_url, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch {clean_url} (HTTP {resp.status_code})")
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extract product title
            title_node = soup.find("h1", class_=lambda x: x and ("product_title" in x or "entry-title" in x or "product-title" in x)) or soup.find("h1")
            if not title_node:
                return None
            name = normalize_product_name(title_node.get_text(strip=True))

            # Extract short/full description
            short_desc_node = soup.find(class_=lambda x: x and ("woocommerce-product-details__short-description" in x or "short-description" in x))
            short_desc = short_desc_node.get_text(strip=True) if short_desc_node else ""

            full_desc_node = soup.find(id="tab-description") or soup.find(class_=lambda x: x and "product-description" in x)
            full_desc = full_desc_node.get_text(separator="\n", strip=True) if full_desc_node else short_desc

            # Extract image
            img_node = soup.find("meta", property="og:image") or soup.find("img", class_=lambda x: x and ("wp-post-image" in x or "product-image" in x))
            image_url = ""
            if img_node:
                image_url = img_node.get("content") or img_node.get("src") or ""

            # Extract SKU
            sku_node = soup.find("span", class_="sku")
            sku = sku_node.get_text(strip=True) if sku_node else None

            # Extract Price
            price = 0.0
            price_node = soup.find("p", class_="price") or soup.find("span", class_="woocommerce-Price-amount")
            if price_node:
                import re
                p_text = price_node.get_text()
                price_match = re.search(r'[\d,]+(?:\.\d+)?', p_text)
                if price_match:
                    try:
                        price = float(price_match.group(0).replace(',', ''))
                    except ValueError:
                        price = 0.0

            specs = extract_specifications(name, f"{short_desc} {full_desc}")
            category = extract_category(name)
            brand = extract_brand(name)

            return {
                "name": name,
                "sku": sku,
                "brand": brand,
                "category": category,
                "short_description": short_desc,
                "full_description": full_desc,
                "specifications": specs,
                "price": price,
                "image_url": image_url,
                "product_url": clean_url,
                "source_type": "website"
            }
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return None

    def search_kepler_product_url(self, product_name: str, sku: Optional[str] = None) -> str:
        """Construct canonical Kepler Tech LLC direct product route or search path"""
        # Create slug-friendly path or standard fallback canonical link
        slug = product_name.lower().replace("'", "").replace('"', "")
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
        return f"{BASE_URL}/product/{slug}/"
