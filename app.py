import re
import logging
import os
import sys

# Ensure backend modules (models, services, tools, prompts) are resolvable
_root = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(_root, "backend")
for _p in (_root, _backend):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("salesai")

from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from auth import require_admin
from models.product import Product
from models.lead import Lead
from models.order import Order
from models.cart import Cart
from models.chat_session import ChatSession
from services.agent_loop import process_chat_message
from services.ollama_client import chat_completion, OllamaError
from services.whatsapp import send_whatsapp_message, mark_read_and_typing, send_whatsapp_buttons, synthesize_text_to_audio_file

app = Flask(
    __name__,
    template_folder="frontend/templates",
    static_folder="frontend/static"
)
app.config.from_object(Config)

limiter = Limiter(get_remote_address, app=app, default_limits=[])

SESSION_ID_RE = re.compile(r'^[A-Za-z0-9_\-]{1,128}$')

# Per-sender lock — prevents race conditions when a customer double-texts.
# Uses a thread-safe BoundedLockManager to avoid unbounded memory growth.
import collections
import threading

class BoundedLockManager:
    """Thread-safe bounded lock cache to prevent memory leaks from inactive senders."""
    def __init__(self, max_locks: int = 500):
        self.max_locks = max_locks
        self._locks = collections.OrderedDict()
        self._manager_lock = threading.Lock()

    def get_lock(self, sender: str) -> threading.Lock:
        with self._manager_lock:
            if sender in self._locks:
                self._locks.move_to_end(sender)
                return self._locks[sender]
            
            # Evict oldest unlocked lock if capacity exceeded
            if len(self._locks) >= self.max_locks:
                for k in list(self._locks.keys()):
                    lock = self._locks[k]
                    if not lock.locked():
                        del self._locks[k]
                        break

            lock = threading.Lock()
            self._locks[sender] = lock
            return lock

_lock_manager = BoundedLockManager(max_locks=500)


def _get_sender_lock(sender: str):
    return _lock_manager.get_lock(sender)


def _valid_session_id(session_id) -> bool:
    return bool(session_id) and bool(SESSION_ID_RE.match(str(session_id)))


# --- Public / customer-facing routes ---------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/widget-demo")
def widget_demo():
    return render_template("widget_demo.html")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def _synthesize_bubble(text, session_id):
    import uuid
    import os
    os.makedirs("static/audio", exist_ok=True)
    uid = uuid.uuid4().hex
    filename = f"reply_{session_id}_{uid}.mp3"
    filepath = os.path.join("static", "audio", filename)
    if synthesize_text_to_audio_file(text, filepath):
        return f"/static/audio/{filename}"
    return None


@app.route("/api/chat", methods=["POST"])
@limiter.limit(Config.RATE_LIMIT_CHAT)
def chat():
    data = request.json or {}
    session_id = data.get("session_id")
    message = data.get("message")
    language = data.get("language", "English")
    voice_reply = data.get("voice_reply", False)

    if not _valid_session_id(session_id):
        return jsonify({"error": "Missing or invalid session_id"}), 400
    if not message or not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Missing message"}), 400
    if len(message) > 2000:
        return jsonify({"error": "Message too long"}), 400

    try:
        response_bubbles = process_chat_message(session_id, message, language=language)
        
        # Always check if we want to synthesize (e.g. if voice_reply is true)
        if voice_reply and response_bubbles:
            first_text_bubble = None
            for bubble in response_bubbles:
                text = bubble.get("text", "")
                if text and "💵 Price:" not in text and "🆔 Product ID:" not in text:
                    first_text_bubble = text
                    break
            if first_text_bubble:
                bot_audio_url = _synthesize_bubble(first_text_bubble, session_id)
                if bot_audio_url:
                    session = ChatSession.get_or_create(session_id)
                    from models.db import save_mem_db, get_collection, USE_IN_MEMORY
                    for msg in reversed(session.get("messages", [])):
                        if msg.get("role") == "assistant":
                            msg["audio_url"] = bot_audio_url
                            if USE_IN_MEMORY:
                                save_mem_db()
                            else:
                                idx = session["messages"].index(msg)
                                get_collection("chat_sessions").update_one(
                                    {"_id": session_id},
                                    {"$set": {f"messages.{idx}.audio_url": bot_audio_url}}
                                )
                            break
                    for bubble in response_bubbles:
                        if bubble.get("text") == first_text_bubble:
                            bubble["audio_url"] = bot_audio_url
                            break
                            
        return jsonify({"bubbles": response_bubbles})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat-audio", methods=["POST"])
