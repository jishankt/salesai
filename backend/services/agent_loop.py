"""
The agent loop.

Small local models via Ollama skip or garble tool calls unpredictably. Rather
than hoping the model behaves, this loop layers deterministic checks on top:
  - pre-fetching product search results before the model even replies, so
    product facts are never invented
  - detecting when the model *says* it will check something but doesn't call
    a tool, and forcing a retry
  - detecting a payment-link placeholder without a real create_order/
    checkout_cart call, and forcing that too
  - a manual JSON-in-text fallback parser for models that emit a tool call as
    plain text instead of using the tools API field

None of this makes the small model smarter — it makes its failure modes
survivable.
"""
import re
import json

from models.chat_session import ChatSession
from models.lead import Lead
from models.order import Order
from models.cart import Cart
from tools.handlers import checkout_cart
from services.ollama_client import chat_completion, OllamaError
from services.lead_extraction import looks_like_product_question, save_lead_signals_if_any, is_valid_name, is_valid_contact, is_valid_territory
from services.rendering import render_payment_button, render_payment_text
from tools.definitions import OLLAMA_TOOLS
from tools.handlers import TOOL_MAP, search_products
from config import Config

def translate_text(text: str, target_lang: str) -> str:
    if not text or not text.strip() or target_lang in ("English", "en", "en-US"):
        return text
    prompt = (
        f"You are a professional translator. Translate the following text into {target_lang}. "
        "Do NOT add any explanation, commentary, or introduction. Return ONLY the translation.\n\n"
        f"Text: \"{text}\"\n"
        "Translation:"
    )
    try:
        result = chat_completion([{"role": "user", "content": prompt}], temperature=0.1)
        translated = result.get("message", {}).get("content", "").strip()
        if (translated.startswith('"') and translated.endswith('"')) or (translated.startswith("'") and translated.endswith("'")):
            translated = translated[1:-1].strip()
        return translated
    except Exception as e:
        print(f"Translation error to {target_lang}: {e}")
        return text

def translate_to_english(text: str) -> str:
    if not text or not text.strip():
        return text
    # Fast path: English ASCII text does not need translation API calls
    if all(ord(c) < 128 for c in text):
        return text
    prompt = (
        "You are a professional translator. Translate the following text into English. "
        "Do NOT add any explanation, commentary, or introduction. Return ONLY the translation.\n\n"
        f"Text: \"{text}\"\n"
        "Translation:"
    )
    try:
        result = chat_completion([{"role": "user", "content": prompt}], temperature=0.1)
        translated = result.get("message", {}).get("content", "").strip()
        if (translated.startswith('"') and translated.endswith('"')) or (translated.startswith("'") and translated.endswith("'")):
            translated = translated[1:-1].strip()
        return translated
    except Exception as e:
        print(f"Translation to English error: {e}")
        return text

import random
from datetime import datetime

GREETING_VARIANTS = [
    "Welcome to Kepler Tech! 🖨️ We specialize in Epson Large Format Printers, Citizen Photo Printers, OEM Inks, and Media. What can I find for you today?",
    "Great to connect with you! Looking for Epson SureColor printers, UltraChrome inks, or fine art canvas rolls today? 🖨️",
    "Welcome to Kepler Tech! How can I assist with your printing equipment, inks, or supplies today?",
    "Glad you reached out! What printers, genuine inks, or media rolls can I help you with today?",
    "Welcome to Kepler Tech! Let me know what printing supplies you need and I'll find the best options for you.",
]


def _get_time_of_day_salutation() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    elif hour < 17:
        return "afternoon"
    else:
        return "evening"


from prompts.persona import get_system_prompt
from services.pre_router import normalize_user_input, detect_multi_intents

SYSTEM_PROMPT = get_system_prompt()

# Matches any variation of a payment link placeholder / mock link the model might invent
PAYMENT_PLACEHOLDER_REGEX = re.compile(
    r'\[\s*(?:insert\s+)?(?:payment\s+|checkout\s+)?link\s*\]|\binsert\s+(?:payment\s+)?link\b|'
    r'\[payment_link\]|https?://[^\s]*?(?:pay|checkout|payment)[^\s]*',
    re.IGNORECASE,
)

# Order/purchase intent phrases stripped out before running a deterministic product search
_INTENT_PHRASES = [
    "tell me details about", "tell me details for", "tell me about", "show me details about",
    "show details for", "show details of", "details of", "details about",
    "i want to order", "i want to buy", "i'd like to order", "i'd like to buy",
    "i would like to order", "i would like to buy", "can i order", "can i get",
    "can i buy", "i need to order", "i need to buy", "please order", "please get",
    "i wanna buy", "i wanna order", "wanna buy", "wanna order",
    "i want", "order me", "get me", "give me", "i need", "wanna",
    "hi kepler", "kepler", "do you have", "is there", "any", "left",
    "available", "please", "can you check", "how much is", "price of", "cost of",
]


