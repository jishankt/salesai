import re
import urllib.parse
from typing import Optional, Dict, Any, List

def sanitize_url(url: str) -> str:
    """Strip tracking params (?srsltid=..., utm_*, etc.) and enforce https://www.keplertechllc.com"""
    if not url:
        return "https://www.keplertechllc.com"
    
    parsed = urllib.parse.urlparse(url.strip())
    # Keep only clean path
    clean_url = f"https://www.keplertechllc.com{parsed.path.rstrip('/')}"
    if not clean_url.endswith('/') and '.' not in parsed.path.split('/')[-1]:
        clean_url += '/'
    return clean_url

def normalize_product_name(raw_name: str) -> str:
    name = raw_name.strip()
    name = re.sub(r'\s+', ' ', name)
    # Standardize SureColor naming
    name = re.sub(r'SureColor\s+SC\s+([A-Za-z0-9-]+)', r'SureColor SC-\1', name, flags=re.I)
    name = re.sub(r'WorkForce\s+WF\s+([A-Za-z0-9-]+)', r'WorkForce \1', name, flags=re.I)
    return name

def extract_brand(name: str) -> str:
    name_l = name.lower()
    if "epson" in name_l:
        return "Epson"
    elif "citizen" in name_l:
        return "Citizen"
    elif "innova" in name_l:
        return "Innova"
    elif "korejet" in name_l:
        return "Korejet"
    elif "aircast" in name_l:
        return "AirCastPro"
    return "Epson"

def extract_category(name: str) -> str:
    name_l = name.lower()
    if "printer" in name_l or "plotter" in name_l:
        if "photo printer" in name_l or "p900" in name_l or "p700" in name_l or "sc-p" in name_l:
            return "Photo Printer"
        elif "large format" in name_l or "technical" in name_l or "sc-t" in name_l:
            return "Large Format Printer"
        elif "multifunction" in name_l or "multi function" in name_l or "mfp" in name_l:
            return "Multifunction Enterprise Printer"
        return "Printer"
    elif "scanner" in name_l:
        return "Scanner"
    elif "ink" in name_l or "cartridge" in name_l or "singlepack" in name_l:
        return "Ink Cartridge"
    elif "maintenance box" in name_l or "maintenance tank" in name_l or "maintenance cartridge" in name_l:
        return "Maintenance Box"
    elif "paper" in name_l or "canvas" in name_l or "film" in name_l or "rag" in name_l or "media" in name_l or "roll" in name_l:
        return "Print Media & Paper"
    elif "blade" in name_l or "stick" in name_l or "pen" in name_l or "bag" in name_l:
        return "Accessory"
    elif "software" in name_l or "server" in name_l:
        return "Software & Server"
    return "Supplies"

def extract_specifications(name: str, desc: str = "") -> Dict[str, Any]:
    specs = {}
    combined = f"{name} {desc}"
    
    # Capacity / Volume
    vol_match = re.search(r'(\d+)\s*(ml|l|liter|liters)\b', combined, re.I)
    if vol_match:
        specs["capacity"] = f"{vol_match.group(1)}{vol_match.group(2).lower()}"
        
    # Width / Dimensions (inches / mm)
    size_inch_match = re.search(r'(\d{2,3})[\'"]+|(\d{1,2})[\'"]+\s*(?:large|photo|wireless|printer|paper|canvas|film|roll)', combined, re.I)
    if size_inch_match:
        val = size_inch_match.group(1) or size_inch_match.group(2)
        specs["print_width"] = f"{val} inch"
        
    # Paper weight (GSM)
    gsm_match = re.search(r'(\d{3})\s*gsm\b', combined, re.I)
    if gsm_match:
        specs["weight_gsm"] = int(gsm_match.group(1))
        
    # Sheet size (A4, A3, A3+, A2, 4x6, 6x8, 8x12)
    sheet_match = re.search(r'\b(A4|A3\+|A3|A2|DIN A4|DIN A3|DIN A2|4x6|6x8|8x12)\b', combined, re.I)
    if sheet_match:
        specs["sheet_size"] = sheet_match.group(1).upper()
        
    # Roll length
    roll_match = re.search(r'x\s*(\d+(\.\d+)?)\s*(m|meter|feet|\')\b', combined, re.I)
    if roll_match:
        specs["roll_length"] = f"{roll_match.group(1)}{roll_match.group(3)}"
        
    # Colors
    colors = []
    color_candidates = [
        "Photo Black", "Matte Black", "Cyan", "Magenta", "Yellow", 
        "Light Cyan", "Light Magenta", "Vivid Magenta", "Vivid Light Magenta",
        "Gray", "Light Gray", "Dark Gray", "Light Black", "Light Light Black",
        "Orange", "Green", "Violet", "Red"
    ]
    for c in color_candidates:
        if re.search(r'\b' + re.escape(c) + r'\b', combined, re.I):
            colors.append(c)
    if colors:
        specs["colors"] = colors
        
    return specs