@limiter.limit(Config.RATE_LIMIT_CHAT)
def chat_audio():
    session_id = request.form.get("session_id")
    language = request.form.get("language", "English")
    
    if not _valid_session_id(session_id):
        return jsonify({"error": "Missing or invalid session_id"}), 400
        
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
        
    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "Empty audio file"}), 400

    try:
        import uuid
        import os
        os.makedirs("static/audio", exist_ok=True)
        uid = uuid.uuid4().hex
        
        # Save user's uploaded voice file
        customer_filename = f"customer_{session_id}_{uid}.ogg"
        customer_filepath = os.path.join("static", "audio", customer_filename)
        audio_file.save(customer_filepath)
        
        # Read file bytes for transcription
        with open(customer_filepath, "rb") as f:
            audio_bytes = f.read()
            
        from services.whatsapp import transcribe_audio_via_whisper
        transcription = transcribe_audio_via_whisper(audio_bytes)
        
        if not transcription:
            return jsonify({"error": "Could not transcribe audio. Please try speaking clearly or typing."}), 422
            
        # Process transcription
        response_bubbles = process_chat_message(session_id, transcription, language=language)
        
        # Save customer audio_url in session history
        customer_audio_url = f"/static/audio/{customer_filename}"
        session = ChatSession.get_or_create(session_id)
        from models.db import save_mem_db, get_collection, USE_IN_MEMORY
        
        # Attach audio_url to the user's message in session history
        for msg in reversed(session.get("messages", [])):
            if msg.get("role") == "user":
                msg["audio_url"] = customer_audio_url
                if USE_IN_MEMORY:
                    save_mem_db()
                else:
                    idx = session["messages"].index(msg)
                    get_collection("chat_sessions").update_one(
                        {"_id": session_id},
                        {"$set": {f"messages.{idx}.audio_url": customer_audio_url}}
                    )
                break
                
        # Synthesize Jishan's reply
        bot_audio_url = None
        # Find first conversational bubble
        first_text_bubble = None
        if response_bubbles:
            for bubble in response_bubbles:
                text = bubble.get("text", "")
                # Skip product cards / lists
                if text and "💵 Price:" not in text and "🆔 Product ID:" not in text:
                    first_text_bubble = text
                    break
                
        if first_text_bubble:
            bot_audio_url = _synthesize_bubble(first_text_bubble, session_id)
            if bot_audio_url:
                # Attach audio_url to the assistant's message in session history
                for msg in reversed(session.get("messages", [])):
                    if msg.get("role") == "assistant":
                        msg["audio_url"] = bot_audio_url
                        if USE_IN_MEMORY:
                            save_mem_db()
                        else:
                            idx = session["messages"].index(msg)
                            get_collection("chat_sessions").update_one(
                                {"_id": session_id},
                                {"$set": {f"messages.{idx}.audio_url": bot_audio_url}}
                            )
                        break
                        
                # Add audio_url to the bubble returned to the frontend
                for bubble in response_bubbles:
                    if bubble.get("text") == first_text_bubble:
                        bubble["audio_url"] = bot_audio_url
                        break
                        
        return jsonify({
            "transcription": transcription,
            "customer_audio_url": customer_audio_url,
            "bubbles": response_bubbles
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/correct", methods=["POST"])
@limiter.limit(Config.RATE_LIMIT_CHAT)
def correct_text():
    data = request.json or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"corrected": ""})

    try:
        prompt = (
            "You are a transcription correction assistant. Correct any spelling, grammar, "
            "or word errors in the following user message. Keep the message natural, exactly as spoken. "
            "Do NOT add any extra commentary or wrap it in quotes. Do NOT add a period at the end of the sentence. "
            f"Input text: \"{text}\"\n"
            "Corrected text:"
        )
        result = chat_completion([{"role": "user", "content": prompt}], temperature=0.1)
        corrected = result.get("message", {}).get("content", "").strip()
        if (corrected.startswith('"') and corrected.endswith('"')) or (corrected.startswith("'") and corrected.endswith("'")):
            corrected = corrected[1:-1].strip()
        corrected = corrected.rstrip(".")
        return jsonify({"corrected": corrected})
    except OllamaError as e:
        print(f"Correction error: {e}")
        return jsonify({"corrected": text})


