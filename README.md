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

---

## Core System Architecture & Components

The backend now exposes a production-grade infrastructure layer (`app/backend/`) designed for observability, resilience, and startup safety.

### Metrics Collection (`app/backend/metrics.py`)

A thread-safe `MetricsCollector` registry manages two metric primitives:

- **Counter** — monotonically increasing values (e.g. `notifications_sent_total`).
- **Histogram** — distributions of observed latencies or sizes (e.g. `ai_tool_call_duration_seconds`).

Both are label-aware and safe for concurrent access. A process-wide `metrics` singleton is exported for one-line instrumentation:

```python
from app.backend.metrics import metrics

counter = metrics.counter("ai_commands_total", provider="openai")
counter.inc()

histogram = metrics.histogram("tool_call_duration_seconds", tool="create_invoice")
histogram.observe(0.42)
```

`snapshot()` returns a serialisable dict suitable for Prometheus pull or JSON dump.

### Circuit Breaker (`app/backend/circuit_breaker.py`)

`CircuitBreaker` protects every external dependency (Odoo JSON-RPC, Telegram Bot API, future LLM providers) from cascading failures. It operates in three states:

| State | Behaviour |
|---|---|
| `CLOSED` | Calls pass through. Failures increment a counter. |
| `OPEN` | Calls fail immediately with `CircuitOpenError`. After `recovery_timeout` seconds the breaker transitions to `HALF_OPEN`. |
| `HALF_OPEN` | A limited number of probe calls (`half_open_max_calls`) are allowed through. Success closes the breaker; failure re-opens it. |

Configuration is explicit per-instance:

```python
from app.backend.circuit_breaker import CircuitBreaker

breaker = CircuitBreaker(
    name="odoo_jsonrpc",
    failure_threshold=5,
    recovery_timeout=30.0,
    half_open_max_calls=3,
)

result = breaker.call(gateway.execute, model, method, args, kwargs)
```

All state transitions emit structured log entries.

### Health Checks (`app/backend/health.py`)

`HealthCheck` is a pluggable registry of component probes. Each probe returns a `ComponentHealth` with a `HealthStatus` (`healthy`, `degraded`, `unhealthy`), optional latency, and a human-readable message.

```python
from app.backend.health import HealthCheck, HealthStatus

health = HealthCheck()
health.register("database", lambda: ComponentHealth(...))
health.register("odoo", lambda: ComponentHealth(...))

status = health.check()  # aggregate dict
```

Aggregate logic: one `unhealthy` component marks the whole system `unhealthy`; `degraded` marks the system `degraded`; otherwise `healthy`.

### Logging & Configuration (`app/backend/logging.py`, `app/backend/config.py`)

**Logging** supports two formatters out of the box:

- **Structured JSON** — every record includes `timestamp`, `level`, `logger`, `message`, `module`, `function`, `line`, and optional `exception` / `extra` fields. Ideal for ELK / Datadog ingestion.
- **Human-readable** — colour-friendly console format for local development.

```python
from app.backend.logging import configure_logging, get_logger

configure_logging("INFO", json_format=True)
logger = get_logger("notifications.telegram")
```

**Configuration validation** runs at startup and produces a `ValidationResult` per field:

- Validates `DATABASE_URL` presence.
- Validates the active AI provider key (`OPENAI_API_KEY`, `GROQ_API_KEY`, or `GEMINI_API_KEY`).
- Validates Telegram consistency (`TELEGRAM_BOT_TOKEN` ↔ `TELEGRAM_CHAT_ID`).
- Validates Odoo completeness (`ODOO_URL` + `ODOO_DATABASE` + `ODOO_USERNAME` + `ODOO_API_KEY`).

Raising `SettingsValidationError` on failure prevents the app from starting with a half-configured environment.

---

## Advanced Frontend Interfaces & Components

The Streamlit UI layer (`app/ui/`) now uses a component architecture with layout-independent animation primitives.

### Toast Notification Container (`app/ui/components/toast.py`)

A fixed-position toast engine injected once per page load via `inject_toast_container()`. Toasts slide in from the right, auto-dismiss after a configurable duration, and slide out on removal.

```python
from app.ui.components.toast import render_toast

render_toast(
    title="Invoice created",
    message="INV-2026-001 has been saved.",
    icon="✅",
    duration=3.5,
)
```

Implementation notes:
- Uses a single `#toast-root` container in the DOM.
- Each toast gets a unique ID and a self-removing `<script>` block.
- CSS animations (`slideInRight`, `slideOutRight`) are GPU-composited for smooth 60fps motion.
- Pointer-events are disabled on the container and enabled on individual toasts to avoid blocking page interaction.

### Skeleton Loaders (`app/ui/components/widgets.py`)

Two shimmer placeholders ground long-running operations (LLM tool loops, database queries, PDF rendering):

- `render_skeleton_metric(count=4)` — four metric-card skeletons for dashboard loading states.
- `render_skeleton_card()` — a single content-card skeleton for detail views.

