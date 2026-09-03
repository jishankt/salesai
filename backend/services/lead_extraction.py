"""
Deterministic lead-signal extraction.

We do NOT rely on the LLM to decide when to save contact/budget info — small
local models skip tool calls unpredictably. This scans every user message
with regex and writes directly to the DB as a safety net, independent of
whatever the LLM decides to do with the create_lead tool.
"""
import re

from models.lead import Lead
from models.chat_session import ChatSession

PHONE_REGEX = re.compile(r'(\+?\d[\d\-\s]{8,13}\d)')
BUDGET_REGEX = re.compile(
    r'(?:under|below|around|about|upto|up to)?\s*(\d{2,6})\s*(aed|rs\.?|₹|\$|dollars?|rupees?)?',
    re.IGNORECASE,
)
PRODUCT_INTENT_REGEX = re.compile(
    r'\b(do you have|is there|price|cost|how much|stock|available|any .* left|'
    r'recommend|suggestion|popular|best seller|what.*ink|what.*canvas|buy|order|want to order|i want|'
    r'details|datails|info|specs|send.*details|send.*datails)\b',
    re.IGNORECASE,
)
NAME_REGEX = re.compile(r"\b(?:my name is|i am|this is|call me|i'm)\s+([a-zA-Z]{2,15})\b", re.IGNORECASE)

NAME_STOPWORDS = {
    "unit", "units", "ink", "inks", "canvas", "canvases", "cartridge", "cartridges", "box", "boxes",
    "pack", "packs", "yellow", "black", "matte", "cyan", "magenta", "pcs", "pieces", "item", "items",
    "product", "products", "quantity", "quantities", "yes", "no", "ok", "okay", "sure", "confirmed",
    "please", "thanks", "thank you", "hello", "hi", "kepler", "agent", "epson", "korejet", "unknown", "none",
    "what", "why", "how", "who", "when", "where", "what you saying", "are you kidding", "kidding",
    "joke", "printer", "printers", "supplies", "not analyzed", "test"
}


def looks_like_product_question(text: str) -> bool:
    clean = text.lower().strip("?,. ()")
    words = clean.split()
    if not words:
        return False

    confirm_blacklist = {
        "proceed", "confirm", "yes", "ok", "okay", "sure", "correct", "place", "place order",
        "go ahead", "checkout", "nope", "cancel", "yep", "yeah", "order proceed",
        "inquire discount", "check stock & delivery", "check delivery & stock", "check stock",
        "check delivery", "draft quotation", "draft full set quote", "prepare quotation",
        "request bulk discount", "request volume discount"
    }
    if clean in confirm_blacklist or any(clean.startswith(cb) for cb in confirm_blacklist):
        return False
    if any(w in confirm_blacklist for w in words) and not any(k in words for k in ["sc-p9500", "sc-f100", "wf-c20750", "cx-02", "cz-01"]):
        return False

    product_keywords = [
        "p9500", "p7500", "p9000", "p20000", "p8000", "p6000", "p5000", "t3200", "t5200", "t7200",
        "cx-02", "cx02", "cz-01", "cz01", "cy-02", "surecolor", "ultrachrome", "epson", "citizen",
        "ink", "inks", "cartridge", "cartridges", "photo black", "matte black", "cyan", "magenta",
        "yellow", "canvas", "paper", "roll", "rolls", "printer", "printers", "plotter", "plotters",
        "scanner", "scanners", "700ml", "350ml", "220ml", "110ml"
    ]
    if any(k in clean for k in product_keywords):
        return True

    return bool(PRODUCT_INTENT_REGEX.search(text))


def is_valid_name(name: str) -> bool:
    if not name:
        return False
    name_clean = name.strip().lower()
    if len(name_clean) < 3:
        return False
    if any(char.isdigit() for char in name_clean):
        return False
    if name_clean in NAME_STOPWORDS:
        return False
    words = name_clean.split()
    if any(w in ["what", "why", "how", "who", "when", "where", "saying", "kidding", "want", "need", "are", "you", "is"] for w in words):
        return False
    return True