@app.route("/api/webhook/whatsapp", methods=["GET", "POST"])
@limiter.limit("60 per minute")
def whatsapp_webhook():
    # --- GET: Meta Webhook Verification ---
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == Config.META_WEBHOOK_VERIFY_TOKEN:
                print("[WhatsApp] Webhook verified successfully!")
                return challenge, 200
            else:
                return "Forbidden", 403
        return "Bad Request", 400

    # --- POST: Incoming WhatsApp Message ---
    if request.method == "POST":
        # Validate X-Hub-Signature-256 if META_APP_SECRET is set
        if Config.META_APP_SECRET:
            signature_header = request.headers.get("X-Hub-Signature-256")
            if not signature_header or not signature_header.startswith("sha256="):
                print("[WhatsApp] Missing or invalid X-Hub-Signature-256 header")
                return "Forbidden", 403
            
            import hmac
            import hashlib
            expected_sig = signature_header.split("sha256=")[1]
            computed_sig = hmac.new(
                Config.META_APP_SECRET.encode("utf-8"),
                request.data,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected_sig, computed_sig):
                print("[WhatsApp] Webhook HMAC signature verification FAILED!")
                return "Unauthorized", 401

        data = request.json or {}
        print(f"[WhatsApp] Incoming Webhook Payload: {data}")
        
        # Parse the Meta WhatsApp Cloud API payload
        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    
                    if not messages:
                        continue
                        
                    for msg in messages:
                        sender_phone = msg.get("from")
                        msg_id = msg.get("id")
                        msg_type = msg.get("type", "")

                        # Deduplicate incoming webhooks
                        if msg_id:
                            if not hasattr(app, 'processed_messages'):
                                app.processed_messages = []
                            if msg_id in app.processed_messages:
                                print(f"[WhatsApp] Skipping duplicate message {msg_id}")
                                continue
                            app.processed_messages.append(msg_id)
                            # Keep queue length capped at 1000 using FIFO
                            if len(app.processed_messages) > 1000:
                                app.processed_messages.pop(0)

                        # --- Unsupported message types (voice, image, sticker, etc.) ---
                        # Reply with a friendly fallback so the bot never goes silent.
                        if msg_type not in ("text", "interactive", "audio"):
                            if sender_phone:
                                print(f"[WhatsApp] Unsupported message type '{msg_type}' from {sender_phone}")
                                send_whatsapp_message(
                                    sender_phone,
                                    "I can only read text and voice messages right now — mind typing that out? 😊",
                                )
                            continue

                        # --- Extract message text from text, interactive button reply, or audio ---
                        message_text = ""
                        btn_id = ""
                        prod_id = ""
                        prod_name = ""
                        voice_mode = False  # True when customer sent a voice note → reply with voice too
                        if msg_type == "text":
                            message_text = msg.get("text", {}).get("body", "").strip()
                        elif msg_type == "audio":
                            audio_obj = msg.get("audio", {})
                            media_id = audio_obj.get("id")
                            if media_id:
                                from services.whatsapp import get_whatsapp_media_url, download_whatsapp_media, transcribe_audio_via_whisper
                                print(f"[WhatsApp] Processing audio message (Media ID: {media_id}) from {sender_phone}")
                                media_url = get_whatsapp_media_url(media_id)
                                if media_url:
                                    audio_bytes = download_whatsapp_media(media_url)
                                    if audio_bytes:
                                        transcription = transcribe_audio_via_whisper(audio_bytes)
                                        if transcription:
                                            message_text = transcription
                                            voice_mode = True  # Customer used voice — reply with voice
                                            print(f"[WhatsApp] Transcribed audio message: {message_text}")
                                
                                if not message_text:
                                    send_whatsapp_message(
                                        sender_phone,
                                        "I couldn't hear that very clearly — could you try repeating or typing it out? 🎙️"
                                    )
                                    return "EVENT_RECEIVED", 200
                        elif msg_type == "interactive":
                            interactive = msg.get("interactive", {})
                            if interactive.get("type") == "button_reply":
                                btn_reply = interactive.get("button_reply", {})
                                btn_id = btn_reply.get("id", "")
                                btn_title = btn_reply.get("title", "").strip()
                                
                                if btn_id.startswith("create_draft_"):
                                    prod_id = btn_id.replace("create_draft_", "")
                                    prod = Product.find_by_id(prod_id)
                                    prod_name = prod["name"] if prod else prod_id
                                    message_text = f"Create draft for {prod_name} ({prod_id})"
                                else:
                                    message_text = btn_title
                                print(f"[WhatsApp] Received button reply '{message_text}' (ID: {btn_id}) from {sender_phone}")

                        # Show read receipt + typing indicator immediately so the
                        # customer isn't staring at a dead chat while Ollama thinks.
                        if msg_id:
                            mark_read_and_typing(msg_id)

                        if sender_phone and message_text:
                            print(f"[WhatsApp] Received message from {sender_phone}: {message_text}")
                            # Record incoming customer message in ChatSession
                            ChatSession.add_message(sender_phone, "user", message_text)
                            
                            # Parse campaign attribution tag if present
                            ref_match = re.search(r'ref_(\w+)', message_text, re.IGNORECASE)
                            source_tag = ref_match.group(1) if ref_match else None
                            
                            # Initialize Lead placeholder if not exists or update campaign source
                            if not Lead.get_by_session(sender_phone):
                                Lead.create_or_update_lead(sender_phone, source=source_tag)
                            elif source_tag:
                                Lead.create_or_update_lead(sender_phone, source=source_tag)
                                print(f"[WhatsApp] Campaign source '{source_tag}' attribution captured for {sender_phone}")
                            
                            import threading
                            import traceback
                            import time

                            # Allow user to clear memory and start fresh
                            if message_text.lower().strip() in ("reset", "restart", "clear"):
                                from models.db import USE_IN_MEMORY, save_mem_db
                                
                                if USE_IN_MEMORY:
                                    session = ChatSession.get_or_create(sender_phone)
                                    session["messages"] = []
                                    from models.db import MEM_DB
                                    MEM_DB["leads"].pop(sender_phone, None)
                                    save_mem_db()
                                else:
                                    ChatSession.get_collection().delete_one({"_id": sender_phone})
                                    Lead.get_collection().delete_one({"_id": sender_phone})
                                    
                                send_whatsapp_message(sender_phone, "Memory cleared! 🧹 Starting a brand new chat. What can I help you with today?")
                                return "EVENT_RECEIVED", 200

                            # --- Fast Rule-Based Bypasses ---
                            # 1. Add to Cart Button Click
                            if msg_type == "interactive" and btn_id.startswith("add_to_cart_"):
                                from tools.handlers import add_to_cart
                                reply_text = add_to_cart(sender_phone, prod_id, 1)
                                send_whatsapp_message(sender_phone, f"✅ Added *{prod_name}* to cart!\n\n{reply_text}")
                                send_whatsapp_buttons(sender_phone, "What would you like to do next?", [
                                    {"id": "btn_catalog", "title": "Product List"},
                                    {"id": "btn_cart", "title": "View Cart"},
                                    {"id": "btn_checkout", "title": "Checkout"}
                                ])
                                return "EVENT_RECEIVED", 200

                            # 2. View Cart Button Click
                            if btn_id == "btn_cart" or message_text.lower().strip() == "view cart":
                                from tools.handlers import view_cart
                                reply_text = view_cart(sender_phone)
                                send_whatsapp_message(sender_phone, reply_text)
                                
                                cart = Cart.get(sender_phone)
                                has_items = bool(cart and cart.get("items"))
                                if has_items:
                                    buttons = [
                                        {"id": "btn_catalog", "title": "Product List"},
                                        {"id": "btn_cart", "title": "View Cart"},
                                        {"id": "btn_checkout", "title": "Checkout"}
                                    ]
                                else:
                                    buttons = [
                                        {"id": "btn_catalog", "title": "Product List"}
                                    ]
                                send_whatsapp_buttons(sender_phone, "What would you like to do next?", buttons)
                                return "EVENT_RECEIVED", 200

                            # 3. Checkout Button Click
                            if btn_id == "btn_checkout" or message_text.lower().strip() == "checkout":
                                cart = Cart.get(sender_phone)
                                if not cart or not cart.get("items"):
                                    send_whatsapp_message(sender_phone, "Your cart is empty! Please add some items to your cart first. 🛒")
                                    return "EVENT_RECEIVED", 200
                                
                                lead = Lead.get_by_session(sender_phone)
                                if not lead or not lead.get("name"):
                                    reply = "Perfect! To get your order finalized, what is your full name? 😊"
                                    ChatSession.add_message(sender_phone, "assistant", reply)
                                    send_whatsapp_message(sender_phone, reply)
                                    return "EVENT_RECEIVED", 200
                                elif not lead.get("contact"):
                                    reply = f"Thanks {lead.get('name')}! And what contact number or email address should we put on your invoice? 📱"
                                    ChatSession.add_message(sender_phone, "assistant", reply)
                                    send_whatsapp_message(sender_phone, reply)
                                    return "EVENT_RECEIVED", 200
                                else:
                                    from tools.handlers import checkout_cart
                                    reply = checkout_cart(sender_phone, lead.get("name"), lead.get("contact"))
                                    send_whatsapp_message(sender_phone, reply)
                                    return "EVENT_RECEIVED", 200

                            # Process the message through our AI agent loop asynchronously.
                            # A per-sender lock ensures double-texts are serialised rather
                            # than running two threads against the same ChatSession at once.
                            def process_and_send(sender, text, use_voice=False):
                                with _get_sender_lock(sender):
                                    try:
                                        with app.app_context():
                                            clean_text = text.lower().strip()
                                            if clean_text in ("product list", "btn_products", "btn_catalog") or btn_id in ("btn_products", "btn_catalog"):
                                                from tools.handlers import recommend_products
                                                response_bubbles = [{"text": recommend_products()}]
                                            else:
                                                response_bubbles = process_chat_message(
                                                    sender, text, channel="whatsapp", btn_id=btn_id
                                                )
                                             # Split bubbles if they contain product card dividers to send them separately
                                            final_bubbles = []
                                            for bubble in response_bubbles:
                                                bubble_text = ""
                                                delay = 0.1
                                                if isinstance(bubble, dict) and "text" in bubble:
                                                    bubble_text = bubble["text"]
                                                    delay = bubble.get("delay", 0.1)
                                                elif isinstance(bubble, str):
                                                    bubble_text = bubble

                                                if not bubble_text:
                                                    continue

                                                if "━━━━━━━━━━━━━━━━━━━━" in bubble_text:
                                                    parts = [p.strip() for p in bubble_text.split("━━━━━━━━━━━━━━━━━━━━") if p.strip()]
                                                    for part in parts:
                                                        final_bubbles.append({
                                                            "text": part,
                                                            "delay": 0.1,
                                                            "is_product_card": True
                                                        })
                                                else:
                                                    final_bubbles.append({
                                                        "text": bubble_text,
                                                        "delay": delay,
                                                        "is_product_card": False
                                                    })

                                            voice_reply_parts = []  # Collect non-product text for voice reply

                                            for idx, bubble in enumerate(final_bubbles):
                                                bubble_text = bubble["text"]
                                                if bubble.get("delay", 0) > 0:
                                                    time.sleep(min(0.2, bubble["delay"]))
                                                
                                                # If it is a product card, extract the ID and send with an individual "Draft Quotation" button!
                                                if bubble.get("is_product_card"):
                                                    id_match = re.search(r'(?:Product ID|ID):\*?\s*`?([A-Z0-9\-]+)`?', bubble_text, re.IGNORECASE)
                                                    if id_match:
                                                        prod_id = id_match.group(1)
                                                        buttons = [
                                                            {"id": f"create_draft_{prod_id}", "title": "Draft Quotation"}
                                                        ]
                                                        prod = Product.find_by_id(prod_id)
                                                        img_url = prod.get("image_url") if prod else None
                                                        if img_url and "auto=format" in img_url:
                                                            img_url = img_url.replace("auto=format", "fm=jpg")
                                                        card_text = f"━━━━━━━━━━━━━━━━━━━━\n{bubble_text}\n━━━━━━━━━━━━━━━━━━━━"
                                                        send_whatsapp_buttons(sender, card_text, buttons, image_url=img_url)
                                                        continue
                                                
                                                # Send regular message bubble (attach main menu buttons to the final message)
                                                if idx == len(final_bubbles) - 1:
                                                    if "estimated budget range" in bubble_text.lower():
                                                        buttons = [
                                                            {"id": "btn_budget_1k", "title": "Under 1K AED"},
                                                            {"id": "btn_budget_5k", "title": "1K - 5K AED"},
                                                            {"id": "btn_budget_5k_plus", "title": "5K+ AED"}
                                                        ]
                                                        send_whatsapp_buttons(sender, bubble_text, buttons)
                                                    else:
                                                        send_whatsapp_message(sender, bubble_text)
                                                else:
                                                    send_whatsapp_message(sender, bubble_text)
                                                
                                                voice_reply_parts.append(bubble_text)

                                            # If customer sent a voice note, reply with a voice note too
                                            if use_voice and voice_reply_parts:
                                                from services.whatsapp import send_whatsapp_voice
                                                # Only speak the first conversational bubble (not product cards)
                                                # _prepare_voice_text() inside send_whatsapp_voice handles
                                                # all cleanup — just pass the raw first reply bubble
                                                first_bubble = voice_reply_parts[0] if voice_reply_parts else ""
                                                if first_bubble:
                                                    print(f"[VoiceReply] Sending humanized voice reply to {sender}")
                                                    send_whatsapp_voice(sender, first_bubble)

                                    except Exception as e:
                                        print(f"[WhatsApp] Async Processing Error: {e}")
                                        traceback.print_exc()

                            # Run in background thread to return 200 OK to Meta instantly
                            threading.Thread(
                                target=process_and_send, args=(sender_phone, message_text), kwargs={"use_voice": voice_mode}, daemon=True
                            ).start()
                                        
        except Exception as e:
            import traceback
            print("[WhatsApp] Error processing webhook:")
            traceback.print_exc()
            
        # Always return 200 OK to Meta so they don't retry the webhook
        return "EVENT_RECEIVED", 200


