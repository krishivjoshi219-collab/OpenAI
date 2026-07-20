# Aster Ops · AI Operations Employee

> **OpenAI Build Week Hackathon Entry** · Track: Work and Productivity  
> Codex Session ID: `019f70f1-c6ee-7243-9897-aadd366e1819`

Aster Ops is a voice-driven AI operations employee for small and medium businesses.
It replaces complex ERP systems and manual spreadsheets with natural-language
workflows: create customers, raise invoices, manage inventory, and get compliance
guidance just by typing or speaking.

---

## Table of Contents

1. [Quick Start — Streamlit Community Cloud](#1-quick-start--streamlit-community-cloud) ← **start here**
2. [Quick Start — Run Locally](#2-quick-start--run-locally)
3. [How Onboarding Works](#3-how-onboarding-works)
4. [Required & Optional Secrets](#4-required--optional-secrets)
5. [Feature Overview](#5-feature-overview)
6. [Architecture](#6-architecture)
7. [Running the Test Suite](#7-running-the-test-suite)
8. [Codex Collaboration History](#8-codex-collaboration-history)

---

## 1. Quick Start — Streamlit Community Cloud

This is the recommended way to run Aster Ops publicly without managing a server.

### Step 1 · Fork the repository

Click **Fork** on GitHub. Your fork will be the source Streamlit Cloud deploys from.

### Step 2 · Create a Streamlit Cloud account

Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.

### Step 3 · Deploy the app

1. Click **New app**.
2. Set **Repository** to your fork (`your-username/OpenAI`).
3. Set **Branch** to `main`.
4. Set **Main file path** to `app/ui/streamlit_app.py`.
5. Click **Deploy**.

### Step 4 · Add secrets

While the app is deploying (or after it's up), open **App settings → Secrets** and
paste in the following block.  Replace placeholder values with your real keys.

```toml
# ── Required for AI features ──────────────────────────────────────────────────
GROQ_API_KEY = "gsk_..."          # https://console.groq.com
AI_PROVIDER  = "groq"             # groq | openai | gemini

# ── Optional: switch AI model ─────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"   # default, change if needed

# ── Optional: OpenAI instead of Groq ─────────────────────────────────────────
# AI_PROVIDER   = "openai"
# OPENAI_API_KEY = "sk-..."
# OPENAI_MODEL  = "gpt-4o"

# ── Optional: Telegram daily summaries ───────────────────────────────────────
# TELEGRAM_BOT_TOKEN = "..."
# TELEGRAM_CHAT_ID   = "..."

# ── Optional: PostgreSQL (defaults to SQLite if omitted) ─────────────────────
# DATABASE_URL = "postgresql+psycopg://user:pass@host/dbname"
```

**Where to get a free Groq API key:** [console.groq.com](https://console.groq.com) →
sign up for free → Create API Key.

### Step 5 · Open the app

Streamlit Cloud shows a URL like `https://your-app.streamlit.app`.  Open it and
follow the [onboarding flow](#3-how-onboarding-works).

---

## 2. Quick Start — Run Locally

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11 or 3.12 |
| pip | latest (`pip install -U pip`) |

### Step 1 · Clone the repo

```bash
git clone https://github.com/krishivjoshi219-collab/OpenAI.git
cd OpenAI
```

### Step 2 · Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 · Configure environment variables

Copy the example file and fill in your keys:

```bash
cp .env.example .env        # if .env.example exists
# — or — create .env manually:
```

```env
# Minimum required
GROQ_API_KEY=gsk_...
AI_PROVIDER=groq

# Optional
GROQ_MODEL=llama-3.3-70b-versatile
DATABASE_URL=sqlite:///aster_ops.db
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

### Step 4 · Run database migrations

```bash
PYTHONPATH=. alembic upgrade head
```

### Step 5 · Start the app

```bash
PYTHONPATH=. streamlit run app/ui/streamlit_app.py
```

The app opens at [http://localhost:8501](http://localhost:8501).

---

## 3. How Onboarding Works

Onboarding takes about two minutes and has four steps.

### Step 1 · Create your workspace

Enter your business name, contact email, operating currency, and team size.
You can also **say your business name** with the voice recorder (English or Hindi).

### Step 2 · Import your existing data *(optional)*

Upload a **PDF** or **CSV** file.  You can also skip this entirely and add data
manually later.

#### Importing a PDF

Drop any business PDF — an invoice, a product catalogue, a customer report.
The AI reads the full text, figures out what type of data it contains
(invoices / customers / products / stock), and returns structured rows for you
to review.

> **Tip:** The AI works on text-layer PDFs.  If your PDF is a scanned image
> without OCR text, export from your source system as CSV instead.

#### Importing a CSV

Aster Ops accepts CSV exports from any tool.  Column names are mapped
fuzzily — `"customer_name"`, `"client"`, `"buyer"` all map to the customer
name field, so you don't need to rename headers.

Supported import types:

| Type | What it imports |
|------|----------------|
| **Invoices** | invoice number, customer, amount, status, dates |
| **Customers** | name, email, phone, billing address |
| **Products** | name, SKU, unit price, cost price, description |
| **Stock** | SKU, quantity on hand, reorder level |

### Step 3 · Review and confirm

Every extracted row is shown in an editable table before anything is saved.
Edit cells, remove rows, or add new ones — then click **Save to workspace**.

### Step 4 · You're all set

Your workspace is ready.  Go to the **Business Dashboard** for a live overview,
or start issuing **AI Commands**.

---

## 4. Required & Optional Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `GROQ_API_KEY` | **Yes** (if using Groq) | Get one free at [console.groq.com](https://console.groq.com) |
| `AI_PROVIDER` | No | `groq` (default) · `openai` · `gemini` |
| `GROQ_MODEL` | No | Default: `llama-3.3-70b-versatile` |
| `OPENAI_API_KEY` | Only if `AI_PROVIDER=openai` | [platform.openai.com](https://platform.openai.com) |
| `OPENAI_MODEL` | No | Default: `gpt-4o` |
| `GEMINI_API_KEY` | Only if `AI_PROVIDER=gemini` | [ai.google.dev](https://ai.google.dev) |
| `DATABASE_URL` | No | Defaults to `sqlite:///aster_ops.db` |
| `TELEGRAM_BOT_TOKEN` | No | For daily summary notifications |
| `TELEGRAM_CHAT_ID` | No | Paired with the bot token |

On **Streamlit Community Cloud** paste these into **App settings → Secrets** as TOML
(see the example in [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example)).

On **local / server** set them as OS environment variables or in a `.env` file.

---

## 5. Feature Overview

### Onboarding & AI PDF Import
Upload any invoice PDF, product catalogue, or customer list.  The AI extracts
structured rows automatically — no column mapping required.

### Business Dashboard
Live snapshot of unpaid invoices, low-stock products, and open customer balances,
updated on every page load.

### AI Commands (natural language)
Type instructions like:
- *"Create an invoice for Acme Corp for $1,500"*
- *"Add 50 units of SKU-123 to stock"*
- *"Mark invoice INV-042 as paid"*
- *"What's our total outstanding balance?"*

The AI executes the action and shows a confirmation.

### Voice Commands
Record audio directly in the browser.  Groq Whisper transcribes it, and the
same AI command engine runs the instruction.  Works in English and Hindi.

### Business Memory (RAG)
Add operational context the AI retrieves mid-conversation — pricing rules,
supplier terms, customer preferences.

### Government Assistant
Instant guidance on Indian and US compliance requirements — GST, TDS, income tax,
FEMA, and more.

### Telegram Notifications
Send a daily business wrap-up to any Telegram chat with one click.

### Bring Your Own Key (BYOK)
Enter an API key in the sidebar to override the server-level key for your session
— useful for shared deployments.

---

## 6. Architecture

```
app/
├── ai/             # AI provider clients, tool registry, Whisper
├── business/       # Core business engine (customers, products, invoices, stock)
├── database/       # SQLAlchemy models, session factory, Alembic migrations
├── models/         # ORM models and enums
├── onboarding/     # File extraction (CSV + AI PDF) and import service
├── prompts/        # Jinja2 prompt templates per command type
├── ui/
│   ├── components/ # Reusable layout, sidebar, styles, voice input
│   └── pages/      # One file per page (home, dashboard, customers …)
└── config.py       # pydantic-settings configuration
config/settings.py  # Environment variable schema
```

### AI provider stack

```
Streamlit UI
     │
     ▼
AIService (app/ai/service.py)          ← provider-agnostic orchestration
     │
     ├── Groq (llama-3.3-70b-versatile)     via OpenAI-compatible endpoint
     ├── OpenAI (gpt-4o / Responses API)
     └── Gemini (gemini-2.0-flash)           via OpenAI-compatible endpoint
```

### PDF extraction pipeline

```
Uploaded PDF
     │
     ▼  pdfplumber — extract full text
     │
     ▼  Groq / OpenAI — structured JSON extraction prompt
     │
     ▼  AiPdfExtractionProvider._parse_ai_response()
     │
     ▼  ExtractionPreview (reviewable, not yet persisted)
     │
     ▼  st.data_editor — user reviews / edits rows
     │
     ▼  OnboardingImportService.confirm() — database write
```

---

## 7. Running the Test Suite

```bash
PYTHONPATH=. python -m pytest
```

The suite has **22 tests** covering database CRUD, onboarding parsers (CSV + PDF),
RAG retrieval, AI tool-calling, and business-rule validation.

```bash
# Lint
ruff check .

# Type-check
mypy app
```

---

## 8. Codex Collaboration History

### Session ID
`019f70f1-c6ee-7243-9897-aadd366e1819`

This codebase was built in collaboration with OpenAI Codex over one session using
`gpt-5.6-terra`.  Key milestones:

1. **MVP architecture** — SQLAlchemy repository pattern, pydantic-settings config,
   Streamlit multi-page layout.
2. **Onboarding pipeline** — CSV header fuzzy mapping, pdfplumber table extraction,
   AI-powered PDF extraction (any layout), interactive `st.data_editor` review.
3. **Transaction engine** — `ActionLog` with full undo support (reverse stock,
   restore invoice to draft, refund balance).
4. **Bilingual voice input** — Groq Whisper transcription + Hinglish prompt templates.
5. **Telegram wrap-up** — `TelegramBot` client, sidebar dispatch button with
   exception guards.
6. **Streamlit Cloud compatibility** — `_bridge_secrets()` for `st.secrets →
   os.environ`, CSS header fix for sidebar toggle, `_nav_pending` pattern to avoid
   `StreamlitAPIException` on navigation.