def get_system_context(session_id: str) -> str:
    lead = Lead.get_by_session(session_id)
    session = ChatSession.get_or_create(session_id)

    facts = []
    if lead:
        if lead.get("name"):
            facts.append(f"Customer Name: {lead['name']}")
        if lead.get("contact"):
            facts.append(f"Customer Contact: {lead['contact']}")
        if lead.get("needs"):
            facts.append(f"Customer Needs: {lead['needs']}")
        if lead.get("budget"):
            facts.append(f"Customer Budget: {lead['budget']}")

    context_str = ""
    if facts:
        context_str = "\n[Current Customer Profile Context - Use this information naturally instead of re-asking]:\n" + "\n".join(facts)

    if lead and lead.get("name") and lead.get("contact"):
        context_str += (
            "\n[🚨 STOP — DO NOT ASK FOR CONTACT DETAILS AGAIN 🚨]"
            f"\nThis customer is FULLY QUALIFIED. Name = '{lead['name']}', Contact = '{lead['contact']}'."
            "\nYOU MUST NOT ask for their name, phone number, contact, or any personal details again."
            "\nYou already have everything. Proceed directly to confirming the order and calling checkout_cart/create_order."
        )

    last_search_result = ""
    has_search = False
    for msg in reversed(session.get("messages", [])):
        if msg.get("role") == "tool" and msg.get("name") in ["search_products", "get_printer_consumables"]:
            last_search_result = msg.get("content", "")
            has_search = True
            break

    if last_search_result and "no products found" not in last_search_result.lower():
        trimmed = last_search_result[:2500]
        context_str += f"\n\n[Active Product Inventory / Consumables — ONLY quote data from here for stock/price/availability]:\n{trimmed}"

    return context_str


def _deterministic_product_prefetch(session_id: str, user_message_text: str) -> bool:
    """If the message clearly looks like a product question, pre-fetch search
    results and inject them into history so the model never has to invent facts."""
    is_product_question = looks_like_product_question(user_message_text)
    if not is_product_question:
        return False

    clean_q = user_message_text.lower()
    
    # If the router explicitly detected a get_printer_consumables request
    if clean_q.startswith("get_printer_consumables for "):
        printer_term = user_message_text[len("get_printer_consumables for "):].strip()
        from tools.handlers import get_printer_consumables
        print(f"[{session_id}] Deterministic Router: Pre-fetching get_printer_consumables for '{printer_term}'")
        tool_result = get_printer_consumables(printer_term)
        virtual_tool_call = [{"function": {"name": "get_printer_consumables", "arguments": {"printer_query": printer_term}}}]
        ChatSession.add_message(session_id, "assistant", "", tool_calls=virtual_tool_call)
        ChatSession.add_message(session_id, "tool", str(tool_result), name="get_printer_consumables")
        return True

    clean_q = re.sub(r'^(?:what\s+is\s+the\s+(?:price|cost)\s+(?:of|for)|how\s+much\s+is\s+(?:the)?|tell\s+me\s+the\s+price\s+of)\s+', '', clean_q, flags=re.IGNORECASE).strip()
    for prefix in _INTENT_PHRASES:
        clean_q = clean_q.replace(prefix, "")
    clean_q = re.sub(r'^\s*\d+\s+', '', clean_q)
    clean_q = clean_q.strip("?,. ()") or user_message_text

    print(f"[{session_id}] Deterministic Router: Pre-fetching search_products for query '{clean_q}'")
    tool_result = search_products(clean_q)

    virtual_tool_call = [{"function": {"name": "search_products", "arguments": {"query": clean_q}}}]
    ChatSession.add_message(session_id, "assistant", "", tool_calls=virtual_tool_call)
    ChatSession.add_message(session_id, "tool", str(tool_result), name="search_products")
    return True


def _call_model(messages):
    try:
        response_json = chat_completion(messages, tools=OLLAMA_TOOLS, temperature=0.75)
        return response_json.get("message", {})
    except OllamaError as e:
        print(f"Ollama connection error: {e}")
        return {"role": "assistant", "content": "", "_connection_error": True}


