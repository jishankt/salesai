"""
Consultative Needs Discovery & Multi-Factor Satisfaction Scoring Engine.
Intercepts broad/ambiguous requests (e.g. "I want ink", "need a printer", "paper")
and engages the customer with consultative qualification questions before matching
products with a 60%-100% satisfaction score.
"""
import re
from typing import Tuple, Optional, Dict, Any, List

BROAD_CATEGORY_PATTERNS = {
    "ink": [
        r"^(?:no\s+)?(?:do\s+you\s+have\s+|i\s+need\s+|i\s+want\s+|show\s+me\s+|give\s+me\s+|wanna\s+)?(?:some\s+)?(?:inks?|cartridges?|bottles?|toners?)\s*\??$",
    ],
    "printer": [
        r"(?:new\s+printing\s+shop|new\s+shop|printing\s+business|new\s+business|event\s+setup|my\s+business)",
        r"(?:recommend|need|want|looking\s+for|trying\s+to\s+buy|buy|purchase|get|show\s+me|check).*(?:new\s+|large\s+format\s+)?(?:printers?|plotters?|machines?)",
        r"^(?:printers?|plotters?|machines?)$"
    ],
    "paper": [
        r"^(?:no\s+)?(?:do\s+you\s+have\s+|i\s+need\s+|i\s+want\s+|show\s+me\s+|give\s+me\s+|wanna\s+)?(?:some\s+)?(?:papers?|canvas|canvas\s+rolls?|rolls?|media)\s*\??$",
    ],
    "scanner": [
        r"^(?:no\s+)?(?:do\s+you\s+have\s+|i\s+need\s+|i\s+want\s+|show\s+me\s+|give\s+me\s+|wanna\s+)?(?:some\s+)?(?:scanners?)\s*\??$",
    ]
}

SPECIFIC_EXCLUSIONS = [
    # If the user mentioned a specific model name/code or specific ink color, it's NOT a broad query
    r"\b(?:sc-p\d+[a-z0-9]*|sc-t\d+[a-z0-9]*|sc-f\d+[a-z0-9]*|p\d{3,5}[a-z0-9]*|t\d{3,5}[a-z0-9]*|f\d{3,4}[a-z0-9]*|cx-02[a-z0-9]*|cz-01|cy-02|wf-[a-z0-9]+|am-[a-z0-9]+|em-[a-z0-9]+|c13t\d+|t800\d+|photo\s+black|matte\s+black|cyan|magenta|yellow|700ml|350ml|110ml|1\.6l)\b"
]

CATEGORY_DISCOVERY_PROMPTS = {
    "ink": (
        "Sure! We carry the complete range of genuine Epson UltraChrome and WorkForce inks. 🖨️\n\n"
        "What printer model do you have? Which color(s) or cartridge size are you looking for?\n\n"
        "[Options: SureColor SC-P Inks | WorkForce Pro Inks | EcoTank / Dye-Sub]"
    ),
    "printer": (
        "Welcome to Kepler Tech! 🖨️ We distribute Epson Large Format & Citizen Photo Printers across the UAE.\n\n"
        "Which printing category best fits your requirement?\n\n"
        "• 📐 **Technical & CAD/GIS** (Epson SC-T series — 24\" to 44\" for architectural drawings)\n"
        "• 🏢 **Office & Enterprise** (Epson WorkForce A4/A3 high-speed business MFPs)\n"
        "• 📸 **Photo Booth & Events** (Citizen compact dye-sub photo printers)\n"
        "• 🎨 **Fine Art & Photography** (Epson SC-P series — 12-color 99% Pantone)\n\n"
        "[Options: Technical / CAD | Office & Enterprise | Photo Booth | Fine Art & Photo]"
    ),
    "paper": (
        "We stock genuine Innova fine art papers and Korejet canvas rolls! 🎨\n\n"
        "What media type are you looking for?\n"
        "[Options: Artistic Canvas Rolls | Fine Art Smooth Paper | Photo Gloss / Luster]"
    ),
    "scanner": (
        "We carry high-speed Epson business and flatbed scanners. 📄\n\n"
        "What document size do you need to scan?\n"
        "[Options: A4 Business Scanner | A3 Large Format Flatbed | High-Speed Document Scanner]"
    )
}

def is_broad_query(query: str) -> Tuple[bool, Optional[str]]:
    """Checks if a user query is a broad/unspecified category request."""
    if not query:
        return False, None
    q = query.strip().lower()
    
    # If specific model or SKU is present, do not intercept as broad
    for excl in SPECIFIC_EXCLUSIONS:
        if re.search(excl, q):
            return False, None

    # Strip greeting prefix if attached to the sentence
    q_norm = re.sub(r'^(?:hi|hello|hey|greetings|good\s+morning|good\s+afternoon|good\s+evening)[,\s!\-]+', '', q).strip()

    for cat, patterns in BROAD_CATEGORY_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, q_norm):
                return True, cat
    return False, None

def get_discovery_question(category: str) -> str:
    """Returns the consultative qualification question for a broad category."""
    return CATEGORY_DISCOVERY_PROMPTS.get(category, "Could you specify the model or specifications you are looking for?")

def compute_satisfaction_score(product: Dict[str, Any], query: str, budget: Optional[float] = None) -> float:
    """
    Computes a multi-factor satisfaction match score from 60.0% to 100.0%.
    Factors:
    - Exact SKU / Model match: 100.0%
    - Title / SKU match: 40%
    - Description / Specs match: 30%
    - Budget compliance: 20%
    - Stock readiness: 10%
    """
    q_clean = re.sub(r'[^a-z0-9]', '', (query or "").lower())
    name_clean = re.sub(r'[^a-z0-9]', '', product.get("name", "").lower())
    sku_clean = re.sub(r'[^a-z0-9]', '', product.get("sku", product.get("_id", "")).lower())

    # Direct exact model match (e.g. 'c11ch87401by', 'wfc20750', 'c13t02s100')
    if (sku_clean and sku_clean in q_clean) or (q_clean and q_clean in sku_clean and len(q_clean) >= 4):
        return 100.0
    if product.get("_match_score", 0) >= 300:
        return 100.0

    score = 60.0
    q_words = [w.lower() for w in query.split() if len(w) > 2]
    name_l = product.get("name", "").lower()
    desc_l = product.get("description", "").lower()
    sku_l = product.get("sku", product.get("_id", "")).lower()

    # Exact term matches
    matching_words = sum(1 for w in q_words if w in name_l or w in sku_l)
    if matching_words > 0:
        score += min(25.0, (matching_words / max(len(q_words), 1)) * 25.0)

    # Spec matches in description
    desc_matches = sum(1 for w in q_words if w in desc_l)
    if desc_matches > 0:
        score += min(10.0, (desc_matches / max(len(q_words), 1)) * 10.0)

    # Stock bonus
    if int(product.get("stock", 0)) > 0:
        score += 5.0

    # Budget fit
    price = float(product.get("price", 0.0))
    if budget and budget > 0:
        if price <= budget:
            score += 10.0
        elif price <= budget * 1.2:
            score += 5.0
    else:
        score += 5.0

    return min(100.0, round(score, 1))