Shimmer is implemented via a CSS `linear-gradient` animation (`shimmer` keyframes) that sweeps a lighter band across a neutral base colour. No JavaScript or image assets required.

### Micro-Interaction Animations (`app/ui/components/styles.py`)

All animations are CSS-first, hardware-accelerated, and respect `prefers-reduced-motion` via standard media queries where applicable.

| Animation | Target | Trigger |
|---|---|---|
| `pageFadeIn` | Page header, section titles, cards | Initial page render |
| `float` | Empty-state icon | Continuous |
| `shimmer` | Skeleton cards | Loading state |
| `spin` | Custom spinner | Processing state |
| `pulse-ring` | Voice recording indicator | Active recording |
| `slideInRight` / `slideOutRight` | Toast notifications | Show / dismiss |

Card surfaces use `box-shadow` and `transform: translateY(-2px)` on hover to create a tactile lift effect. Buttons use `:active` state to collapse back to baseline, simulating physical press. Sidebar nav items slide 2px right on hover. Badges scale to 1.05× on hover. Form inputs gain a forest-green focus ring (`box-shadow: 0 0 0 3px rgba(18,91,72,.12)`).

---

## Integration with Codex Cloud Engine

This project is actively developed through the **OpenAI Codex CLI** development loop.

- **Codex Session ID:** `019f7498-46ec-7831-a552-1fa39a9f4525`
- **Model:** `gpt-4.1` (free tier)
- **Model Context Protocol (MCP):** Linked tooling surfaces for filesystem reads, Bash execution, and web search are wired into the Codex runtime.

The development workflow is terminal-native:

1. **Analyze** — Codex reads the full `app/` tree via MCP filesystem tools, identifies multi-step action flows, data-model inconsistencies, and UI gaps.
2. **Patch** — Edits are applied directly to the workspace (`app/ai/`, `app/business/`, `app/ui/`, `app/notifications/`) with atomic `Edit` operations.
3. **Deploy** — Bash tooling runs `py_compile` checks, `pytest` suites, and lint gates (`ruff`, `mypy`) before marking a turn complete.
4. **Log** — Every Codex turn emits execution blocks capturing the prompt, tool calls, and diff summaries. This session's provenance is traceable through the Codex Session ID above.

This loop systematically analysed and patched the entire multi-step business logic matrix — from the Responses API adapter's conversation-history fallback to the Odoo circuit-breaker wrapper — without leaving the terminal.

---

## The Architectural Edge

### vs. Standard ChatGPT (Web / API)

| Limitation | ChatGPT Web / API | Aster Ops AI Employee |
|---|---|---|
| **Execution memory** | Ephemeral per-session; lost on refresh or timeout | Persistent `ConversationState` with `previous_response_id` fallback + `conversation_messages` cache |
| **Multi-turn reliability** | Context drift after 4K–8K tokens; no server-side continuation | `ChatCompletionsClient` adapter reconstructs full history from `state.messages` when `previous_response_id` cache misses |
| **Bilingual operation** | English-primary; Hindi mixed quality | Explicit English + Hindi voice examples, Whisper `hi` language code, and mixed-language prompt templates |
| **Tool execution** | Optional function calling; no guaranteed execution audit | Mandatory tool loop with `ActionLogEntry` per call, structured output validation, and 8-turn cap with safe failure recovery |
| **Business scoping** | No multi-tenant data isolation | UUID-based `business_id` scoping on every SQLAlchemy query and tool invocation |

### vs. Stock Odoo Integrations

| Limitation | Native Odoo Modules | Aster Ops `aster_ops_integration` |
|---|---|---|
| **Integration style** | Rigid, synchronous XML-RPC / JSON-RPC hooks | Pluggable `OdooGateway` protocol with circuit-breaker protection and async webhook inbound (`/aster_ops/webhook/inbound`) |
| **Observability** | Minimal logging; no structured audit trail | Immutable `aster_ops_log` model with sequence reference (`AOP-000001`), request/response payloads, latency, and error capture |
| **Data integrity** | Loose external references; fragile post-migration IDs | Unique `(company_id, external_system, external_model, external_id)` constraint on `aster_ops_mapping` |
| **Resilience** | Remote Odoo downtime blocks sync jobs | `CircuitBreaker` trips after 5 failures, enters `HALF_OPEN` probe mode after 30s, and prevents thread / worker exhaustion |
| **Scheduling** | Basic `ir.cron` with no visibility | Scheduled action (`ir_cron_sync_aster_ops`) runs every 15 minutes with pending-record detection and error-state tracking |
| **Security** | Broad model access via groups | Granular `ir.model.access.csv` — users read logs/mappings; managers have full CRUD |

The combination of persistent conversational memory, circuit-breaker-protected Odoo connectivity, immutable audit logging, and a terminal-native Codex development loop creates a system that is structurally more reliable, observable, and maintainable than either a raw ChatGPT wrapper or a stock Odoo connector.
