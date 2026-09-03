"""
Input normalization for SalesAI.
Cleans spelling errors, phonetic transcription artifacts, and unwanted whitespace.
"""
import re

# Common typos and transcribed speech artifacts for printing hardware & supplies
TYPO_CORRECTIONS = {
    r"\bepsn\b": "epson",
    r"\beposn\b": "epson",
    r"\bsurecolr\b": "surecolor",
    r"\bsurcolor\b": "surecolor",
    r"\bctzn\b": "citizen",
    r"\bcitizn\b": "citizen",
    r"\bprntr\b": "printer",
    r"\bprntrs\b": "printers",
    r"\bplottr\b": "plotter",
    r"\bcanvs\b": "canvas",
    r"\binva\b": "innova",
    r"\bkorjet\b": "korejet",
    r"\bshajar\b": "sharjah",
    r"\bdubia\b": "dubai",
    r"\babudabi\b": "abu dhabi",
    r"\bryadh\b": "riyadh",
    r"\bsupplay\b": "supply",
    r"\bcosumables?\b": "consumables",
    r"\bcosumeables?\b": "consumables",
    r"\bcosumabls?\b": "consumables",
    r"\bconsumabl\b": "consumable",
    r"\bconsumabls\b": "consumables",
    r"\bmainatance\b": "maintenance",
    r"\bmaintanance\b": "maintenance",
    r"\bmaintenence\b": "maintenance",
    r"\bmaintance\b": "maintenance",
    r"\bmaintanence\b": "maintenance",
    r"\bmaintenace\b": "maintenance",
    r"\bhallo\b": "hello",
    r"\byou ink\b": "your ink",
    r"\bi trying to\b": "i want to",
    r"\btrying to buy\b": "want to buy",
    r"\blooking to buy\b": "want to buy",
    r"\bwanna buy\b": "want to buy",
    r"\bwanr\b": "want to",
    r"\bwanr\s+buy\b": "want to buy",
    r"\bprinetr\b": "printer",
    r"\bprinetrs\b": "printers",
    r"\bprnter\b": "printer",
    r"\bprnters\b": "printers",
    r"\blookin\b": "looking",
    r"\bbyu\b": "buy",
    r"\binkss?\b": "inks",
}

# Known UAE / Middle East territories
KNOWN_TERRITORIES = [
    "dubai", "abu dhabi", "sharjah", "ajman", "ras al khaimah", 
    "fujairah", "umm al quwain", "al ain", "riyadh", "jeddah", "dammam", "saudi", "uae", "oman", "qatar", "india"
]

def normalize_user_input(text: str) -> str:
    """Cleans typos, whitespace, and phonetic transcription artifacts."""
    if not text:
        return ""
    cleaned = text.strip()
    for pattern, replacement in TYPO_CORRECTIONS.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned
