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
