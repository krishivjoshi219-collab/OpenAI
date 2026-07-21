# Aster Ops · AI Operations Employee

**Hackathon project** (OpenAI Build Week) — a voice-driven AI operations assistant for small and medium businesses. Create customers, raise invoices, manage inventory, and get compliance guidance by typing or speaking in English or Hindi.

## Stack
- **Frontend/UI:** Streamlit 1.59
- **AI:** OpenAI Responses API (default) · Groq Chat Completions · Gemini Chat Completions
- **Database:** SQLite (development/Cloud) · PostgreSQL (production)
- **ORM:** SQLAlchemy 2.0 + Alembic migrations
- **Voice:** Groq Whisper (`whisper-large-v3-turbo`)
- **PDF export:** ReportLab · Pillow (AVIF/JPG)

## How to run
The workflow **Start application** runs the app on port 5000:
```
PYTHONPATH=/home/runner/workspace streamlit run app/ui/streamlit_app.py --server.port 5000 --server.address 0.0.0.0 --server.headless true
```

## Required secrets
At least one AI provider key is required. Add it via Replit Secrets **or** paste it into the "Bring Your Own Key" sidebar at runtime:

| Secret | Required for |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI provider (default) |
| `GROQ_API_KEY` | Groq LLM + voice transcription |
| `GEMINI_API_KEY` | Gemini provider |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram notifications (optional) |
| `DATABASE_URL` | PostgreSQL URL (optional; SQLite used otherwise) |

Set `AI_PROVIDER=groq` (or `gemini`) to switch providers.

## Key fixes applied (post-import)
- `asyncio.run()` replaced with `asyncio.new_event_loop().run_until_complete()` in the preflight check so it works on Streamlit Cloud's event-loop thread
- `WhisperService` now checks the BYOK sidebar Groq key before falling back to environment secrets
- Chat adapter (`Groq`/`Gemini` path) no longer sends the `strict` field in tool definitions or JSON schema — Groq rejects it with a 400 error
- `reportlab` and `psycopg[binary]` installed and confirmed working

## Project layout
```
app/
  ui/               Streamlit pages + components
  ai/               AI provider clients and tool orchestration
  business/         Core business engine (customers, invoices, inventory)
  database/         SQLAlchemy sessions, repositories, table creation
  models/           ORM models
  onboarding/       CSV / PDF extraction pipeline
  services/         Dashboard, government assistant, invoice image/PDF
  memory/           Keyword RAG retriever
  notifications/    Telegram adapter
config/
  settings.py       pydantic-settings configuration
```

## User preferences
- Do not restructure the project layout without asking
- Keep fixes minimal — no new features without explicit request