def is_valid_contact(contact: str) -> bool:
    if not contact:
        return False
    c = contact.strip().lower()
    if "@" in c and "." in c:
        return True
    digits = re.sub(r'\D', '', c)
    return len(digits) >= 8

def is_valid_territory(territory: str) -> bool:
    if not territory:
        return False
    t = territory.strip().lower()
    if any(w in t for w in ["printer", "ink", "cartridge", "what", "why", "want", "need", "canvas", "p9500"]):
        return False
    return True


def extract_lead_signals(text: str) -> dict:
    """Best-effort regex/heuristic extraction of contact/budget/name from raw customer text."""
    signals = {}

    phone_match = PHONE_REGEX.search(text)
    if phone_match:
        digits = re.sub(r'\D', '', phone_match.group(1))
        if len(digits) >= 10:
            signals['contact'] = phone_match.group(1).strip()

    budget_match = BUDGET_REGEX.search(text)
    if budget_match and budget_match.group(1):
        candidate_digits = budget_match.group(1)
        if not signals.get('contact') or candidate_digits not in signals['contact']:
            signals['budget'] = budget_match.group(0).strip()

    name_match = NAME_REGEX.search(text)
    if name_match:
        signals['name'] = name_match.group(1).strip().capitalize()
    else:
        clean_name_text = text
        if phone_match:
            clean_name_text = clean_name_text.replace(phone_match.group(1), "")
        if budget_match:
            clean_name_text = clean_name_text.replace(budget_match.group(0), "")

        clean_name_text = re.sub(
            r'\b(my name is|i am|this is|call me|i\'m|hey|hello|hi|please|thanks|thank you)\b',
            '', clean_name_text, flags=re.IGNORECASE,
        )
        clean_name_text = re.sub(r'[^\w\s]', ' ', clean_name_text)
        name_words = [w.strip() for w in clean_name_text.split() if w.strip()]
        name_words = [w for w in name_words if w.lower() not in NAME_STOPWORDS and w.isalpha()]

        if 1 <= len(name_words) <= 3:
            signals['name'] = " ".join(w.capitalize() for w in name_words)

    return signals


def save_lead_signals_if_any(session_id: str, text: str):
    session = ChatSession.get_or_create(session_id)
    last_assistant_msg = ""
    for msg in reversed(session.get("messages", [])):
        if msg.get("role") == "assistant" and msg.get("content"):
            content_trimmed = msg["content"].strip()
            if not msg.get("tool_calls") and not (content_trimmed.startswith("{") and content_trimmed.endswith("}")):
                last_assistant_msg = content_trimmed.lower()
                break

    asked_name = any(w in last_assistant_msg for w in ["name", "who is", "call you", "introduce"])
    asked_contact = any(w in last_assistant_msg for w in ["contact", "number", "phone", "email", "whatsapp"])
    asked_budget = any(w in last_assistant_msg for w in ["budget", "price range", "limit", "spend", "how much"])

    signals = extract_lead_signals(text)
    if not signals:
        return

    filtered = {}

    is_explicit_name = bool(NAME_REGEX.search(text))
    if (asked_name or is_explicit_name) and signals.get("name") and is_valid_name(signals["name"]):
        filtered["name"] = signals["name"]

    if asked_contact and signals.get("contact"):
        filtered["contact"] = signals["contact"]

    if asked_budget and signals.get("budget"):
        filtered["budget"] = signals["budget"]

    if not filtered:
        return

    try:
        existing_lead = Lead.get_by_session(session_id)
        if existing_lead and existing_lead.get("name") and filtered.get("name"):
            is_explicit = bool(NAME_REGEX.search(text))
            if not is_explicit:
                filtered.pop("name", None)

        if filtered.get("name") or filtered.get("contact") or filtered.get("budget"):
            Lead.create_or_update_lead(
                session_id,
                name=filtered.get("name"),
                contact=filtered.get("contact"),
                needs=None,
                budget=filtered.get("budget"),
            )
            print(f"[{session_id}] Context-aware captured lead signals: {filtered}")
    except Exception as e:
        print(f"[{session_id}] Lead signal save failed: {e}")
