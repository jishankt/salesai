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
    r"\bconsumbls?\b": "consumables",
    r"\bconsumbles?\b": "consumables",
    r"\bconsomables?\b": "consumables",
    r"\bcunsumables?\b": "consumables",
    r"\bcomsumables?\b": "consumables",
    r"\bcartrige?s?\b": "cartridges",
    r"\bcatridges?\b": "cartridges",
    r"\bcatridge\b": "cartridge",
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

    # 2. Feelings, Health & Abstract Chit-Chat
    if re.search(r'\b(?:not (?:feeling|feeeing) well|feeling (?:sick|bad|down|sad|unwell|tired)|i am (?:sick|ill|unwell)|headache|fever)\b', t):
        return True, "I'm so sorry to hear that! Please take care of yourself and rest up. Whenever you're ready, I'll be right here to help you with anything you need. Wishing you a swift recovery! 🌸"

    if re.search(r'\b(?:do you have (?:feelings|feeelings|emotion|emotions)|are you happy|are you good at sales)\b', t):
        return True, "As your Kepler Sales Agent, I'm purely focused on giving you the best technical advice and pricing for printing equipment! What kind of printing project are you working on today? 🎨"

    # 3. Learning & Memory capability questions
    if re.search(r'\b(?:leaning ability|learning ability|do you learn|can you learn|do you remember me)\b', t):
        return True, "I remember and track our full conversation during your active session to assist your order accurately. What printing equipment or supplies can I assist you with?"

    # 4. Company Location & Office info / Where to Buy
    if re.search(r'\b(?:where (?:is|are|you) (?:your )?(?:compnay|company|located|office|ocated)|company location|where is kepler|your office|where (?:can|do) i (?:buy|order|purchase|get)|how to (?:buy|order|purchase)|where to buy)\b', t):
        return True, "Kepler Tech LLC is located in Dubai, UAE (Al Maktoum Tower, Deira). We supply, deliver, and install equipment directly across Dubai, Abu Dhabi, Sharjah, and all GCC countries! 🚚\n\nWould you like me to prepare an official Proforma Invoice / Quotation draft with delivery terms?"

    # 4b. Consumables & Supplies Capability Questions
    # (e.g. "do you provide consumables", "do you provide consumabls", "do you sell consumables", "do you have consumables", "do you provide inks", "do you sell ink", "can you supply paper")
    if re.search(r'\b(?:do\s+you|can\s+you|can\s+i|do\s+we|are\s+you)\s+(?:provide|supply|sell|carry|have|offer|stock|get)\s+(?:any\s+)?(?:consumables?|supplies|inks?|cartridges?|toners?|maintenance\s+box(?:es)?|waste\s+(?:box|tank)|media(?:\s+rolls?)?|papers?|ribbons?)\b', t) or re.search(r'^(?:do\s+you\s+(?:provide|sell|carry|have|supply)\s+)?(?:consumables?|supplies)$', t) or re.search(r'\b(?:provide|supply|sell)\s+(?:consumables?|supplies|inks?)\b', t):
        return True, (
            "Yes, absolutely! We provide 100% genuine OEM consumables for all Epson and Citizen printing equipment, including:\n\n"
            "• 💧 **Genuine Inks:** Epson UltraChrome PRO12, XD3, and WorkForce high-capacity ink cartridges\n"
            "• 📦 **Maintenance Boxes:** Original OEM waste ink tanks and replacement pads\n"
            "• 📜 **Media & Paper Rolls:** Innova fine art smooth cotton papers and Korejet canvas rolls\n"
            "• 📸 **Citizen Photo Ribbons:** Original ribbon and paper sets for CX-02, CZ-01, and CY-02\n\n"
            "Which printer model do you need consumables for? Just let me know your model (e.g., *SC-T5700D*, *WF-C21000*, or *SC-P9500*) and I'll find the exact compatible supplies for you! 😊\n\n"
            "[Options: SureColor SC-P Inks | WorkForce Pro Inks | EcoTank / Dye-Sub | Canvas Rolls]"
        )

    # 4c. Authorized Distributor / Genuine Products Questions
    if re.search(r'\b(?:authorized|authorised|official|distributor|dealer)\b.*\b(?:epson|citizen|kepler)\b|\b(?:is\s+it\s+(?:original|genuine)|are\s+(?:they|your\s+products?|your\s+inks?)\s+(?:original|genuine)|are\s+you\s+(?:official|authorized|authorised))\b', t):
        return True, (
            "Yes! Kepler Tech LLC is an official authorized distributor for Epson Commercial & Large Format Printing Systems and Citizen Photo Printers across the UAE and Middle East. 🛡️\n\n"
            "Every printer, UltraChrome ink cartridge, and accessory is 100% genuine OEM with factory warranty and certified local engineer support.\n\n"
            "What type of equipment or supplies can I assist you with today?\n\n"
            "[Options: Technical / CAD | Office & Enterprise | Inks & Consumables | Check Stock & Delivery]"
        )

    # 4d. General Product Range / What do you sell / provide
    if re.search(r'\b(?:what(?:\s+kind\s+of|\s+type\s+of)?\s+(?:products?|printers?|equipment|plotters?)\s+do\s+you\s+(?:have|sell|provide|carry|offer)|what\s+do\s+you\s+(?:sell|provide|offer|carry)|what\s+products?\s+(?:do\s+you\s+have|are\s+available)|product\s+range)\b', t):
        return True, (
            "At Kepler Tech, we provide commercial printing hardware, genuine inks, and media across four core categories: 🖨️\n\n"
            "• 📐 **Technical & CAD Plotters:** Epson SureColor SC-T series (24\" to 44\" for architectural drawings & GIS maps)\n"
            "• 🏢 **High-Speed Office MFPs:** Epson WorkForce Enterprise (up to 100 ppm Heat-Free departmental printing)\n"
            "• 📸 **Photo Booth & Events:** Citizen compact dye-sub photo printers (CX-02, CZ-01, CY-02)\n"
            "• 🎨 **Photo & Fine Art:** Epson SureColor SC-P series (12-color UltraChrome PRO archival systems)\n"
            "• 💧 **Genuine Supplies:** UltraChrome inks, maintenance tanks, canvas rolls, and photo media\n\n"
            "Which category are you interested in exploring today?\n\n"
            "[Options: Technical / CAD | Office & Enterprise | Photo Booth | Fine Art & Photo]"
        )

    # 4e. Warranty, Maintenance, Repair & Service inquiries
    if re.search(r'\b(?:do\s+you\s+(?:provide|offer|give|have)\s+)?(?:warranty|guarantee|maintenance(?:\s+contract)?|amc|service\s+contract|installation|repairs?|servicing|setup|technical\s+support)\b', t) and not any(k in t for k in ["price", "cost", "how much"]):
        return True, (
            "Yes! All equipment supplied by Kepler Tech is backed by comprehensive technical support: 🛠️\n\n"
            "• **Official Factory Warranty:** Direct manufacturer warranty on all Epson and Citizen machines\n"
            "• **UAE Delivery & On-Site Installation:** Available across Dubai, Abu Dhabi, Sharjah, and all emirates\n"
            "• **Annual Maintenance Contracts (AMC):** Preventive maintenance visits and certified technician assistance\n"
            "• **Genuine Spare Parts:** Direct factory replacement parts and printheads\n\n"
            "Are you looking for service on an existing machine, or considering new equipment with warranty?\n\n"
            "[Options: Technical / CAD | Office & Enterprise | Inks & Consumables | Connect with Specialist]"
        )

    # 4f. Showroom / In-person demonstration inquiries
    if re.search(r'\b(?:showroom|visit\s+(?:your\s+)?(?:office|shop|showroom|store)|see\s+(?:in\s+person|demo|machine|printers?)|demo\s+center|live\s+demo)\b', t):
        return True, (
            "You are very welcome to visit our office in Dubai, UAE (Al Maktoum Tower, Deira)! 🏢\n\n"
            "We offer live equipment demonstrations, sample print testings, and media evaluation for our Epson SureColor plotters, fine art printers, and Citizen photo booth machines.\n\n"
            "Would you like to schedule a demonstration or speak with our hardware specialist?\n\n"
            "[Options: Technical / CAD | Office & Enterprise | Check Stock & Delivery | Connect with Specialist]"
        )

    # 4g. Payment methods / options
    if re.search(r'\b(?:how\s+(?:can\s+i|to)\s+pay|payment\s+methods?|payment\s+options?|accept\s+card|accept\s+cash|credit\s+card|bank\s+transfer|wire\s+transfer)\b', t):
        return True, (
            "We support convenient payment options for both corporate accounts and individual buyers across the UAE: 💳\n\n"
            "• **Online Card Payment:** Instant secure card checkout (Visa, Mastercard)\n"
            "• **Bank Wire Transfer:** Direct corporate TT / bank transfer against official Proforma Invoices\n"
            "• **Cheque / COD:** Available for approved corporate clients and volume delivery orders\n\n"
            "Would you like me to prepare an official Proforma Invoice / quotation draft for your equipment or supplies?\n\n"
            "[Options: Draft Quotation | Check Stock & Delivery | Contact Specialist]"
        )

    # 5. Delivery & Territory Questions & Stock Checks
    if re.search(r'\b(?:check stock & delivery|check delivery & stock|check stock|check delivery|delivery options?|delivery terms?)\b', t) or (
        re.search(r'\b(?:delivery|deliver|shipping|ship|do you deliver|can you deliver|deliver to|ship to)\b.*\b(?:abu dhabi|sharjah|dubai|al ain|ajman|rak|fujairah|uae|musaffah|gcc|saudi)\b|\b(?:where do you deliver|delivery areas|delivery locations)\b', t)
    ):
        return True, "🚚 **Kepler Tech Delivery & Stock Information:**\n\n• **Direct Dispatch:** All in-stock printers, genuine inks, and maintenance supplies ship directly from our Dubai central warehouse.\n• **UAE Delivery:** 24–48 hours across Dubai, Abu Dhabi, Sharjah, Ajman, RAK, and Al Ain.\n• **GCC Freight:** Regular dispatch to Saudi Arabia, Oman, Qatar, Bahrain, and Kuwait.\n• **Complimentary Delivery:** Included on qualifying commercial hardware and volume supply orders.\n\nWould you like me to check stock availability or show compatible inks and supplies?\n\n[Options: Inquire Discount | Compatible Inks & Supplies | Check Stock & Delivery]"

    # 6. Price / Cost / How-much questions — redirect to website
    if re.search(r'\b(?:what(?:\s+is|\s+are)?\s+(?:the\s+)?(?:price|cost|rate|pricing|fee|fees)|how\s+much|price\s+(?:of|for)|cost\s+(?:of|for)|any\s+price|what\s+(?:is\s+)?(?:your\s+)?price|tell\s+me\s+(?:the\s+)?price|give\s+me\s+(?:the\s+)?price|i\s+want\s+to\s+know\s+(?:the\s+)?price|price\s+list|price\s+details?|pricing\s+(?:for|of|details?)|aed\s+price|check\s+price|price\s+check|how\s+much\s+(?:does|is|it\s+costs?))\b', t):
        return True, "For the latest pricing, please tap the 🔗 **Website** link on any product card to view current AED pricing directly on our official Kepler Tech store!\n\nWould you like me to help you find the right product first?\n\n[Options: Technical / CAD | Office & Enterprise | Photo Booth | Fine Art & Photo]"

    # 6b. Discount questions — redirect to website
    if re.search(r'\b(?:inquire discount|request (?:bulk|volume) discount|give me (?:a )?discounts?|any discount|discount for products?|best price|special offer|what discount|discount do you give|bulk discount|volume discount|any offer|any deal|best deal)\b', t):
        return True, "For the best pricing and any ongoing offers, please visit the product page directly on our official website — all current prices and deals are listed there! 🔗\n\nWould you like me to help you find the right product?\n\n[Options: Technical / CAD | Office & Enterprise | Photo Booth | Fine Art & Photo]"

    # 7. Conversational Clarification on Single-Word Confusion ("what", "huh", "pardon", "sorry")
    if t in ("what", "what?", "huh", "huh?", "pardon", "sorry?", "i don't understand", "idk"):
        return True, "I'm here to help you find the right printing equipment or supplies at Kepler Tech! 😊\n\nWould you like to check live equipment stock, delivery terms, or view compatible inks?\n\n[Options: Check Stock & Delivery | Inquire Discount | Inks & Consumables]"

    # 8. Compliments, Product Praise & General pleasantries
    if re.search(r'\b(?:good (?:product|printer|quality|ai|model|bot|job)|nice (?:product|printer|bot)|great (?:product|printer|job)|you are good|well done|thank you|thanks|looks good|this is good|i like this)\b', t) and not any(k in t for k in ["price", "cost", "how much"]):
        return True, "Thank you! It is indeed one of our most dependable, high-performance solutions. Would you like me to prepare an official Proforma Invoice / Quotation draft with delivery terms, or show compatible supplies?\n\n[Options: Draft Quotation | Check Stock & Delivery | Inquire Discount]"

    # 9. Customer Frustration / Annoyance / Complaint Handling with sincere apology
    if re.search(r'\b(?:angry|annoyed|frustrated|irritated|upset|terrible|horrible|useless|bad service|worst service|stupid bot|waste of time|not helping|stop repeating|you don\'t understand|you dont understand|nonsense|disappointed)\b', t):
        return True, "I am truly sorry for the frustration and inconvenience! 🙏 We deeply value your time. I want to make sure your requirements are handled properly — would you like me to connect you with our senior human sales specialist right now?\n\n[Options: Connect with Specialist | Check Stock & Delivery | Inquire Discount]"

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
        return "Epson WorkForce DS-70 Business Scanner"
    if t in ("a3 large format flatbed", "a3 flatbed", "large format flatbed"):
        return "Epson Expression 12000XL Photo Scanner"
    if t in ("high-speed document scanner", "high speed scanner", "document scanner"):
        return "Epson WorkForce DS-900WN High-Speed Network Document Scanner"

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
            
    # Direct mapping for Category Pills
    if t in ("technical / cad", "technical", "cad", "cad plotters", "technical plotters"):
        return "Epson SureColor SC-T CAD Technical Plotter"
    if t in ("office & enterprise", "office", "enterprise", "workforce", "business printers", "office printers"):
        return "Epson WorkForce Business Office Printer"
    if t in ("photo booth", "photo booth printers", "citizen", "citizen photo"):
        return "Citizen Photo Printer"
    if t in ("fine art & photo", "fine art", "photo printers", "fine art photo"):
        return "Epson SureColor SC-P Fine Art Photo Printer"

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
    is_asking_for_maint = any(k in t for k in ["maintenance", "maintenance box", "waste box", "waste ink", "maintenance tank", "tank"])
    is_asking_for_inks = any(k in t for k in ["ink", "inks", "cartridge", "cartridges", "bottle", "bottles", "ribbon", "media", "paper"]) and not is_asking_for_maint
    is_asking_for_all = any(k in t for k in ["consumables", "consumable", "consumbls", "consumble", "consumabls", "supplies", "supply", "full set", "all consumables"]) or bool(re.search(r'\bcons?u?m[a-z]*bl[a-z]*\b', t))
    is_asking_for_ink = is_asking_for_maint or is_asking_for_inks or is_asking_for_all
    
    cons_sub_type = "maintenance" if is_asking_for_maint else ("inks" if is_asking_for_inks else "all")

    if is_anaphoric:
        session = ChatSession.get_or_create(session_id)
        last_prod = extract_last_mentioned_product_from_history(session.get("messages", []))
        if last_prod:
            if is_asking_for_ink:
                return f"get_printer_consumables for {last_prod}|type={cons_sub_type}"
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

    _PRINTER_MODEL_PATTERN = r'\b(WF-[A-Z0-9]+(?:\s+[A-Z0-9]+)?|EM-[A-Z0-9]+|SC-[A-Z0-9]+|AM-[A-Z0-9]+|P\d{3,5}[A-Z0-9]*|T\d{3,5}[A-Z0-9]*|F\d{3,4}[A-Z0-9]*|C\d{4,5}[A-Z0-9]*|CX-02W|CX-02|CX02|CZ-01|CY-02|L\d{4}[A-Z0-9]*)\b'

    # Check negative correction intent (e.g. "these are not F100 inks", "not for this printer", "wrong inks")
    is_correction = any(k in t for k in ["these are not", "this is not", "not f100", "wrong ink", "not the ink", "not for f100", "not for sc-f100", "incorrect ink", "different ink"])
    if is_correction:
        m = re.search(_PRINTER_MODEL_PATTERN, user_text, re.IGNORECASE)
        if m:
            printer_code = m.group(1).upper()
            return f"get_printer_consumables for {printer_code}|type={cons_sub_type}"
        session = ChatSession.get_or_create(session_id)
        last_prod = extract_last_mentioned_product_from_history(session.get("messages", []))
        if last_prod:
            return f"get_printer_consumables for {last_prod}|type={cons_sub_type}"

    # If user mentions specific printer + ink / supplies / maintenance in a single phrase e.g. "maintenance box for f100" or "cx-02 consumables"
    if is_asking_for_ink:
        m = re.search(_PRINTER_MODEL_PATTERN, user_text, re.IGNORECASE)
        if m:
            printer_code = m.group(1).upper()
            return f"get_printer_consumables for {printer_code}|type={cons_sub_type}"
        m_for = re.search(r'(?:for|of)\s+([A-Za-z0-9\-]+)', t)
        if m_for:
            code = m_for.group(1).strip().upper()
            if len(code) >= 3 and code.lower() not in ("it", "that", "this", "printer", "plotter", "machine", "me", "my"):
                return f"get_printer_consumables for {code}|type={cons_sub_type}"
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


