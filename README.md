# AI Operations Employee

A polished MVP foundation for an AI Operations Employee, built for OpenAI Build Week. It is intentionally an application scaffold, not a production ERP: business workflows and integrations are left unimplemented.

## Stack

- Python 3.12+
- Streamlit
- OpenAI Responses API
- SQLAlchemy 2.x and Alembic
- Pydantic Settings
- PostgreSQL, with SQLite supported for local development
- Telegram Bot API

## Project layout

```text
app/
  ai/             # OpenAI client and AI orchestration boundary
  business/       # Future domain workflows and ERP adapters
  database/       # Engine, sessions, and migration metadata
  memory/         # Future conversational and operational memory
  models/         # SQLAlchemy ORM models
  notifications/  # Telegram and future notification channels
  onboarding/     # Company setup and configuration flow
  prompts/        # Version-controlled prompt templates
  routers/        # Application-facing request/page routing
  services/       # Use-case services
  ui/             # Streamlit presentation layer
  utils/          # Cross-cutting helpers
config/           # Typed runtime settings
migrations/       # Alembic migration environment
tests/            # Automated tests
docs/             # Architecture and product documentation
```

Dependencies flow inward: UI and routers call services; services coordinate AI, memory, notifications, and business adapters; infrastructure concerns stay behind their respective module boundaries. This makes an eventual Odoo adapter a `business/` integration rather than a rewrite of UI or use cases.

## Getting started

1. Create and activate a Python 3.12+ virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in the values you need.
4. Start the placeholder UI: `streamlit run app/ui/streamlit_app.py`

## Database layer

The initial schema contains business-scoped customers, suppliers, products, invoices and invoice items, inventory, durable business memory, and per-business settings. Every entity has a UUID primary key and audit timestamps. Database access goes through the generic `Repository[T]`, while callers own the transaction via `session_scope`.

## AI-to-business tool calling

`create_business_ai_service(engine, business_id)` connects the OpenAI Responses API to a single, already-scoped `BusinessEngine`. The model sees JSON-schema function tools, chooses the appropriate business operation, and includes a short `reason` with every call. The adapter validates and converts JSON input to typed domain commands, then returns JSON-safe records to the model.

Call `AIService.business_command(...)` to permit execution and require the standard strict JSON response (`summary`, `outcome`, `actions`, and `next_steps`). Its `AIResult` contains that parsed `structured_output` plus `actions`: one structured audit entry per attempted tool call (`tool_name`, `reason`, arguments, status, and output). The same events are emitted as JSON application log records named `ai_business_action`, including failures, so they can be forwarded to a central log store.

## Notifications

`NotificationService` sends daily summaries, invoice reminders, low-inventory alerts, and approval requests through a channel-neutral contract. `TelegramNotificationChannel` is the initial adapter; email, WhatsApp, Slack, and SMS can implement the same `NotificationChannel` protocol without changing business notification use cases. `create_notification_service()` uses `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to configure the default Telegram route. Every delivery returns a structured receipt and is logged as a `business_notification` event.

## Government Assistant

The Government Assistant produces structured preparation checklists, document lists, business-registration guidance, and tax-registration guidance for India and the United States. It is deliberately informational rather than legal advice: every response states its uncertainty, includes a non-advice disclaimer, and links to first-party government sources for verification.

## Odoo integration

`create_odoo_ai_service()` uses Odoo JSON-RPC and the `ODOO_URL`, `ODOO_DATABASE`, `ODOO_USERNAME`, and `ODOO_API_KEY` environment variables. Its dedicated OpenAI tool allowlist supports customer creation/search, draft invoice creation, inventory-count updates, invoice send-and-print requests, and Odoo scheduled activities. Use `service.command(..., agent=ODOO_AGENT, execute_tools=True)` (or provide the equivalent agent profile) so only the Odoo tools are exposed.

## Database migrations

Alembic includes the initial schema revision. Apply it with:

```bash
alembic upgrade head
```

Create a migration after changing models with:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Quality checks

```bash
ruff check .
mypy app
pytest
```
