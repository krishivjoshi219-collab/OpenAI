# AI Operations Employee

A full-stack AI-powered business operations workspace built on Streamlit, OpenAI (and compatible providers), PostgreSQL, and SQLAlchemy. Originally scaffolded for OpenAI Build Week and extended with multi-provider AI, PDF import/export, a live code viewer, and a suite of automated tests.

---

## Features

| Area | What's included |
|---|---|
| **AI commands** | Natural-language business commands executed via tool-calling (create customers, products, invoices, reminders, update inventory) |
| **Multi-provider AI** | Switch between **OpenAI**, **Groq**, and **Google Gemini** with a single env-var — no code changes required |
| **Onboarding imports** | Upload **CSV or PDF** files to seed customers, products, stock levels, or invoices with a pre-save review step |
| **Invoice export** | Download any invoice as **JPG**, **AVIF**, or **PDF** — all rendered with your business branding |
| **Dashboard** | Live snapshot of open invoices, low inventory, and customers with outstanding balances |
| **Business Memory** | Keyword-based RAG store for operational context the AI can retrieve mid-command |
| **Government Assistant** | Structured, source-linked registration and tax guidance for 🇮🇳 India and 🇺🇸 United States |
| **Notifications** | Telegram channel adapter for daily summaries, invoice reminders, low-stock alerts, and approval requests |
| **Odoo integration** | JSON-RPC adapter exposing Odoo customer, invoice, inventory, and activity tools to the AI layer |
| **View Code** | In-app searchable code browser — browse every source file with syntax highlighting and line numbers |
| **22 automated tests** | Covering AI orchestration, onboarding extraction, database layer, notifications, dashboard, government assistant, and Odoo tools |

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| UI | Streamlit (port 5000) |
| AI | OpenAI Responses API · Chat Completions adapter (Groq, Gemini) |
| ORM / DB | SQLAlchemy 2 · Alembic · PostgreSQL (SQLite for tests) |
| PDF generation | ReportLab |
| PDF parsing | pdfplumber |
| Image export | Pillow 12 (JPEG + AVIF native) |
| Config | Pydantic Settings |
| Notifications | Telegram Bot API |

---

## Project layout

```
app/
  ai/               # Provider client factory, Responses API service, Chat Completions adapter
  business/         # BusinessEngine, domain services, Odoo adapter, typed commands
  database/         # Session factory, generic Repository[T], Alembic wiring
  memory/           # Keyword RAG retriever and business-scoped memory CRUD
  models/           # SQLAlchemy ORM models (business, customer, invoice, product, inventory …)
  notifications/    # NotificationService, Telegram channel, contracts
  onboarding/       # CSV + PDF extraction providers, confirmation service
  prompts/          # Version-controlled Jinja2 prompt templates
  services/         # Dashboard, Government assistant, Invoice image/PDF renderers
  ui/
    components/     # Layout, styles, shared widgets, Pendo instrumentation
    pages/          # One module per page (home, onboarding, dashboard, invoices …)
  streamlit_app.py  # Entry point — page registry and routing
config/             # Typed runtime settings (Pydantic BaseSettings)
migrations/         # Alembic migration scripts
tests/              # 22 pytest tests
```

---

## Getting started

### 1. Clone and install

```bash
git clone https://github.com/krishivjoshi219-collab/OpenAI.git
cd OpenAI
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in the values you need:

```bash
cp .env.example .env
```

Minimum required for the app to start (AI features disabled without a key):

```env
DATABASE_URL=postgresql://user:pass@localhost/dbname   # or leave blank for SQLite in tests
```

### 3. Apply database migrations

```bash
alembic upgrade head
```

### 4. Run

```bash
PYTHONPATH=. streamlit run app/ui/streamlit_app.py --server.port 5000
```

---

## AI provider configuration

The app supports three providers. Set `AI_PROVIDER` to switch — no code changes needed.

| Provider | `AI_PROVIDER` value | Required secrets |
|---|---|---|
| OpenAI (default) | `openai` | `OPENAI_API_KEY` |
| Groq | `groq` | `GROQ_API_KEY` |
| Google Gemini | `gemini` | `GEMINI_API_KEY` |

```env
AI_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile        # optional, has a default

# or

