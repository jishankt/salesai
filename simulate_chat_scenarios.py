"""
Autonomous stress test script simulating real conversation sessions across all edge cases:
1. Multi-turn discovery & 1-question qualification continuity
2. Exact product & consumable lookup (e.g. SC-T3700DE -> Inks)
3. Out of area / out of catalog queries (shoes, iPhones, non-existent models)
4. Pronoun / anaphora continuity ('that printer', 'give me price for it')
5. Multiple questions asked in a single turn
6. Customer frustration / anger and apology de-escalation
7. Commercial pricing, bulk discounts & quotation
8. Order checkout & payment link generation
"""
import sys
import os
import json

# Ensure python path
root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(root, "backend"))
sys.path.insert(0, root)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from orchestration.orchestrator import ConversationOrchestrator
from orchestration.state_repository import StateRepository

def run_chat_session(title, turns):
    print(f"\n=======================================================")
    print(f"🧪 SCENARIO: {title}")
    print(f"=======================================================")
    session_id = f"sim_{os.urandom(4).hex()}"
    StateRepository.clear_cache()

    for idx, user_msg in enumerate(turns, 1):
        print(f"\n👤 [User Turn {idx}]: {user_msg}")
        res = ConversationOrchestrator.process_message(session_id, user_msg)
        reply = res.get("content", "")
        orch = res.get("orchestration", {})
        
        # Display first few lines of reply
        reply_lines = reply.strip().split("\n")
        display_reply = "\n   ".join(reply_lines[:6])
        if len(reply_lines) > 6:
            display_reply += f"\n   ... [{len(reply_lines) - 6} more lines of cards/details]"
        
        print(f"🤖 [Agent]:\n   {display_reply}")
        if orch:
            print(f"   [State Engine] -> Intent: {orch.get('intent')} | Stage: {orch.get('sales_stage')} | Action: {orch.get('action')}")

def main():
    # Scenario 1: Multi-turn Qualification & Continuity
    run_chat_session("1. Qualification & Continuity Flow", [
        "Hi, I run an architecture firm and we need a large format printer.",
        "A1 (24-inch)",
        "We also need scanning for blueprints.",
        "What inks does it take?"
    ])

    # Scenario 2: Out of Area / Out of Scope Queries
    run_chat_session("2. Out of Scope & Non-Existent Models", [
        "Do you sell Nike running shoes or iPhone 16?",
        "Do you have the Epson SureColor P99999 500-inch gold edition printer in stock?",
        "Do you deliver to London, UK?"
    ])

    # Scenario 3: Multiple Asks in a Single Turn
    run_chat_session("3. Compound Multi-Question Turn", [
        "Can you tell me about the Citizen CX-02, what size photos it prints, and what discount you give for 10 units?",
        "Send me quotation for it."
    ])

    # Scenario 4: Frustration, Escalation & De-escalation
    run_chat_session("4. Customer Frustration & Apology Flow", [
        "Why is this taking so long? This is so frustrating and annoying!",
        "Can I speak with a human sales manager?",
        "Okay, fine. What is your office address in Dubai?"
    ])

    # Scenario 5: Exact Model Lookup, Anaphora & Cart/Checkout
    run_chat_session("5. Exact Model -> Inks -> Quotation -> Checkout", [
        "SC-T3700DE",
        "Check inks for that printer",
        "Give me price for 5 units of C13T50M100",
        "Send me the payment link please"
    ])

if __name__ == "__main__":
    main()
