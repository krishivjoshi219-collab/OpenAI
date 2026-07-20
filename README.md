# Aster Ops · AI Operations Employee
> **OpenAI Build Week Hackathon Entry**  
> **Track:** Work and Productivity  
> **Codex Session ID:** `019f70f1-c6ee-7243-9897-aadd366e1819`  

---

## Executive Summary
Aster Ops is a production-grade, voice-driven AI operations employee designed for small and medium businesses. Built under the core product principle that **"People shouldn't learn software; software should learn people,"** Aster Ops provides a natural language command center that replaces complex ERP systems, manual spreadsheet tracking, and rigid databases with fluid conversational workflows.

Through deep integration with the OpenAI API (and compatible multi-provider engines), Aster Ops handles onboarding data ingestion, business memory retention, automated invoicing, real-time inventory management, proactive status updates, and compliance support.

---

## Table of Contents
1. [Codex Collaboration History](#1-codex-collaboration-history)
2. [How it Works & Usage Guide](#2-how-it-works--usage-guide)
3. [The Architectural Edge](#3-the-architectural-edge)
   - [vs. ChatGPT Web/API](#vs-chatgpt-webapi)
   - [vs. Stock Odoo ERP Connectors](#vs-stock-odoo-erp-connectors)
4. [Functional Modules](#4-functional-modules)
   - [Onboarding & Ingest](#onboarding--ingest)
   - [Conversational Commands & Multi-turn History](#conversational-commands--multi-turn-history)
   - [Durable RAG Business Memory](#durable-rag-business-memory)
   - [Action Engine & Transactional Undo](#action-engine--transactional-undo)
   - [Government Assistant (India & US)](#government-assistant-india--us)
   - [Proactive Telegram Bot Notifications](#proactive-telegram-bot-notifications)
   - [Searchable Code Viewer](#searchable-code-viewer)
5. [Production Architecture](#5-production-architecture)
   - [Resilience (Circuit Breaker, Preflight Health Checks)](#resilience-circuit-breaker-preflight-health-checks)
   - [Observability (Metrics Collector, Structured Logger)](#observability-metrics-collector-structured-logger)
   - [Database Schema & Models](#database-schema--models)
6. [Installation & Getting Started](#6-installation--getting-started)
7. [Automated Test Suite & Quality Verification](#7-automated-test-suite--quality-verification)

---

## 1. Codex Collaboration History

### Session ID
`/feedback Codex Session ID: 019f70f1-c6ee-7243-9897-aadd366e1819`

### Narrative of Codex Cooperation
This codebase was conceptualized, structured, and systematically built in collaboration with OpenAI Codex. Over the course of Session `019f70f1-c6ee-7243-9897-aadd366e1819` running `gpt-5.6-terra`, we transitioned the project from an abstract prompt outline into a fully typed python repository containing 11 frontend pages, 22 robust unit tests, and production-grade reliability layers.

Key developmental milestones achieved with Codex include:
1. **MVP Architecture & Layout Design**: Scaffolding the repository pattern using SQLAlchemy, separating UI rendering from business services, and establishing configuration validation using Pydantic Settings.
2. **Onboarding & Parsing Pipeline**: Crafting the heuristics for robust CSV and PDF table extraction (`pdfplumber` integration) along with interactive `st.data_editor` mapping.
3. **Transaction Execution & Reversals**: Modeling the `ActionLog` and coding the mathematical operations required to support full **Undo** actions (e.g., reversing stock levels, restoring invoices to draft, and refunding balances).
4. **Bilingual Voice Input Integration**: Wiring Groq Whisper audio transcription alongside localized mixed English-Hindi (Hinglish) prompt templates for conversational commands.
5. **Proactive Telegram Wrap-up**: Programming the `TelegramBot` client and adding the sidebar event dispatch button with proper exception wrapping to guard the Streamlit UI against network drops.

---

## 2. How it Works & Usage Guide

### Dynamic Walkthrough
1. **Onboarding**: Upload your business datasets (invoices, customer directories, product stock sheets) in CSV or PDF format. Review and correct the parsed records inside the data editor before committing them to the database.
2. **Command Center**: Control your entire business by typing or speaking in English or Hinglish:
   * *"Create an invoice for Priya Sharma for 3 Organic Cotton Totes."*
   * *"SKU TOTE-001 ki stock 120 units set karo."*
3. **Action Execution & Reversal**: The AI translates your query into a structured execution package. If you make a mistake, say *"Undo the last action"* to run a rollback.
4. **Dashboard & Analytics**: Monitor open receivables, low inventory bars, and recent activity updates.
5. **Government Assistant**: Enter your country (US or India) and target business structure to receive state-specific checklists and regulatory filing guidance.
6. **Telegram End-of-Day Wrap-up**: Send outbound event summaries and low-stock alerts to your team.

---

## 3. The Architectural Edge

### vs. ChatGPT Web/API
Unlike simple ChatGPT wrappers, Aster Ops isolates, validates, and persists every interaction:
* **Persistent Execution Memory**: Instead of losing context on page refreshes, Aster Ops maintains a database-backed `ConversationState`.
* **Reliable Multi-Turn Execution**: Multi-turn history is systematically managed so the agent retains context across multiple tool calls without drift.
* **Scoped SQL Ingestion**: Database operations are strictly isolated by UUID-based business keys, preventing leakage between workspaces.
* **Deterministic Execution Logs**: An immutable audit log records the exact reason and schema for every AI action.

### vs. Stock Odoo ERP Connectors
Standard Odoo integrations rely on rigid, fragile sync pipelines. Aster Ops introduces:
* **Circuit Breaker Protection**: All outgoing RPC connections to external systems like Odoo are wrapped in a three-state circuit breaker (`CLOSED`, `OPEN`, `HALF_OPEN`) to prevent cascading thread pool exhaustion.
* **Webhook Resilience**: Incoming data updates are processed asynchronously through logging gateways, ensuring network timeouts do not block core transactions.
* **Observability Instrumentation**: All API integrations automatically populate metrics (histograms and counters) to log latencies and error rates.

---

## 4. Functional Modules

### Onboarding & Ingest
Aster Ops imports operational datasets via `app/onboarding/`:
* **CSV and PDF Table Locators**: Scans files to identify structures, normalizes header column aliases (`unit_price` vs. `price` vs. `rate`), and maps them onto clean tables.
* **Data Verification Screen**: Users review extracted records via Streamlit’s interactive data editor before database commitment.

### Conversational Commands & Multi-turn History
* **Multilingual Input**: Support for spoken audio (Groq Whisper) and text input.
* **Jinja2 Prompt Templates**: Version-controlled prompts construct detailed system instructions dynamically based on current memory.

### Durable RAG Business Memory
* **Context Retrieval**: Business preferences, operational facts, or customer specifications are saved into the `business_memory` table.
* **Vectorless Retrieval**: A keyword-based token search engine queries stored facts in real-time to augment prompt context before action analysis.

### Action Engine & Transactional Undo
* **Structured Payload Validation**: Action proposals are processed as Pydantic schemas.
* **Undo Support**: The Action Engine maintains database links for each transaction. When an undo command runs, the system reverses the values in the SQL database.

### Government Assistant (India & US)
* **Localized Checklists**: Tailored compliance rules for Indian and US jurisdictions (e.g., GST registration, EIN procurement, labor filings).
* **Source Citations**: Links to official sites (Udyam, IRS, state portals) are provided to ensure guidelines are verifiable.

### Proactive Telegram Bot Notifications
* **Team Communication**: Sends automated alerts to Telegram channels.
* **Manual Trigger**: The "Generate End-of-Day Wrap-up" button compiles active sales metrics and stock alerts for delivery.

### Searchable Code Viewer
* **Developer Diagnostics**: A built-in code search interface allows developers and judges to browse, filter, and inspect the codebase from inside the Streamlit app.

---

## 5. Production Architecture

```
                                  [ Streamlit Frontend ]
                                            │
                      ┌─────────────────────┼─────────────────────┐
                      ▼                     ▼                     ▼
              [ Voice / Text ]       [ Data Ingest ]      [ Code Viewer ]
                      │                     │
                      ▼                     ▼
               [ AI Service ]        [ CSV/PDF Parser ]
                      │                     │
      ┌───────────────┴───────────────┐     │
      ▼                               ▼     ▼
[ Memory RAG ]               [ Action Execution Engine ]
                                      │
                                      ▼
                             [ SQLAlchemy ORM ]
                                      │
                              ┌───────┴───────┐
                              ▼               ▼
                        [ SQLite DB ]  [ Telegram Bot ]
```

### Resilience
* **Circuit Breaker (`circuit_breaker.py`)**: Drops failing connections immediately to prevent bottleneck delays.
* **Self-Healing Schema**: Auto-creates missing tables and applies migrations on startup without crashing the interface.

### Observability
* **Metrics Collector (`metrics.py`)**: Captures detailed metrics for database queries, tool invocation latency, and error states.
* **JSON Structured Logging (`logging.py`)**: Structured formatting for production log ingestion.

---

## 6. Installation & Getting Started

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/krishivjoshi219-collab/OpenAI.git
cd OpenAI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```env
DATABASE_URL=sqlite:///aster_ops.db
AI_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

### 3. Run Database Migrations
```bash
alembic upgrade head
```

### 4. Start the Application
```bash
PYTHONPATH=. streamlit run app/ui/streamlit_app.py
```

---

## 7. Automated Test Suite & Quality Verification
The project includes **22 automated tests** verifying database CRUD, RAG retrieval accuracy, onboarding parsers, and tool-calling execution.

Run the test suite:
```bash
python3 -m pytest
```

Check static linting and type constraints:
```bash
ruff check .
mypy app
```