@app.route("/api/chat/<session_id>", methods=["GET"])
def get_chat_history(session_id):
    if not _valid_session_id(session_id):
        return jsonify({"error": "Invalid session_id"}), 400
    session = ChatSession.get_or_create(session_id)
    messages = []
    for msg in session.get("messages", []):
        if msg["role"] in ("user", "assistant") and msg.get("content"):
            content_trimmed = msg["content"].strip()
            if msg.get("tool_calls") or (content_trimmed.startswith("{") and content_trimmed.endswith("}")):
                continue
            content = msg.get("original_content") or msg["content"]
            messages.append({
                "role": "bot" if msg["role"] == "assistant" else "user",
                "content": content,
                "sender_type": msg.get("sender_type"),
                "audio_url": msg.get("audio_url"),
                "timestamp": msg.get("timestamp")
            })
    return jsonify({"messages": messages})


@app.route("/api/lead/<session_id>", methods=["GET"])
def get_lead(session_id):
    if not _valid_session_id(session_id):
        return jsonify({"error": "Invalid session_id"}), 400
    lead = Lead.get_by_session(session_id)
    if not lead:
        return jsonify({"status": "no_lead", "lead": None})
    lead = dict(lead)
    lead.pop("_id", None)
    return jsonify({"status": "success", "lead": lead})