AI_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash             # optional, has a default
```

Groq and Gemini are wrapped by `ChatCompletionsClient`, which adapts their Chat Completions-compatible endpoints to the same `ResponsesClient` protocol that `AIService` uses. Conversation history is managed in-process so multi-turn commands work the same across all three providers.

---

## Onboarding imports (CSV and PDF)

The onboarding flow accepts **CSV** and **PDF** files for four import types:

| Import type | Required columns (any alias accepted) |
|---|---|
| Customers | `name` / `customer_name` / `client` · `email` · `phone` · `address` |
| Products | `name` / `product_name` · `sku` / `product_code` / `code` · `unit_price` / `price` / `rate` |
| Stock | `sku` / `product_code` · `quantity_on_hand` / `qty` / `stock` / `inventory` |
| Invoices | `invoice_number` / `number` / `ref` · `customer_name` / `client` / `bill_to` · `total` / `amount` · optional date + status fields |

**PDF extraction** uses `pdfplumber` to locate the largest table across all pages. Column headers are normalised (lowercase, underscores) and matched against an extensive alias list. Malformed or image-only PDFs return a clear warning rather than crashing.

A pre-save review screen shows all extracted records before anything is written to the database.

---

## Invoice export

Every invoice can be downloaded in three formats directly from the Invoices page:

| Format | Details |
|---|---|
| **JPG** | Full-resolution JPEG rendered with Pillow — dark-green branded layout |
| **AVIF** | Smaller AVIF at quality 75, same layout |
| **PDF** | A4 PDF rendered with ReportLab — matching colour palette, table grid, and footer |

All three formats share the same `InvoiceImageData` DTO and produce the same visual design (header band, meta row with status badge, FROM / BILL TO columns, line-items table with alternating rows, right-aligned totals, notes, footer).

---

## AI tool calling

`create_business_ai_service(engine, business_id)` wires the active AI provider to a business-scoped `BusinessEngine`. The model has access to seven tools:

- `create_customer` · `search_customers`
- `create_product` · `search_products`
- `update_inventory`
- `create_reminder`
- `create_invoice`

Each tool call includes a `reason` field so audit logs explain *why* the model chose each action. The tool loop runs up to **8 turns** (configurable via `_MAX_TOOL_TURNS`) before aborting with a clear error.

`AIService.business_command()` requires a strict JSON response (`summary`, `outcome`, `actions`, `next_steps`) and returns an `AIResult` with both the parsed structured output and a per-tool `ActionLogEntry` tuple.

---

## Notifications

`NotificationService` routes business events through replaceable channel adapters:

| Event | Method |
|---|---|
| Daily summary | `send_daily_summary()` |
| Invoice reminder | `send_invoice_reminder()` |
| Low inventory alert | `send_low_inventory_alert()` |
| Approval request | `send_approval_request()` |

`TelegramNotificationChannel` is the initial adapter. Configure it with:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Every delivery returns a `DeliveryReceipt` and is logged as a `business_notification` structured record. Failed targets do not block successful ones.

---

## Government Assistant

Produces structured preparation checklists for **🇮🇳 India** and **🇺🇸 United States** covering:

- Business structure and registration steps
- Required documents
- Tax registration guidance (GST / EIN)
- Employer obligations (if applicable)
- Official first-party source links

All responses include an explicit uncertainty list and a non-legal-advice disclaimer.

---

## Database

The schema is applied via Alembic. Key tables:

`businesses` · `customers` · `products` · `suppliers` · `invoices` · `invoice_items` · `inventory` · `reminders` · `business_memory` · `business_settings`

Every entity uses a UUID primary key and `created_at` / `updated_at` audit timestamps. The generic `Repository[T]` handles add, get, list (paginated), and delete. Callers own their transactions via `session_scope`.

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration after changing models
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

---

## Tests

```bash
pytest                    # run all 22 tests
pytest -v --tb=short      # verbose with short tracebacks
```

| Test file | Coverage |
|---|---|
| `test_ai_service.py` | Structured command format, conversation history, tool execution audit |
| `test_business_engine.py` | Customer/product/invoice/inventory CRUD via engine |
| `test_business_memory.py` | Memory CRUD scoping, keyword retriever protocol |
| `test_dashboard.py` | Snapshot isolation across businesses |
| `test_database_layer.py` | UUID persistence, repository read/write |
| `test_government_assistant.py` | India GST/Udyam guidance, US EIN/sales-tax adaptation |
| `test_notifications.py` | Event formatting, channel routing, failure receipts, Telegram adapter |
| `test_odoo_integration.py` | Service-to-model mapping, tool exposure, JSON-RPC auth flow |
| `test_onboarding_imports.py` | CSV preview, DB persistence, corrupt-PDF warning, unsupported-format rejection |
| `test_smoke.py` | Settings load with SQLite |

---

## Environment variables reference

```env
# Database
DATABASE_URL=postgresql://...          # Replit injects this automatically

# AI provider (pick one)
AI_PROVIDER=openai                     # openai | groq | gemini  (default: openai)
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash

# Notifications
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Odoo (optional)
ODOO_URL=https://your-instance.odoo.com
ODOO_DATABASE=your-db
ODOO_USERNAME=admin
ODOO_API_KEY=...

# App
SESSION_SECRET=...                     # Used by Streamlit session state signing
```

---

## Quality checks

```bash
ruff check .
mypy app
pytest
```
