"""
Qualification rules schema enforcing strict 1-question-at-a-time qualification.
Guarantees that the assistant never overwhelms the user with multi-part questions.
"""
from typing import Dict, Any, List, Optional
from orchestration.state import ConversationAIState

QUALIFICATION_RULES: Dict[str, List[Dict[str, Any]]] = {
    "technical_cad": [
        {
            "field": "print_size",
            "priority": 1,
            "question": "What maximum drawing size do you normally print?",
            "options": ["A1 (24-inch)", "A0 (36-inch)", "Large (44-inch)"],
        },
        {
            "field": "scan_required",
            "priority": 2,
            "question": "Do you need built-in scanning for old drawings/blueprints as well?",
            "options": ["Yes (Multifunction MFP)", "No (Print Only)"],
        },
        {
            "field": "daily_volume",
            "priority": 3,
            "question": "Roughly how many drawings or plans do you print per day?",
            "options": ["Light (<15/day)", "Medium (15-50/day)", "High Volume (50+/day)"],
        },
    ],
    "photo_booth": [
        {
            "field": "print_size",
            "priority": 1,
            "question": "What photo print sizes do you mainly produce for your events?",
            "options": ["4×6 standard", "6×8 & strips", "8×10 / 8×12 studio"],
        },
        {
            "field": "monthly_volume",
            "priority": 2,
            "question": "What is your estimated print volume per event?",
            "options": ["100–300 prints", "300–700 prints", "High (800+ prints)"],
        }
    ],
    "photo_fineart": [
        {
            "field": "print_size",
            "priority": 1,
            "question": "What maximum width do you need for your fine art & photo prints?",
            "options": ["24-inch (P7500)", "44-inch (P9500)", "64-inch (P20000)"],
        },
        {
            "field": "use_case",
            "priority": 2,
            "question": "Are you primarily printing on canvas, fine art cotton rag, or photo glossy media?",
            "options": ["Canvas & Fine Art Rag", "Photo Glossy / Luster", "Mixed Media"],
        }
    ],
    "sublimation": [
        {
            "field": "print_size",
            "priority": 1,
            "question": "What width dye-sublimation printer are you looking for?",
            "options": ["A4 Desktop (F100)", "24-inch Roll (F500)", "44-inch+ Industrial (F6400)"],
        },
        {
            "field": "use_case",
            "priority": 2,
            "question": "What items are you transferring onto (mugs/promos, apparel/sportswear, or interior signage)?",
            "options": ["Mugs & Gifts", "Apparel & Sportswear", "Textile & Signage"],
        }
    ],
    "office_business": [
        {
            "field": "print_size",
            "priority": 1,
            "question": "Do you need A4 only or A3/A3+ printing as well?",
            "options": ["A4 Only", "A3 / Tabloid", "Not sure"],
        },
        {
            "field": "monthly_volume",
            "priority": 2,
            "question": "About how many pages does your office print per month?",
            "options": ["Under 2,000 pages", "2,000–10,000 pages", "Over 10,000 pages"],
        }
    ]
}

def get_next_qualification_question(state: ConversationAIState) -> Optional[Dict[str, Any]]:
    """
    Evaluates state and returns the single next highest-priority missing question.
    Returns None if all required fields are collected or category is not qualified.
    """
    category = state.category or "technical_cad"
    rules = QUALIFICATION_RULES.get(category)
    if not rules:
        return None

    for rule in rules:
        field_name = rule["field"]
        # If not answered yet and not previously asked
        if getattr(state, field_name, None) is None and field_name not in state.asked_fields:
            return rule

    return None