@app.route("/api/cart/<session_id>", methods=["GET"])
def get_cart(session_id):
    if not _valid_session_id(session_id):
        return jsonify({"error": "Invalid session_id"}), 400
    return jsonify(Cart.to_view(Cart.get(session_id)))


@app.route("/api/products", methods=["GET"])
def get_products():
    products = Product.get_all_products()
    for p in products:
        p["_id"] = str(p["_id"])
    return jsonify(products)


@app.route("/checkout/<order_id>")
def checkout_page(order_id):
    order = Order.get_by_id(order_id)
    if not order:
        return "Order not found", 404
    return render_template("checkout.html", order=order)


@app.route("/api/checkout/<order_id>", methods=["POST"])
@limiter.limit("10 per minute")
def complete_payment(order_id):
    # Security check: Block direct browser completion if running live provider (Razorpay)
    if Config.PAYMENT_PROVIDER.lower() == "razorpay":
        logger.warning(
            "Direct payment completion attempt blocked for order %s because PAYMENT_PROVIDER=razorpay.",
            order_id
        )
        return jsonify({
            "error": "Forbidden. Automatic payment confirmation is managed via Razorpay Webhook signature verification."
        }), 403

    order = Order.get_by_id(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    from services.notifications import notify_order_event
    updated = Order.set_payment_status(order_id, "paid", "completed")
    notify_order_event("order_paid", updated or order)
    return jsonify({"status": "success", "message": "Payment verified successfully!"})


@app.route("/api/webhook/razorpay", methods=["POST"])
@limiter.limit("60 per minute")
def razorpay_webhook():
    from services.payment import verify_razorpay_signature
    from services.notifications import notify_order_event

    signature = request.headers.get("X-Razorpay-Signature", "")
    raw_body = request.get_data()

    if not verify_razorpay_signature(raw_body, signature):
        logger.warning("Razorpay webhook signature verification failed.")
        return jsonify({"error": "Invalid signature"}), 400

    data = request.json or {}
    event = data.get("event")
    logger.info("Razorpay webhook event received: %s", event)

    if event in ("payment_link.paid", "order.paid", "payment.captured"):
        payload = data.get("payload", {})
        entity_data = (
            payload.get("payment_link", {}).get("entity", {}) or
            payload.get("order", {}).get("entity", {}) or
            payload.get("payment", {}).get("entity", {})
        )
        order_id = entity_data.get("reference_id") or entity_data.get("receipt") or entity_data.get("notes", {}).get("order_id")

        if order_id:
            order = Order.get_by_id(order_id)
            if order:
                updated = Order.set_payment_status(order_id, "paid", "completed")
                notify_order_event("order_paid", updated or order)
                logger.info("Order %s marked paid via Razorpay webhook signature verification.", order_id)
                return jsonify({"status": "success", "order_id": order_id}), 200

    return jsonify({"status": "ignored"}), 200


# --- Admin routes (all require X-Admin-Key) ---------------------------------

@app.route("/admin")
def admin_dashboard():
    return render_template("admin.html")


@app.route("/api/admin/leads", methods=["GET"])
@require_admin
def admin_get_leads():
    leads = Lead.get_all()
    for l in leads:
        l.pop("_id", None)
    return jsonify(leads)


@app.route("/api/admin/orders", methods=["GET"])
@require_admin
def admin_get_orders():
    orders = Order.get_all()
    try:
        orders.sort(key=lambda o: str(o.get("created_at", "")), reverse=True)
    except Exception:
        pass
    return jsonify(orders)


@app.route("/api/admin/analytics", methods=["GET"])
@require_admin
def admin_analytics():
    leads = Lead.get_all()
    orders = Order.get_all()
    products = Product.get_all_products()

    total_leads = len(leads)
    qualified_leads = sum(1 for l in leads if l.get("status") == "qualified")
    escalated_leads = sum(1 for l in leads if l.get("status") == "escalated")

    total_orders = len(orders)
    paid_orders = [o for o in orders if o.get("payment_status") == "paid"]
    revenue = sum(o.get("total_amount", 0) for o in paid_orders)
    pending_revenue = sum(o.get("total_amount", 0) for o in orders if o.get("payment_status") != "paid")

    # Order Paid / Conversion Rate percentage
    conversion_rate = round((len(paid_orders) / total_orders) * 100, 1) if total_orders else 0.0

    # Top products by units sold across all orders
    units_sold = {}
    for o in orders:
        for item in o.get("items", []):
            units_sold[item["name"]] = units_sold.get(item["name"], 0) + item.get("quantity", 0)
    top_products = sorted(units_sold.items(), key=lambda kv: kv[1], reverse=True)[:5]

    low_stock = [
        {"name": p["name"], "stock": p["stock"]}
        for p in sorted(products, key=lambda p: p.get("stock", 0))
        if p.get("stock", 0) <= 3
    ][:10]

    return jsonify({
        "leads": {"total": total_leads, "qualified": qualified_leads, "escalated": escalated_leads},
        "orders": {"total": total_orders, "paid": len(paid_orders)},
        "revenue": {"collected": round(revenue, 2), "pending": round(pending_revenue, 2), "currency": Config.CURRENCY},
        "conversion_rate_percent": conversion_rate,
        "top_products": [{"name": n, "units_sold": q} for n, q in top_products],
        "low_stock": low_stock,
        "products": {
            "total": len(products),
            "item_groups": len(set(p.get("item_group") for p in products if p.get("item_group")))
        }
    })


@app.route("/api/admin/products", methods=["POST"])
@require_admin
def admin_add_product():
    data = request.json or {}
    name = data.get("name")
    price = data.get("price")
    stock = data.get("stock")
    description = data.get("description")
    tags = data.get("tags") or []
    product_id = data.get("product_id") or None
    image_url = data.get("image_url") or ""

    if not name or price is None or stock is None:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        prod = Product.insert_product(
            name=name, price=float(price), stock=int(stock),
            description=description or "", tags=tags, product_id=product_id,
            image_url=image_url
        )
        return jsonify({"status": "success", "product": prod}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/products/<product_id>/stock", methods=["PUT"])
@require_admin
def admin_update_stock(product_id):
    data = request.json or {}
    stock = data.get("stock")
    if stock is None:
        return jsonify({"error": "Missing stock value"}), 400

    prod = Product.find_by_id(product_id)
    if not prod:
        return jsonify({"error": "Product not found"}), 404

    try:
        diff = int(stock) - prod["stock"]
        Product.update_stock(product_id, diff)
        return jsonify({"status": "success", "new_stock": int(stock)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/orders/<order_id>/payment", methods=["PUT"])
@require_admin
def admin_toggle_payment(order_id):
    data = request.json or {}
    status = data.get("payment_status")
    if status not in ("paid", "unpaid"):
        return jsonify({"error": "Invalid status"}), 400

    order = Order.get_by_id(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    updated = Order.set_payment_status(order_id, status)
    return jsonify({"status": "success", "payment_status": updated.get("payment_status")})


@app.route("/api/admin/leads/<session_id>/status", methods=["POST"])
@require_admin
def admin_update_lead_status(session_id):
    data = request.json or {}
    status = data.get("status")
    if status not in ("new", "contacted", "qualified", "won", "lost"):
        return jsonify({"error": "Invalid status"}), 400
        
    from models.lead import Lead
    Lead.create_or_update_lead(session_id, status=status)
    return jsonify({"status": "success", "lead_status": status})


@app.route("/api/admin/seed", methods=["POST"])
@require_admin
def seed_database():
    """Reseeds sample Epson products from products.json. Admin-only (was
    unauthenticated /api/seed before — anyone could wipe the catalog)."""
    import json
    try:
        Product.delete_all()
        with open("products.json", "r") as f:
            sample_products = json.load(f)
        for item in sample_products:
            Product.insert_product(
                name=item["name"], price=item["price"], stock=item["stock"],
                description=item["description"], tags=item["tags"], product_id=item.get("_id"),
            )
        return jsonify({"message": f"Database seeded with {len(sample_products)} products."}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/<session_id>", methods=["GET"])
def get_chat_transcript(session_id):
    if not _valid_session_id(session_id):
        return jsonify({"error": "Missing or invalid session_id"}), 400

    session = ChatSession.get_or_create(session_id)
    return jsonify({
        "session_id": session_id,
        "messages": session.get("messages", []),
        "created_at": str(session.get("created_at", ""))
    })


@app.route("/api/admin/chats", methods=["GET"])
@require_admin
def admin_get_all_chats():
    sessions = ChatSession.get_all()
    result = []
    for s in sessions:
        sid = s.get("_id")
        messages = s.get("messages", [])
        last_msg = ""
        last_time = ""
        for m in reversed(messages):
            if m.get("content"):
                last_msg = m.get("content")
                last_time = m.get("timestamp")
                break
        lead = Lead.get_by_session(sid)
        
        # Find primary user intent across all user messages in the session
        user_intent = ""
        user_msgs = [m.get("content", "").lower() for m in messages if m.get("role") in ("user", "human")]
        combined_user_text = " ".join(user_msgs)
        if any(k in combined_user_text for k in ["p9500", "p7500", "p20000", "p9000", "p900", "p5300", "p700", "citizen", "cx-02", "cy-02", "cz01", "printer", "plotter"]):
            user_intent = "printer"
        elif any(k in combined_user_text for k in ["ink", "cartridge", "ultrachrome", "t800"]):
            user_intent = "ink"
        elif any(k in combined_user_text for k in ["canvas", "paper", "media", "roll"]):
            user_intent = "media"
        elif any(k in combined_user_text for k in ["buy", "order", "checkout", "quote", "pay", "payment"]):
            user_intent = "checkout"

        result.append({
            "session_id": sid,
            "name": lead.get("name") if lead else sid,
            "contact": lead.get("contact") if lead else sid,
            "status": lead.get("status") if lead else "prospect",
            "last_message": last_msg,
            "user_intent": user_intent,
            "message_count": len(messages),
            "updated_at": str(last_time) if last_time else ""
        })
    result.sort(key=lambda c: str(c.get("updated_at") or ""), reverse=True)
    return jsonify(result)


@app.route("/api/admin/chats/<session_id>/send", methods=["POST"])
@require_admin
def admin_send_message(session_id):
    data = request.json or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Missing message content"}), 400

    # 1. Store message in chat session as assistant with admin tag
    ChatSession.add_message(session_id, "assistant", f"[Admin]: {message}", sender_type="admin")

    # 2. If session_id is a WhatsApp phone number, deliver via Meta Cloud API
    whatsapp_sent = False
    if session_id and (session_id.isdigit() or session_id.startswith("+")):
        try:
            send_whatsapp_message(session_id, message)
            whatsapp_sent = True
        except Exception as e:
            logger.error("Failed to send WhatsApp message to %s: %s", session_id, e)

    return jsonify({
        "status": "success",
        "session_id": session_id,
        "message": message,
        "whatsapp_sent": whatsapp_sent
    })


@app.route("/api/admin/chats/<session_id>/voice", methods=["POST"])
@require_admin
def admin_send_voice(session_id):
    data = request.json or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Missing voice note text"}), 400

    # 1. Store message in chat session as admin voice note
    ChatSession.add_message(session_id, "assistant", f"[Admin Voice Note]: 🎙️ {text}", sender_type="admin", is_voice=True)

    # 2. Synthesize & send voice note to WhatsApp number via Meta Cloud API
    whatsapp_sent = False
    if session_id and (session_id.isdigit() or session_id.startswith("+")):
        try:
            from services.whatsapp import send_whatsapp_voice
            send_whatsapp_voice(session_id, text)
            whatsapp_sent = True
        except Exception as e:
            logger.error("Failed to send WhatsApp voice note to %s: %s", session_id, e)

    return jsonify({
        "status": "success",
        "session_id": session_id,
        "text": text,
        "whatsapp_sent": whatsapp_sent
    })


def start_cart_recovery_thread():
    import time
    from datetime import datetime, timedelta
    from models.cart import Cart
    from services.whatsapp import send_whatsapp_message
    
    def recovery_worker():
        time.sleep(15)
        print("[Scheduler] Abandoned Cart Recovery thread started.")
        while True:
            try:
                carts = Cart.get_all()
                now = datetime.utcnow()
                for cart in carts:
                    items = cart.get("items", {})
                    if not items:
                        continue
                    
                    if cart.get("recovery_sent"):
                        continue
                        
                    updated_at = cart.get("updated_at")
                    if isinstance(updated_at, str):
                        try:
                            updated_at = datetime.fromisoformat(updated_at.replace("Z", ""))
                        except:
                            updated_at = None
                            
                    if not updated_at:
                        continue
                        
                    # Trigger after 2 hours of inactivity
                    if now - updated_at >= timedelta(hours=2):
                        session_id = cart.get("session_id")
                        if session_id and session_id.isdigit():
                            print(f"[Scheduler] Sending abandoned cart recovery to {session_id}")
                            send_whatsapp_message(session_id, "Still thinking it over? Your cart's saved 🛒\n\nSend 'View Cart' to see your items, or click 'Checkout' below to finalize!")
                            
                            cart["recovery_sent"] = True
                            Cart._save(session_id, cart)
            except Exception as e:
                print(f"[Scheduler] Recovery worker error: {e}")
            time.sleep(60)

    import threading
    threading.Thread(target=recovery_worker, daemon=True).start()

start_cart_recovery_thread()


# ─── Daily Automated Product Availability Sync ──────────────────────────────
def start_daily_availability_sync():
    import threading
    import time
    import json
    import requests
    from bs4 import BeautifulSoup
    from concurrent.futures import ThreadPoolExecutor
    from models.db import MEM_DB, save_mem_db, USE_IN_MEMORY

    def daily_sync_worker():
        # Initial sleep before first routine cycle
        time.sleep(30)
        print("[Scheduler] Daily Product Availability Sync thread initialized.")
        while True:
            try:
                print("[Scheduler] Starting daily live availability sync from Kepler...")
                with open("products.json", "r", encoding="utf-8") as f:
                    products = json.load(f)

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }

                def check_item(p):
                    url = p.get("website_url", "")
                    if url and "keplertechllc.com/product/" in url:
                        try:
                            r = requests.get(url, headers=headers, timeout=5)
                            if r.status_code == 200:
                                html = r.text
                                soup = BeautifulSoup(html, "html.parser")
                                has_out_of_stock = (
                                    soup.find(class_=lambda c: c and "out-of-stock" in c) is not None or
                                    "out of stock" in html.lower() or
                                    "availability: out of stock" in html.lower()
                                )
                                if has_out_of_stock:
                                    p["availability"] = "Out of Stock"
                                    p["stock"] = 0
                                else:
                                    p["availability"] = "In Stock"
                                    if p.get("stock", 0) <= 0:
                                        p["stock"] = 10
                        except Exception:
                            pass
                    return p

                with ThreadPoolExecutor(max_workers=20) as executor:
                    synced = list(executor.map(check_item, products))

                with open("products.json", "w", encoding="utf-8") as f:
                    json.dump(synced, f, indent=2)

                if USE_IN_MEMORY:
                    for item in synced:
                        pid = item["_id"]
                        if pid in MEM_DB["products"]:
                            MEM_DB["products"][pid]["availability"] = item.get("availability", "In Stock")
                            MEM_DB["products"][pid]["stock"] = item.get("stock", 10)
                    save_mem_db()

                print("[Scheduler] Daily availability sync complete and saved successfully.")
            except Exception as err:
                print(f"[Scheduler] Daily sync error: {err}")

            # Run once every 24 hours (86,400 seconds)
            time.sleep(86400)

    threading.Thread(target=daily_sync_worker, daemon=True).start()

start_daily_availability_sync()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
