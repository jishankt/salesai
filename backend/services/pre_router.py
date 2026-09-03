"""
Pre-router input normalization and multi-intent detection.
Operates before the primary router and agent loop to clean noisy transcripts/typos
and decompose compound multi-intent messages.
"""
import re
from typing import List, Dict, Any, Tuple, Optional

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

def get_conversational_intercept(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detects and responds naturally to meta/chit-chat queries without treating them as product search keywords.
    Returns: (is_intercepted: bool, reply_text: Optional[str])
    """
    if not text:
        return False, None
    t = text.lower().strip("?,. !\"'")

    # 1. Identity & Creation Questions
    if re.search(r'\b(?:what is your name|who are you|whats your name|who r u)\b', t):
        return True, "I am the Kepler Sales Agent, your consultative assistant for Epson and Citizen printing solutions at Kepler Tech LLC in Dubai. 😊 How can I help you today?"
    
    if re.search(r'\b(?:who made you|who created you|who built you|what model are you)\b', t):
        return True, "I am developed by Kepler Tech's AI team to assist customers with product consultations, live stock verification, and quotations for printing equipment. 🖨️"

    if re.search(r'\b(?:are you (?:a )?human|are you real|are you a bot|are you an ai|are you robot)\b', t):
        return True, "I'm Kepler Tech's AI sales specialist! I can assist you directly with product specs, live pricing in AED, and instant quotation drafting. If you ever prefer a human colleague, I can connect you anytime. 😊"

    # 2. Feelings & Abstract Chit-Chat
    if re.search(r'\b(?:do you have (?:feelings|feeelings|emotion|emotions)|are you happy|are you good at sales)\b', t):
        return True, "As your Kepler Sales Agent, I'm purely focused on giving you the best technical advice and pricing for printing equipment! What kind of printing project are you working on today? 🎨"

    # 3. Learning & Memory capability questions
    if re.search(r'\b(?:leaning ability|learning ability|do you learn|can you learn|do you remember me)\b', t):
        return True, "I remember and track our full conversation during your active session to assist your order accurately. What printing equipment or supplies can I assist you with?"

    # 4. Company Location & Office info / Where to Buy
    if re.search(r'\b(?:where (?:is|are|you) (?:your )?(?:compnay|company|located|office|ocated)|company location|where is kepler|your office|where (?:can|do) i (?:buy|order|purchase|get)|how to (?:buy|order|purchase)|where to buy)\b', t):
        return True, "Kepler Tech LLC is located in Dubai, UAE (Al Maktoum Tower, Deira). We supply, deliver, and install equipment directly across Dubai, Abu Dhabi, Sharjah, and all GCC countries! 🚚\n\nWould you like me to prepare an official Proforma Invoice / Quotation draft with delivery terms?"

    # 5. Delivery & Territory Questions
    if re.search(r'\b(?:delivery|deliver|shipping|ship|do you deliver|can you deliver|deliver to|ship to)\b.*\b(?:abu dhabi|sharjah|dubai|al ain|ajman|rak|fujairah|uae|musaffah|gcc|saudi)\b|\b(?:where do you deliver|delivery areas|delivery locations)\b', t):
        return True, "Yes! Kepler Tech provides direct delivery across all UAE Emirates (Dubai, Abu Dhabi, Sharjah, Ajman, RAK, Fujairah, Al Ain) and across the GCC! 🚚 Complimentary delivery is available on qualifying commercial orders."

    # 6. Discount & Commercial Pricing Policy
    if re.search(r'\b(?:give me (?:a )?discounts?|any discount|discount for products?|best price|special offer|what discount|discount do you give|bulk discount|who give you the (?:permission|prermisssion))\b', t):
        return True, "We offer standard catalog pricing with an automatic 10% volume discount on orders of 5+ units, plus custom project quotes for commercial studios. Which equipment or consumables are you considering? 💼"

    # 7. Conversational Clarification on Single-Word Confusion ("what", "huh", "pardon", "sorry")
    if t in ("what", "what?", "huh", "huh?", "pardon", "sorry?", "i don't understand", "idk"):
        return True, "I'm here to help you find the right printing equipment or supplies at Kepler Tech! 😊\n\nWould you like me to create an official quotation draft for your equipment, check live stock, or list compatible inks?\n\n[Options: Prepare Quotation | Check Stock & Delivery | Inks & Consumables]"

    # 8. Compliments & General pleasantries
    if re.search(r'\b(?:good ai|good model|nice bot|great job|you are good|well done|thank you|thanks)\b', t) and not any(k in t for k in ["price", "cost", "printer", "ink", "canvas"]):
        return True, "Thank you! I'm here to ensure you get the exact right printing solution. Let me know what you need or if you'd like me to recommend a setup."

    return False, None

def extract_last_mentioned_product_from_history(messages: list) -> Optional[str]:
    """
    Extracts the most recent specific printer model or product SKU mentioned in the session history.
    """
    if not messages:
        return None
    
    # Check messages from newest to oldest
    for msg in reversed(messages):
        content = msg.get("content", "")
        if not content:
            continue
        
        # Check for Citizen models
        if "citizen cx-02w" in content.lower() or "cx-02w" in content.lower():
            return "Citizen CX-02W"
        if "citizen cx-02" in content.lower() or "cx-02" in content.lower() or "cx02" in content.lower():
            return "Citizen CX-02"
        if "citizen cz-01" in content.lower() or "cz-01" in content.lower():
            return "Citizen CZ-01"
            
        # Check for Epson SureColor / WorkForce models
        sc_match = re.search(r'\b(SC-P\d{3,5}[A-Z0-9]*|SC-T\d{3,5}[A-Z0-9]*|SC-F\d{3,5}[A-Z0-9]*|WF-[A-Z0-9]+|EM-[A-Z0-9]+|P\d{3,5}[A-Z0-9]*)\b', content, re.IGNORECASE)
        if sc_match:
            return sc_match.group(1).upper()
            
        # Check for Epson product names in cards
        name_match = re.search(r'📦 \*([^*]+)\*', content)
        if name_match:
            return name_match.group(1).strip()

    return None

def resolve_conversational_subject(session_id: str, user_text: str) -> str:
    """
    If the user's message contains anaphoric pronouns or follow-up confirmation phrases
    like 'send the details', 'yes that printer', 'how much is it', 'full set', resolve it to the specific product.
    """
    from models.chat_session import ChatSession
    t = user_text.lower().strip("?,. !\"'")
    
    # Check option pill replies for categories & consumables (e.g. "office / business", "technical / cad", "full set")
    # Printers Category Options
    if t in ("office / business", "office & enterprise", "office", "business", "business printers", "office printer"):
        return "Epson WorkForce Business Office Printer"
    if t in ("technical / cad", "technical", "cad", "cad / gis", "gis", "plotter", "technical & cad/gis"):
        return "Epson SureColor SC-T CAD Technical Plotter"
    if t in ("photo booth", "photo booth & events", "events", "photo booth printer"):
        return "Citizen Photo Printer"
    if t in ("fine art & photo", "fine art & photography", "fine art", "photo"):
        return "Epson SureColor SC-P Fine Art Photo Printer"
        
    # Inks Category Options
    if t in ("surecolor sc-p inks", "sc-p inks", "fine art inks", "ultrachrome inks"):
        return "Epson UltraChrome PRO12 SC-P Ink Cartridge"
    if t in ("workforce pro inks", "workforce inks", "office inks", "business inks"):
        return "Epson WorkForce Pro Ink Cartridge"
    if t in ("ecotank / dye-sub", "dye-sub", "ecotank", "sublimation"):
        return "Epson SureColor SC-F Dye Sublimation Ink"
        
    # Papers & Media Category Options
    if t in ("artistic canvas rolls", "canvas rolls", "canvas"):
        return "Korejet Artistic Gloss Matte Canvas Roll"
    if t in ("fine art smooth paper", "fine art paper", "smooth art"):
        return "Innova Fine Art Smooth Cotton Paper"
    if t in ("photo gloss / luster", "photo gloss", "luster", "glossy paper"):
        return "Epson Premium Luster Photo Paper Roll"
        
    # Scanner Category Options
    if t in ("a4 business scanner", "business scanner"):
        return "Epson WorkForce Document Scanner A4"
    if t in ("a3 large format flatbed", "a3 flatbed", "large format flatbed"):
        return "Epson Expression A3 Graphic Flatbed Scanner"
    if t in ("high-speed document scanner", "high speed scanner", "document scanner"):
        return "Epson WorkForce DS Document Scanner"

    if t in ("full set", "just inks", "just the inks", "just maintenance box", "just the maintenance box", "all inks"):
        session = ChatSession.get_or_create(session_id)
        last_prod = extract_last_mentioned_product_from_history(session.get("messages", []))
        if last_prod:
            return f"get_printer_consumables for {last_prod}"
        return user_text

    anaphoric_triggers = [
        "send the details", "send details", "send me the details", "give details", "give me details",
        "yes that printer", "that printer", "the printer", "yes that one", "that one",
        "how much is it", "how much is that", "tell me more about that", "tell me more",
        "is it in stock", "is that in stock", "add that", "i want that one", "i want that"
    ]
    
    is_anaphoric = any(t == trig or t.startswith(trig) for trig in anaphoric_triggers)
    if not is_anaphoric:
        # Check standalone pronouns
        if re.search(r'\b(?:it|that|this one|that printer|the printer)\b', t) and len(t.split()) <= 4:
            is_anaphoric = True
            
    # Check if user is asking for more products / next batch in the same category (e.g. "i want more", "more list", "show more printers")
    is_more_request = any(k in t for k in ["i want more", "want more", "more list", "show more", "more printers", "more models", "other models", "see more", "next", "more"])
    if is_more_request:
        session = ChatSession.get_or_create(session_id)
        history = session.get("messages", [])
        prev_user_cats = []
        for m in reversed(history):
            if m.get("role") == "user":
                ut = m.get("content", "").lower()
                if "fine art" in ut or "photo" in ut:
                    return "Epson SureColor SC-P Fine Art Photo Printer"
                elif "cad" in ut or "technical" in ut or "plotter" in ut:
                    return "Epson SureColor SC-T CAD Technical Plotter"
                elif "office" in ut or "enterprise" in ut or "workforce" in ut:
                    return "Epson WorkForce Business Office Printer"
                elif "booth" in ut or "citizen" in ut:
                    return "Citizen Photo Printer"

    # Check if user is asking for ink/consumables for the previously discussed printer
    ink_triggers = [
        "ink", "inks", "consumables", "consumable", "supplies", "supply", "cartridge", "cartridges",
        "ribbon", "media", "paper", "cleaning", "maintenance", "maintenance box", "waste box", "waste ink", "maintenance tank"
    ]
    is_asking_for_ink = any(k in t for k in ink_triggers)
    
    if is_anaphoric:
        session = ChatSession.get_or_create(session_id)
        last_prod = extract_last_mentioned_product_from_history(session.get("messages", []))
        if last_prod:
            if is_asking_for_ink:
                return f"get_printer_consumables for {last_prod}"
            return f"Give details and quotation for {last_prod}"
            
    # Check standalone number / volume responses (e.g. user replies "2000" or "500" to volume question)
    if re.match(r'^\d{2,6}\s*(?:pages?|prints?|copies|docs?|units?)?$', t):
        session = ChatSession.get_or_create(session_id)
        history = session.get("messages", [])
        # Check if the previous question was about office or monthly volume
        prev_bot_msg = ""
        for m in reversed(history):
            if m.get("role") == "assistant" and m.get("content"):
                prev_bot_msg = m.get("content", "").lower()
                break
        if "office" in prev_bot_msg or "volume" in prev_bot_msg or "pages" in prev_bot_msg:
            return f"office printer for {t} pages"
        if "budget" in prev_bot_msg or "price" in prev_bot_msg:
            return f"printer under {t} AED"

    # Check negative correction intent (e.g. "these are not F100 inks", "not for this printer", "wrong inks")
    is_correction = any(k in t for k in ["these are not", "this is not", "not f100", "wrong ink", "not the ink", "not for f100", "not for sc-f100", "incorrect ink", "different ink"])
    if is_correction:
        m = re.search(r'\b(WF-[A-Z0-9]+|EM-[A-Z0-9]+|SC-[A-Z0-9]+|AM-[A-Z0-9]+|P\d{3,5}[A-Z0-9]*|T\d{3,5}[A-Z0-9]*|F\d{3,4}[A-Z0-9]*|C\d{4,5}[A-Z0-9]*|CX-02W|CX-02|CX02|CZ-01|CY-02)\b', user_text, re.IGNORECASE)
        if m:
            printer_code = m.group(1).upper()
            return f"get_printer_consumables for {printer_code}"
        session = ChatSession.get_or_create(session_id)
        last_prod = extract_last_mentioned_product_from_history(session.get("messages", []))
        if last_prod:
            return f"get_printer_consumables for {last_prod}"

    # If user mentions specific printer + ink / supplies / maintenance in a single phrase e.g. "maintenance box for f100" or "cx-02 consumables"
    if is_asking_for_ink:
        m = re.search(r'\b(WF-[A-Z0-9]+|EM-[A-Z0-9]+|SC-[A-Z0-9]+|AM-[A-Z0-9]+|P\d{3,5}[A-Z0-9]*|T\d{3,5}[A-Z0-9]*|F\d{3,4}[A-Z0-9]*|C\d{4,5}[A-Z0-9]*|CX-02W|CX-02|CX02|CZ-01|CY-02)\b', user_text, re.IGNORECASE)
        if m:
            printer_code = m.group(1).upper()
            return f"get_printer_consumables for {printer_code}"
        if re.search(r'\b(?:it|that|this|the printer|my printer)\b', t):
            session = ChatSession.get_or_create(session_id)
            last_prod = extract_last_mentioned_product_from_history(session.get("messages", []))
            if last_prod:
                clean_ink_query = re.sub(r'\b(?:for it|for that|for this|for the printer)\b|\?', '', user_text, flags=re.IGNORECASE).strip()
                return f"{clean_ink_query} {last_prod}"

    return user_text

def detect_multi_intents(text: str) -> List[Dict[str, Any]]:
    """Splits compound messages into sequential sub-intents."""
    norm = normalize_user_input(text)
    norm_l = norm.lower()
    intents = []

    # Check for location/territory mention
    found_territory = None
    for terr in KNOWN_TERRITORIES:
        if terr in norm_l:
            found_territory = terr.title()
            break

    # Split compound clauses on coordinating conjunctions
    clauses = re.split(r'\b(?:and also|and|plus|along with|also)\b|\?|\,', norm, flags=re.IGNORECASE)
    clauses = [c.strip() for c in clauses if c.strip()]

    for clause in clauses:
        c_l = clause.lower()
        if any(w in c_l for w in ["deliver", "delivery", "shipping", "located", "from", "in", "send to"]) and found_territory:
            intents.append({
                "type": "TERRITORY_QUERY",
                "territory": found_territory,
                "text": clause
            })
        elif any(k in c_l for k in ["p9500", "p7500", "p9000", "p20000", "p8000", "cx", "cz", "printer", "ink", "canvas", "paper", "epson", "citizen"]):
            intents.append({
                "type": "PRODUCT_QUERY",
                "text": clause
            })

    if not intents:
        if found_territory and any(w in norm_l for w in ["deliver", "delivery", "in", "from"]):
            intents.append({"type": "TERRITORY_QUERY", "territory": found_territory, "text": norm})
        else:
            intents.append({"type": "GENERAL_MESSAGE", "text": norm})

    return intents


