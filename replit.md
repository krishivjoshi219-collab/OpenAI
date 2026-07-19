# AI Operations Employee

An AI-powered business operations workspace built on Streamlit, OpenAI-compatible providers, SQLite/PostgreSQL, and SQLAlchemy.

## How to run

The app starts automatically via the **Start application** workflow:

```
PYTHONPATH=/home/runner/workspace streamlit run app/ui/streamlit_app.py --server.port 5000 --server.address 0.0.0.0 --server.headless true
```

It runs on port 5000.

## Environment

| Variable | Value | Notes |
|---|---|---|
| `AI_PROVIDER` | `groq` | Switch to `openai` or `gemini` to change provider |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Active model |
| `GROQ_API_KEY` | *(secret)* | Set via Replit Secrets |
| `DATABASE_URL` | SQLite (default) | Override with a PostgreSQL URL for production |

## Stack

- **Frontend:** Streamlit
- **AI:** Groq (Llama 3.3 70B) — switchable to OpenAI or Gemini via `AI_PROVIDER`
- **Database:** SQLAlchemy + SQLite (local) / PostgreSQL (deployed)
- **Migrations:** Alembic

## User preferences

- Use Groq as the default AI provider.
