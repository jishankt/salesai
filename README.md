# 🤖 Sales AI — Enterprise WhatsApp Sales Bot & CRM

> An intelligent, multi-lingual WhatsApp AI Sales Agent & CRM platform powered by local LLM (Ollama), voice note synthesis, interactive product catalog cards, live admin messenger, and automated checkout.

---

## ✨ Key Features

### 🗣️ Voice Note Conversations
- **Inbound Audio**: Customers send voice notes — automatically transcribed using Speech Recognition / OpenAI Whisper.
- **Multi-language Support**: English, Malayalam (`ml-IN`), and Arabic (`ar-SA`).
- **Outbound Neural Voice**: The bot replies to voice notes with warm, humanized voice notes synthesized via Microsoft Edge Neural TTS.

### 🛍️ Interactive Product Cards
- WhatsApp cards with **product image headers**, stock counters, and direct **"Add to Cart"** buttons.

### 🛒 Cart Management & Automated Checkout
- Multi-turn shopping cart (`add_to_cart`, `view_cart`, `checkout_cart`).
- Generates itemized checkout links and invoices automatically.

### 📊 Admin Console & Live WhatsApp Messenger (`/admin`)
- **Live WhatsApp Messenger**: View all customer conversations in real-time and send direct replies to WhatsApp as an admin.
- **Lead CRM & Pipeline**: Track leads, stages (*Prospect*, *Qualified*, *Escalated*, *Won*), and budget analysis.
- **Order Management & Stock Control**: View sales orders, total revenue, and update product stock in real time.
- **Full Screen Enterprise UI**: Edge-to-edge dark and light glassmorphic theme.

---

## 🗂️ Project Directory Structure

```
salesai/
├── app.py                    # Main Flask web server, API routes & WhatsApp webhook
├── config.py                 # Environment configuration loader
├── auth.py                   # Admin API key security decorator
├── seed_db.py                # Database seeding script for catalog items
├── products.json             # Product catalog seed data
├── requirements.txt          # Complete Python dependency list
├── .env.example              # Environment variables template
│
├── models/
│   ├── db.py                 # MongoDB driver + JSON memory fallback database
│   ├── product.py            # Product model & stock management
│   ├── lead.py               # CRM lead tracking
│   ├── order.py              # Order processing & validation
│   ├── cart.py               # Session cart management
│   └── chat_session.py       # Multi-turn conversation storage
│
├── services/
│   ├── agent_loop.py         # LLM agent tool-calling loop & self-healing guardrails
│   ├── ollama_client.py      # Local Ollama LLM integration
│   ├── whatsapp.py           # Meta Cloud API message & voice note handlers
│   ├── lead_extraction.py    # Name, contact, & budget extraction regex
│   ├── payment.py            # Payment gateway provider (Mock / Razorpay)
│   └── rendering.py          # HTML receipt & checkout template helpers
│
├── static/                   # CSS stylesheets and frontend JavaScript controllers
│   ├── css/style.css         # Enterprise glassmorphism & responsive theme
│   └── js/
│       ├── app.js            # Customer chat controller
│       └── admin.js          # Admin dashboard & WhatsApp live messenger
│
├── templates/
│   ├── index.html            # Customer chat page
│   ├── admin.html            # Admin dashboard & live messenger
│   └── checkout.html         # Payment receipt page
│
└── tests/                    # Pytest test suite
```

---

## 💻 Terminal Commands & Complete Setup Guide

### 1. Environment Setup (Python Virtual Environment)

Open your terminal in the project directory:

```bash
# Clone the repository (or navigate to directory)
cd c:\Users\DELL\Desktop\salesai

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows (PowerShell / Command Prompt):
.\venv\Scripts\activate

# On macOS / Linux:
source venv/bin/activate
```

---

### 2. Install All Dependencies (`requirements.txt`)

```bash
# Upgrade pip to latest version
python -m pip install --upgrade pip

# Install all required dependencies
pip install -r requirements.txt
```

---

### 3. Environment Configuration (`.env`)

Create your `.env` configuration file from the template:

```bash
# Copy template to .env
cp .env.example .env
```

Edit `.env` with your settings:

```env
# --- Server Config ---
PORT=5000
DEBUG=False
ADMIN_API_KEY=123

# --- LLM Config (Ollama) ---
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:latest
OLLAMA_TIMEOUT_SECONDS=30

# --- Payment Config ---
PAYMENT_PROVIDER=mock      # "mock" or "razorpay"
CURRENCY=AED

# --- Meta WhatsApp Cloud API ---
META_WHATSAPP_TOKEN=your_meta_access_token_here
META_PHONE_NUMBER_ID=1243791782144336
META_WEBHOOK_VERIFY_TOKEN=salesai-verify-123

# --- Public URL & Webhook ---
BASE_URL=https://your-domain.trycloudflare.com

# --- Optional Whisper Audio STT ---
OPENAI_API_KEY=your_openai_api_key_here
```

---

### 4. Seed Product Database

```bash
# Populate initial Epson catalog items into the database
python seed_db.py
```

---

### 5. Start the Application Server

```bash
# Run the Flask Application
python app.py
```

Server URLs:
- **Customer Chat UI**: `http://127.0.0.1:5000/`
- **Admin Dashboard & Live Messenger**: `http://127.0.0.1:5000/admin`

---

### 6. Public HTTPS Webhook Tunnels (WhatsApp Integration)

To connect Meta Cloud API webhooks to your local server, run a public tunnel:

```bash
# Option A: Using Cloudflare Tunnel
cloudflared tunnel --url http://localhost:5000

# Option B: Using ngrok
ngrok http 5000

# Option C: Using localhost.run
ssh -R 80:localhost:5000 localhost.run
```

Set the generated HTTPS URL as your `BASE_URL` in `.env` and set up Meta Webhook:
- **Callback URL**: `https://your-tunnel-domain.com/api/webhook/whatsapp`
- **Verify Token**: `salesai-verify-123`
- **Subscribed Fields**: `messages`

---

### 7. Run Test Suite (`pytest`)

```bash
# Execute unit & integration tests
pytest tests/ -v
```

---

## 📡 API Endpoints Reference

### Public / Customer APIs
- `POST /api/chat`: Send text message to AI sales assistant.
  - Body: `{"session_id": "12345", "message": "Show catalog", "language": "English"}`
- `GET /api/chat/<session_id>`: Get chat history for a user session.
- `GET /api/products`: Retrieve all product catalog items.
- `GET /api/lead/<session_id>`: Retrieve lead status for a customer.
- `GET /api/cart/<session_id>`: Get current items in cart.

### Meta WhatsApp Webhook
- `GET /api/webhook/whatsapp`: Meta webhook verification.
- `POST /api/webhook/whatsapp`: Meta incoming WhatsApp message handler.

### Admin APIs (`X-Admin-Key` required)
- `GET /api/admin/analytics`: Get revenue, conversion rate, orders & leads analytics.
- `GET /api/admin/leads`: Fetch all CRM lead profiles.
- `GET /api/admin/orders`: Fetch all customer orders.
- `GET /api/admin/chats`: Get all active WhatsApp customer chat sessions.
- `POST /api/admin/chats/<session_id>/send`: Send reply from admin directly to customer WhatsApp.
  - Body: `{"message": "Hello from admin"}`
- `POST /api/admin/products`: Add a new product to inventory.
- `PUT /api/admin/products/<id>/stock`: Update product stock count.

---

## 📄 License

Private & Proprietary. Built for Enterprise Sales Automation.
