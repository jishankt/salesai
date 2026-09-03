import os
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Config:
    # --- Core ---
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME = os.getenv("DB_NAME", "sales_ai")
    PORT = int(os.getenv("PORT", 5000))

    # SECURITY: debug defaults to False. Only turn on explicitly for local dev.
    DEBUG = _env_bool("DEBUG", False)

    # --- LLM (Local Ollama / Local Server) ---
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # Local Ollama exclusively
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "")
    
    OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://192.168.0.115:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
    OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
    OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45"))
    AGENT_MAX_LOOPS = int(os.getenv("AGENT_MAX_LOOPS", "6"))

    # --- Admin auth ---
    # Set a real secret in your environment before deploying anywhere public.
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-please")

    # --- Payments ---
    # "mock"  -> generates a local /checkout/<id> page (no real money movement)
    # "razorpay" -> uses Razorpay test/live keys below (requires RAZORPAY_KEY_ID/SECRET)
    PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "mock")
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    CURRENCY = os.getenv("CURRENCY", "AED")

    # --- Notifications ---
    # If set, a POST with the order JSON is sent here whenever an order is created/paid.
    ORDER_WEBHOOK_URL = os.getenv("ORDER_WEBHOOK_URL", "")

    # --- Rate limiting ---
    RATE_LIMIT_CHAT = os.getenv("RATE_LIMIT_CHAT", "20 per minute")

    # --- WhatsApp Meta API ---
    META_WHATSAPP_TOKEN = os.getenv("META_WHATSAPP_TOKEN", "")
    META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")
    META_WEBHOOK_VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "my-secret-verify-token")
    META_APP_SECRET = os.getenv("META_APP_SECRET", "")

    # --- Public base URL ---
    # Used to build absolute payment links for WhatsApp (relative links aren't tappable).
    # Set BASE_URL=https://yourdomain.com in .env before going live.
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")

    # --- OpenAI (Whisper API) ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # --- Kepler ERPNext Integration ---
    KEPLER_BASE_URL = os.getenv("KEPLER_BASE_URL", "https://kepler.printersbay.com")
    KEPLER_API_KEY = os.getenv("KEPLER_API_KEY", "")
    KEPLER_API_SECRET = os.getenv("KEPLER_API_SECRET", "")
    KEPLER_COMPANY = os.getenv("KEPLER_COMPANY", "Kepler")