def _manual_parse_tool_call(content_text: str):
    """Fallback for models that emit a tool call as raw JSON text instead of
    using the tools API field. Returns (tool_calls, cleaned_text) or (None, content_text)."""
    cleaned = content_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```[a-zA-Z]*\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()

    if not (cleaned.startswith("{") or "arguments" in cleaned or "name" in cleaned or "search_products" in cleaned or "get_printer_consumables" in cleaned):
        return None, content_text

    try:
        # Check natural language tool call phrases (e.g. "Let's call search_products with query '...'")
        nl_match = re.search(r'(?:call|run|execute)\s+(search_products|get_printer_consumables|recommend_products|get_price|check_stock)\s+(?:with\s+query\s+|for\s+)?["\']([^"\']+)["\']', cleaned, re.IGNORECASE)
        if nl_match:
            fn_name = nl_match.group(1)
            arg_val = nl_match.group(2)
            arg_key = "printer_query" if fn_name == "get_printer_consumables" else "query"
            return [{"function": {"name": fn_name, "arguments": {arg_key: arg_val}}}], ""

        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
            return None, content_text
        parsed = json.loads(cleaned[start_idx:end_idx + 1])
        if "name" not in parsed:
            return None, content_text
        tool_calls = [{"function": {"name": parsed["name"], "arguments": parsed.get("arguments", {})}}]
        text_content = cleaned[:start_idx].strip()
        return tool_calls, text_content
    except Exception:
        return None, content_text


def _resolve_hallucinated_product_ids(func_args: dict, session_id: str = ""):
    from models.product import Product
    from services.pre_router import extract_last_mentioned_product_from_history
    pid = func_args.get("product_id")
    if pid and not Product.find_by_id(pid):
        # Check if active session recently discussed a known product
        if session_id:
            session = ChatSession.get_or_create(session_id)
            last_prod_name = extract_last_mentioned_product_from_history(session.get("messages", []))
            if last_prod_name:
                found_ctx = Product.search_products(last_prod_name)
                if found_ctx:
                    func_args["product_id"] = found_ctx[0]["_id"]
                    return

        # Fallback to model code or numeric search
        search_term = pid.replace("_", " ").replace("-", " ")
        found = Product.search_products(search_term)
        if found:
            func_args["product_id"] = found[0]["_id"]
        else:
            # Fallback to general product search
            import re
            m = re.search(r'(p9500|p7500|p9000|p20000|p8000|p6000|p5000|cx02|cx-02|cz01|cz-01|t3200|t5200|t7200)', pid, re.IGNORECASE)
            if m:
                found_m = Product.search_products(m.group(1))
                if found_m:
                    func_args["product_id"] = found_m[0]["_id"]

    for item in func_args.get("items", []):
        pid = item.get("product_id")
        if pid and not Product.find_by_id(pid):
            search_term = pid.replace("_", " ").replace("-", " ")
            found = Product.search_products(search_term)
            if found:
                item["product_id"] = found[0]["_id"]


def validate_tool_arguments(func_name: str, args: dict) -> tuple[bool, str]:
    schemas = {
        "search_products": {"required": ["query"], "types": {"query": str, "tags": list}},
        "get_printer_consumables": {"required": ["printer_query"], "types": {"printer_query": str}},
        "check_stock": {"required": ["product_id"], "types": {"product_id": str}},
        "get_price": {"required": ["product_id"], "types": {"product_id": str, "qty": int}},
        "get_product_specs": {"required": ["product_id"], "types": {"product_id": str}},
        "scrape_kepler_website": {"required": ["query_or_url"], "types": {"query_or_url": str}},
        "get_shipping_info": {"required": [], "types": {"emirate_or_city": str}},
        "get_warranty_and_support": {"required": [], "types": {"product_query": str}},
        "track_order": {"required": ["order_or_session_id"], "types": {"order_or_session_id": str}},
        "recommend_products": {"required": [], "types": {"context": str}},
        "add_to_cart": {"required": ["session_id", "product_id"], "types": {"session_id": str, "product_id": str, "quantity": int}},
        "view_cart": {"required": ["session_id"], "types": {"session_id": str}},
        "remove_from_cart": {"required": ["session_id", "product_id"], "types": {"session_id": str, "product_id": str}},
        "checkout_cart": {"required": ["session_id", "customer_name", "customer_contact"], "types": {"session_id": str, "customer_name": str, "customer_contact": str}},
        "create_lead": {"required": ["session_id"], "types": {"session_id": str, "name": str, "contact": str, "needs": str, "budget": str}},
        "create_order": {"required": ["session_id", "items", "customer_name", "customer_contact"], "types": {"session_id": str, "items": list, "customer_name": str, "customer_contact": str}},
        "generate_payment_link": {"required": ["order_id"], "types": {"order_id": str}},
        "escalate_to_human": {"required": ["session_id", "reason"], "types": {"session_id": str, "reason": str}},
    }
    
    if func_name not in schemas:
        return False, f"Unknown tool '{func_name}'"
        
    schema = schemas[func_name]
    
    # 1. Check required parameters
    for req in schema["required"]:
        if req not in args or args[req] is None:
            return False, f"Missing required parameter '{req}' for tool '{func_name}'"
            
    # 2. Check types
    for key, val in args.items():
        if key in schema["types"]:
            expected_type = schema["types"][key]
            if expected_type == int:
                try:
                    args[key] = int(val)
                except (ValueError, TypeError):
                    return False, f"Parameter '{key}' must be an integer, got {type(val).__name__}"
            elif expected_type == str:
                if not isinstance(val, str):
                    args[key] = str(val)
            elif expected_type == list:
                if not isinstance(val, list):
                    return False, f"Parameter '{key}' must be a list, got {type(val).__name__}"
                    
    # Special nested validation for create_order items
    if func_name == "create_order":
        items = args.get("items", [])
        if not isinstance(items, list):
            return False, "Parameter 'items' must be a list"
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                return False, f"Item at index {idx} in 'items' list must be an object"
            if "product_id" not in item or "quantity" not in item:
                return False, f"Item at index {idx} must contain 'product_id' and 'quantity'"
            try:
                item["quantity"] = int(item["quantity"])
            except (ValueError, TypeError):
                return False, f"Item quantity at index {idx} must be an integer"
                
    return True, ""


def _execute_tool_call(session_id, tool_call, forced_payment_link_holder):
    func_name = tool_call["function"]["name"]
    func_args = dict(tool_call["function"]["arguments"])

    if func_name in ("create_lead", "create_order", "checkout_cart", "escalate_to_human", "add_to_cart", "view_cart", "remove_from_cart"):
        func_args["session_id"] = session_id

    _resolve_hallucinated_product_ids(func_args, session_id=session_id)

    # Validate schema
    is_valid, err_msg = validate_tool_arguments(func_name, func_args)
    if not is_valid:
        print(f"[{session_id}] Tool validation failed: {err_msg}")
        tool_result = f"Error: Tool argument validation failed. {err_msg}"
        ChatSession.add_message(session_id, "tool", tool_result, name=func_name)
        return {"role": "tool", "content": tool_result, "name": func_name}

    print(f"[{session_id}] Calling tool: {func_name} with args: {func_args}")

    # Track lead scoring actions
    if func_name == "add_to_cart":
        Lead.increment_score(session_id, 10, "cart_add")
    elif func_name in ("search_products", "recommend_products", "get_price", "check_stock"):
        Lead.increment_score(session_id, 5, "price_or_search_check")
    elif func_name in ("checkout_cart", "create_order"):
        Lead.increment_score(session_id, 20, "checkout_started")

    tool_func = TOOL_MAP.get(func_name)
    try:
        tool_result = tool_func(**func_args) if tool_func else f"Error: Tool '{func_name}' is not registered."
    except Exception as ex:
        tool_result = f"Error executing tool: {ex}"

    if func_name in ("create_order", "checkout_cart") and "/checkout/" in str(tool_result):
        link_match = re.search(r'(/checkout/SO-[A-Z0-9]+)', str(tool_result))
        if link_match:
            forced_payment_link_holder["link"] = link_match.group(1)
            print(f"[{session_id}] Captured payment link for forced injection: {forced_payment_link_holder['link']}")

    ChatSession.add_message(session_id, "tool", str(tool_result), name=func_name)
    return {"role": "tool", "content": str(tool_result), "name": func_name}


def ensure_payment_link(session_id, content, channel="web"):
    """Self-healing net: replaces any placeholder link text with the real one,
    or refuses to show a placeholder if no order has actually been created yet.

    The `channel` parameter controls how the payment link is rendered:
      - "web"      → HTML button (render_payment_button) for the browser widget
      - "whatsapp" → plain-text link (render_payment_text) — no HTML tags

    NOTE: an existing order for this session is treated as proof the customer
    already gave name+contact (create_order/checkout_cart both enforce that
    before creating the order) — we don't re-check the separate Lead record
    here, since a model that skips create_lead but still calls checkout_cart
    should still get its real payment link, not a bogus "what's your name?".
    """
    try:
        has_placeholder = bool(PAYMENT_PLACEHOLDER_REGEX.search(content))

        # Check for any order created in this session
        session_orders = sorted(
            Order.get_by_session(session_id),
            key=lambda o: str(o.get("created_at", "")),
            reverse=True,
        )
        latest_order = session_orders[0] if session_orders else None

        if has_placeholder and not latest_order:
            lead = Lead.get_by_session(session_id)
            if not lead or not lead.get("name"):
                return "Perfect! To get your order finalized, what is your full name? 😊"
            if not lead.get("contact"):
                return f"Thanks {lead.get('name')}! And what contact number or email address should we put on your invoice? 📱"
        if latest_order:
            link = latest_order.get("payment_link") or f"/checkout/{latest_order.get('_id', '')}"
            if link.startswith("/"):
                from config import Config
                base = (Config.BASE_URL or "").rstrip("/")
                link = f"{base}{link}"
            if has_placeholder:
                new_content = PAYMENT_PLACEHOLDER_REGEX.sub(link, content)
                if new_content != content:
                    content = new_content
                    ChatSession.update_last_assistant_message(session_id, content)

            if link not in content and any(
                w in content.lower() for w in ["order", "created", "pay", "confirm", "completed", "placed"]
            ):
                order_id = latest_order.get("_id", "CONFIRMED")
                if channel == "whatsapp":
                    content += render_payment_text(order_id, link)
                else:
                    content += render_payment_button(order_id, link)
    except Exception as e:
        print(f"Error self-healing payment link: {e}")
    return content


def _ensure_details_in_reply(content: str, session_id: str) -> str:
    try:
        session = ChatSession.get_or_create(session_id)
        
        # If we are in the middle of asking for customer name/contact details, do NOT append cart summaries
        lead = Lead.get_by_session(session_id)
        if not lead or not lead.get("name") or not lead.get("contact"):
            if "what is your full name?" in content.lower() or "number or email address" in content.lower():
                return content

        last_tool_msg = None
        for msg in reversed(session.get("messages", [])):
            if msg.get("role") == "tool" and msg.get("name") in (
                "search_products", "recommend_products", "get_printer_consumables", "get_price", "view_cart", "add_to_cart", "remove_from_cart"
            ):
                last_tool_msg = msg
                break
                
        # Only append tool content if a tool was executed in this turn
        if not last_tool_msg:
            return content

        tool_content = last_tool_msg.get("content", "")
        if not tool_content or "no products found" in tool_content.lower() or "cart is empty" in tool_content.lower():
            return content

        # For get_price tool, verify price/AED figures are present
        if last_tool_msg.get("name") == "get_price":
            has_price = any(c.isdigit() for c in content) and ("aed" in content.lower() or "price" in content.lower() or "cost" in content.lower())
            if not has_price:
                content = content.strip() + "\n\n" + tool_content.strip()
                ChatSession.update_last_assistant_message(session_id, content)
        # For search/recommend/consumables tools, we MUST have the divider to split them into separate cards with buttons
        elif last_tool_msg.get("name") in ("search_products", "recommend_products", "get_printer_consumables"):
            if "━━━━━━━━━━━━━━━━━━━━" not in content and "📦" not in content:
                # Do not re-append if tool_content is already in content (e.g. discovery questions)
                if tool_content.strip() not in content.strip():
                    content = content.strip() + "\n\n" + tool_content.strip()
                    ChatSession.update_last_assistant_message(session_id, content)
        else:
            # For other tools, verify general detail keywords
            has_details = "aed" in content.lower() or "price" in content.lower() or "total" in content.lower()
            if not has_details and "━━━━━━━━━━━━━━━━━━━━" not in content:
                content = content.strip() + "\n\n" + tool_content.strip()
                ChatSession.update_last_assistant_message(session_id, content)
    except Exception as e:
        print(f"Error ensuring details in reply: {e}")
    return content


def format_reply(reply_text: str, inject_personality: bool = True):
    """Formats output text into standardized bubble dictionary response."""
    if not reply_text:
        return []
    
    # Return entire message block intact so multi-card carousels are rendered together in a single carousel track
    return [{"text": reply_text.strip(), "delay": 0.05, "is_product_card": "━━━━━━━━━━━━━━━━━━━━" in reply_text}]


def process_chat_message(session_id: str, user_message_text: str, channel: str = "web", language: str = "English", btn_id: str = ""):
    """Returns chat response bubbles: [{"text": ..., "delay": ...}, ...]"""
    # Check feature flag for deterministic conversation state graph orchestrator
    if getattr(Config, "USE_CONVERSATION_ORCHESTRATOR", False):
        from orchestration.orchestrator import ConversationOrchestrator
        res = ConversationOrchestrator.process_message(session_id, user_message_text, client_type=channel)
        content = res.get("content", "")
        # Record into chat history
        session = ChatSession.get_or_create(session_id)
        ChatSession.add_message(session_id, "user", user_message_text)
        ChatSession.add_message(session_id, "assistant", content)
        
        # Translate if user requested non-English
        if language and language not in ("English", "en", "en-US"):
            content = translate_text(content, language)
        return format_reply(content)

    # Normalize typos and transcribe noise
    normalized_input = normalize_user_input(user_message_text)
    
    # Translate input message to English to support deterministic routing and LLM constraints
    user_message_english = translate_to_english(normalized_input)

    # Multi-intent decomposition check
    intents = detect_multi_intents(user_message_english)
    for intent in intents:
        if intent.get("type") == "TERRITORY_QUERY" and intent.get("territory"):
            Lead.create_or_update_lead(session_id, territory=intent["territory"])

    # Deterministic checkout details collection flow
    lead = Lead.get_by_session(session_id)
    session = ChatSession.get_or_create(session_id)

    # Intercept "Create draft for", "Draft Quotation", "Draft Full Set Quote", "Prepare Quotation" commands to start the drafting wizard
    norm_l = normalized_input.strip().lower()
    is_draft_command = norm_l.startswith("create draft for") or norm_l in ("draft quotation", "draft quote", "prepare quotation", "draft full set quote", "create quotation")
    
    if is_draft_command:
        match = re.search(r'\(([^)]+)\)|for\s+([A-Za-z0-9\-]+)$', user_message_text, re.IGNORECASE)
        prod_id = None
        if match:
            prod_id = match.group(1) or match.group(2)
            prod_id = prod_id.strip()
        else:
            from models.product import Product
            all_prods = Product.get_all_products()
            for p in all_prods:
                if p["_id"].lower() in user_message_text.lower():
                    prod_id = p["_id"]
                    break
                    
        # If no explicit ID in command text, check last discussed product from history
        if not prod_id:
            from services.pre_router import extract_last_mentioned_product_from_history
            from models.product import Product
            last_prod = extract_last_mentioned_product_from_history(session.get("messages", []))
            if last_prod:
                found_p = Product.search_products(last_prod)
                if found_p:
                    prod_id = found_p[0]["_id"]

        if prod_id:
            Cart.clear(session_id)
            Cart.add_item(session_id, prod_id, 1)
            
            # Reset lead name and contact to None to force asking every time
            Lead.create_or_update_lead(session_id, name=None, contact=None)
            lead = Lead.get_by_session(session_id) or {}
            
            if not lead.get("name"):
                reply_text = "Sure! I'd be happy to create a draft quotation for you on Kepler. What is your full name? 😊"
                ChatSession.add_message(session_id, "user", user_message_english, original_content=user_message_text)
                ChatSession.add_message(session_id, "assistant", reply_text)
                return format_reply(reply_text)
            elif not lead.get("contact"):
                reply_text = f"Sure! I'll create a draft quotation for you. Since I already have your name ({lead['name']}), what contact number or email address should we put on your invoice? 📱"
                ChatSession.add_message(session_id, "user", user_message_english, original_content=user_message_text)
                ChatSession.add_message(session_id, "assistant", reply_text)
                return format_reply(reply_text)
            else:
                checkout_reply = checkout_cart(session_id, lead["name"], lead["contact"])
                ChatSession.add_message(session_id, "user", user_message_english, original_content=user_message_text)
                ChatSession.add_message(session_id, "assistant", checkout_reply)
                return format_reply(checkout_reply)
                ChatSession.add_message(session_id, "assistant", checkout_reply)
                return format_reply(checkout_reply)

    # Increment lead score for high interaction
    user_count = len([m for m in session.get("messages", []) if m.get("role") == "user"])
    if user_count >= 5:
        Lead.increment_score(session_id, 5, "message_count_high")
    
    # Get last assistant message text
    last_assistant_text = ""
    for msg in reversed(session.get("messages", [])):
        if msg.get("role") == "assistant":
            last_assistant_text = msg.get("content", "").lower()
            break
            
    cart = Cart.get(session_id)
    cart_has_items = bool(cart and cart.get("items"))

    # Check if the message is a product inquiry or command (must NOT be treated as a customer name)
    is_prod_query = looks_like_product_question(user_message_english) or user_message_english.lower().startswith("tell me details") or user_message_english.lower().startswith("show me")

    if cart_has_items and not is_prod_query:
        if "what is your full name?" in last_assistant_text:
            name_val = user_message_text.strip()
            lead = Lead.create_or_update_lead(session_id, name=name_val)
            reply_text = f"Thanks {name_val}! And what contact number or email address should we put on your invoice? 📱"
            
            ChatSession.add_message(session_id, "user", user_message_english, original_content=user_message_text)
            ChatSession.add_message(session_id, "assistant", reply_text)
            return format_reply(reply_text)
            
        elif "number or email address" in last_assistant_text:
            contact_val = user_message_text.strip()
            lead = Lead.create_or_update_lead(session_id, contact=contact_val)
            
            checkout_reply = checkout_cart(session_id, lead.get("name", "Customer"), contact_val)
            
            ChatSession.add_message(session_id, "user", user_message_english, original_content=user_message_text)
            ChatSession.add_message(session_id, "assistant", checkout_reply)
            return format_reply(checkout_reply)

    # If customer explicitly asks for payment link or to proceed with checkout
    is_checkout_intent = any(k in user_message_english.lower() for k in ["payment link", "pay link", "checkout", "send payment", "proceed to buy", "buy now", "link please", "payment please"])
    if is_checkout_intent:
        cart = Cart.get(session_id)
        if not (cart and cart.get("items")):
            # Extract last discussed product or SKU from session messages
            from services.pre_router import extract_last_mentioned_product_from_history
            from models.product import Product
            last_prod = extract_last_mentioned_product_from_history(session.get("messages", []))
            if last_prod:
                found_p = Product.search_products(last_prod)
                if found_p:
                    Cart.add_item(session_id, found_p[0]["_id"], 1)
            else:
                for m in reversed(session.get("messages", [])):
                    if m.get("role") in ("assistant", "tool"):
                        sku_match = re.search(r'\b(C13T[A-Z0-9]+|C11C[A-Z0-9]+|C12C[A-Z0-9]+|CX2\.[0-9xA-Za-z]+)\b', m.get("content", ""))
                        if sku_match:
                            Cart.add_item(session_id, sku_match.group(1), 1)
                            break
        
        cart = Cart.get(session_id)
        if cart and cart.get("items"):
            lead = Lead.get_by_session(session_id) or {}
            cust_name = lead.get("name") or "Valued Client"
            cust_contact = lead.get("contact") or "+971-50-0000000"
            checkout_reply = checkout_cart(session_id, cust_name, cust_contact)
            ChatSession.add_message(session_id, "user", user_message_english, original_content=user_message_text)
            ChatSession.add_message(session_id, "assistant", checkout_reply)
            return format_reply(checkout_reply)

    # Deterministic greeting for simple hello/hi
    greetings = {
        "hi", "hello", "hey", "hola", "hy", "good morning", "good afternoon",
        "good evening", "greetings", "wassup", "sup", "hi there", "hey there",
        "hello there", "hi kepler", "hey kepler", "hello kepler",
        "hi jishan", "hey jishan", "hello jishan", "hello again", "hi again", "hey again"
    }
    clean_msg = user_message_english.lower().strip("?,. !")
    if clean_msg in greetings:
        lead = Lead.get_by_session(session_id)
        tod = _get_time_of_day_salutation()
        if lead and lead.get("name"):
            greeting_text = f"Hey {lead['name']}! Good {tod}! 🖨️ Welcome to Kepler Tech. What printing equipment, genuine inks, or fine art media can I help you with today?"
        else:
            greeting_text = f"Hello! Welcome to Kepler Tech (Epson Large Format & Citizen Photo Printing Solutions). 🖨️ How can I help you today?"
        
        ChatSession.add_message(session_id, "user", user_message_english, original_content=user_message_text)
        ChatSession.add_message(session_id, "assistant", greeting_text)
        return format_reply(greeting_text)

    from services.pre_router import get_conversational_intercept, resolve_conversational_subject

    # Conversational capability, policy, company info, consumables, and chit-chat intercept
    is_intercepted, intercept_reply = get_conversational_intercept(user_message_english)
    if is_intercepted and intercept_reply:
        reply_translated = translate_text(intercept_reply, language)
        ChatSession.add_message(session_id, "user", user_message_english, original_content=user_message_text)
        ChatSession.add_message(session_id, "assistant", intercept_reply, original_content=reply_translated)
        return format_reply(reply_translated)

    # Needs Discovery & Broad Category Intercept (e.g. "i want to know about printers", "need ink", "paper")
    # Only trigger if we haven't already just asked the discovery question in the previous turn
    from services.discovery_engine import is_broad_query, get_discovery_question
    is_broad, broad_cat = is_broad_query(user_message_english)
    asked_discovery_already = (
        "which printing category" in last_assistant_text or 
        "what type of printing" in last_assistant_text or 
        "what printer model do you have" in last_assistant_text or
        "what document size do you need to scan" in last_assistant_text
    )
    
    if is_broad and broad_cat and not asked_discovery_already:
        discovery_reply = get_discovery_question(broad_cat)
        reply_translated = translate_text(discovery_reply, language)
        ChatSession.add_message(session_id, "user", user_message_english, original_content=user_message_text)
        ChatSession.add_message(session_id, "assistant", discovery_reply, original_content=reply_translated)
        return format_reply(reply_translated)

    # Save user message to session history first
    ChatSession.add_message(session_id, "user", user_message_english, original_content=user_message_text)

    # Context Resolution: Resolve 'send details' / 'that printer' / 'it' to the exact product previously discussed
    resolved_query = resolve_conversational_subject(session_id, user_message_english)
    is_product_question = _deterministic_product_prefetch(session_id, resolved_query)

    save_lead_signals_if_any(session_id, user_message_english)

    forced_payment_link_holder = {"link": None}

    session = ChatSession.get_or_create(session_id)
    context = get_system_context(session_id)

    # Let the LLM run entirely in English context
    messages = [{"role": "system", "content": SYSTEM_PROMPT + context}]
    for msg in session["messages"]:
        entry = {"role": msg["role"], "content": msg["content"]}
        if msg.get("tool_calls"):
            entry["tool_calls"] = msg["tool_calls"]
        if msg.get("name"):
            entry["name"] = msg["name"]
        messages.append(entry)

    tool_called_this_request = is_product_question
    nudged_already = False
    empty_response_count = 0

    for loop_idx in range(Config.AGENT_MAX_LOOPS):
        # Max-turn guard: if the agent is looping indefinitely, fallback to human escalation
        if loop_idx >= 5:
            trouble_english = "I apologize, but I am having trouble completing this request. Let me connect you to a human assistant to help you directly."
            trouble_translated = translate_text(trouble_english, language)
            
            # Escalate the lead to human rep in CRM database
            Lead.create_or_update_lead(session_id, status="escalated")
            
            ChatSession.update_last_assistant_message_content_and_translation(
                session_id, trouble_english, original_content=trouble_translated
            )
            return format_reply(trouble_translated, inject_personality=False)

        assistant_message = _call_model(messages)

        ChatSession.add_message(
            session_id, "assistant", assistant_message.get("content", ""),
            tool_calls=assistant_message.get("tool_calls"),
        )
        messages.append(assistant_message)

        tool_calls = assistant_message.get("tool_calls", [])
        content_text = assistant_message.get("content", "")

        # Strip any leaked role header prefix like 'assistant\n\n' or 'assistant:'
        if content_text:
            content_text = re.sub(r'^(?:assistant|system|bot)\s*[:\n\-]+\s*', '', content_text, flags=re.IGNORECASE).strip()
            # Strip reasoning / scratchpad artifacts (e.g. <think>...</think>, <thought>...</thought>, "But we need to interpret: ...")
            content_text = re.sub(r'<(?:think|thought)>[\s\S]*?</(?:think|thought)>', '', content_text, flags=re.IGNORECASE).strip()
            content_text = re.sub(r'^(?:But\s+we\s+need\s+to\s+interpret|Thinking\s+Process|Scratchpad|Reasoning)\s*:[\s\S]*?(?=\n\n[A-Z]|\n\n[👋📦✨]|Hello|Hi|Sure|Dear|$)', '', content_text, flags=re.IGNORECASE).strip()

        if not tool_calls:
            parsed_calls, cleaned_text = _manual_parse_tool_call(content_text)
            if parsed_calls:
                tool_calls = parsed_calls
                ChatSession.pop_last_message(session_id)
                ChatSession.add_message(session_id, "assistant", cleaned_text, tool_calls=tool_calls)
                content_text = cleaned_text

        if not tool_calls:
            content = content_text
            if not content.strip():
                if assistant_message.get("_connection_error"):
                    # On offline Ollama, provide direct synthesized reply from the latest tool output
                    fresh_sess = ChatSession.get_or_create(session_id)
                    last_tool_msg = None
                    for msg in reversed(fresh_sess.get("messages", [])):
                        if msg.get("role") == "tool" and msg.get("content"):
                            last_tool_msg = msg
                            break
                    if last_tool_msg and last_tool_msg.get("content"):
                        content = last_tool_msg.get("content")
                    else:
                        empty_response_count += 1
                else:
                    empty_response_count += 1

                if not content.strip():
                    if empty_response_count >= 3:
                        trouble_english = "hmm, running into a bit of trouble on my end. let me pass you to someone who can help better!"
                        trouble_translated = translate_text(trouble_english, language)
                        ChatSession.update_last_assistant_message_content_and_translation(
                            session_id, trouble_english, original_content=trouble_translated
                        )
                        return format_reply(
                            trouble_translated,
                            inject_personality=False,
                        )
                    continue

            has_placeholder = bool(PAYMENT_PLACEHOLDER_REGEX.search(content))
            if has_placeholder and not forced_payment_link_holder["link"] and not nudged_already:
                nudged_already = True
                ChatSession.pop_last_message(session_id)
                lead = Lead.get_by_session(session_id)
                lead_hint = f" The customer's name is '{lead.get('name', '')}' and contact is '{lead.get('contact', '')}'." if lead else ""
                messages.append({
                    "role": "system",
                    "content": (
                        "🚨 STOP. You wrote a payment link placeholder but never called checkout_cart/create_order. "
                        f"You MUST call one of those RIGHT NOW with the confirmed item(s), quantity, name, and contact.{lead_hint} "
                        "Do NOT reply with text — call the tool immediately."
                    ),
                })
                continue

            text_says_checking = any(w in content.lower() for w in ["check", "lookup", "look up", "find", "search", "sec"])
            should_nudge = (is_product_question or text_says_checking) and not tool_called_this_request
            if should_nudge and not nudged_already:
                nudged_already = True
                ChatSession.pop_last_message(session_id)
                messages.append({
                    "role": "system",
                    "content": (
                        "You said you would check or search for product details, but did not call any tool. "
                        "You MUST call search_products or recommend_products RIGHT NOW before replying. "
                        "Do not describe or estimate — call the tool to get the real data."
                    ),
                })
                continue

            # Retrieve the most recent tool execution payload in this turn or session
            last_tool_payload = None
            for m in reversed(messages):
                if m.get("role") == "tool" and m.get("content"):
                    last_tool_payload = m.get("content")
                    break

            reply_english = ensure_payment_link(session_id, content, channel=channel)

            # If a product catalog tool was executed in this turn, ensure clean single card carousel output
            if tool_called_this_request and last_tool_payload and ("📦" in last_tool_payload or "💧" in last_tool_payload):
                # If model generated a repetitive markdown table or duplicated card summary, replace with verified card payload
                if "| Model |" in reply_english or "━━━━━━━━━━━━━━━━━━━━" in content:
                    reply_english = last_tool_payload

            reply_english = _ensure_details_in_reply(reply_english, session_id)

            # Response validation & anti-hallucination guard
            from services.response_validator import validate_ai_response

            is_valid, val_reason, sanitized_reply = validate_ai_response(reply_english, last_tool_result=last_tool_payload)
            if not is_valid and not nudged_already:
                nudged_already = True
                ChatSession.pop_last_message(session_id)
                messages.append({
                    "role": "system",
                    "content": (
                        f"🚨 Safety Validator Notice: Your previous output failed safety checks ({val_reason}). "
                        "Please re-formulate your answer concisely using ONLY the exact prices, SKUs, and specifications from the verified tool results, without internal system names, raw JSON, or ungrounded claims."
                    ),
                })
                continue
            
            if sanitized_reply:
                reply_english = sanitized_reply

            reply_translated = translate_text(reply_english, language)
            ChatSession.update_last_assistant_message_content_and_translation(
                session_id, reply_english, original_content=reply_translated
            )
            return format_reply(reply_translated)

        tool_called_this_request = True
        for tool_call in tool_calls:
            tool_msg = _execute_tool_call(session_id, tool_call, forced_payment_link_holder)
            messages.append(tool_msg)
            
            # If product catalog tools were executed and returned rich cards or quotes, return immediately
            if tool_call.get("function", {}).get("name") in ("search_products", "recommend_products", "get_printer_consumables", "get_price") and tool_msg.get("content"):
                card_content = tool_msg.get("content")
                if "📦" in card_content or "💧" in card_content or "AED" in card_content:
                    final_reply = f"{card_content}" if ("📦" in card_content or "💧" in card_content) else f"Here are the price details:\n\n{card_content}"
                    ChatSession.add_message(session_id, "assistant", final_reply)
                    return format_reply(final_reply)

    final_content = "let me check on that for you in a moment."
    if forced_payment_link_holder["link"]:
        final_content = f"Your order is confirmed! Here is your payment link: {forced_payment_link_holder['link']}"
    
    final_content = _ensure_details_in_reply(final_content, session_id)
    final_translated = translate_text(final_content, language)
    ChatSession.update_last_assistant_message_content_and_translation(
        session_id, final_content, original_content=final_translated
    )
    return format_reply(final_translated, inject_personality=False)
