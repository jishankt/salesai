"""
Conversational intercepts for meta queries, greetings, identity, company details, and frustration de-escalation.
Allows the assistant to respond immediately to non-commercial queries without unnecessary tool invocations.
"""
import re
from typing import Tuple, Optional

def get_conversational_intercept(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detects and responds naturally to meta/chit-chat queries.
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

    # 4. Company Location & Office info
    if re.search(r'\b(?:where (?:is|are|you) (?:your )?(?:compnay|company|located|office|ocated)|company location|where is kepler|your office)\b', t):
        return True, "Kepler Tech LLC is located in Dubai, UAE (Al Maktoum Tower, Deira). We supply, deliver, and install equipment directly across Dubai, Abu Dhabi, Sharjah, and all GCC countries! 🚚\n\nWould you like me to prepare an official Proforma Invoice / Quotation draft with delivery terms?"

    # 5. Customer Frustration & Escalation (Rule 9: Apologize sincerely & clarify AI nature)
    if re.search(r'\b(?:annoying|annoyed|terrible|horrible|useless|stupid|worst|bad service|angry|frustrated|waste of time|hate this|stop repeating|ridiculous|pathetic|dont answer|not answering|care fully|carefully|listen to me|pay attention|bullshit|nonsense|crap|what (?:you|are you) saying|rubbish|wrong)\b', t):
        return True, "I am truly sorry for the misunderstanding! 🙏 As an AI sales assistant at Kepler Tech, I am here to help you directly. Please let me know the specific printer model, ink, paper roll, or requirements you are looking for and I will assist you immediately!"

    # 6. Gratitude / Closure
    if re.search(r'^(?:thanks|thank you|thx|great thanks|appreciate it|ok thanks|okay thanks)$', t):
        return True, "You are very welcome! If you need anything else—like sample prints, warranty details, or an official quote—I'm right here to help. Have a wonderful day! 😊"

    # 7. Greetings (including 'hello again', 'hi there', etc.)
    if re.search(r'^(?:hi|hello|hey|good morning|good afternoon|good evening|salaam|marhaba|hello again|hi again|hey again)(?:\s+(?:there|kepler|all|everyone))?$', t):
        return True, "Hello! Welcome to Kepler Tech LLC. How can I assist you today with large format printers, genuine inks, or fine art media?"

    return False, None
