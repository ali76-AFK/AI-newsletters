# Newsletter Orchestrator

Local-first, scheduled AI newsletter orchestration with FastAPI, Streamlit,
PostgreSQL, LangGraph workflows, Mailpit, and selectable AI providers.

## Current MVP

The project currently supports:

- Subscriber and topic management.
- Delivery schedule configuration.
- Newsletter creation and recipient drafts.
- AI classification, summarization, and draft refinement.
- Bounded LangGraph newsletter workflow execution.
- Human review for high and critical content.
- Automation controls, duplicate prevention, cooldowns, and daily limits.
- PostgreSQL persistence.
- Mock email delivery through Mailpit.
- Mock, Ollama, and Groq AI-provider modes.

The current source ingestion implementation uses deterministic local articles for
development and demos.

## Important safety model

This system does not run an unrestricted AI agent continuously.

A future scheduler will evaluate saved delivery schedules and start a finite,
bounded workflow only when a schedule is due. AI is used only for specific
tasks such as classification, summarization, and refinement.

High and critical newsletter content must be reviewed by a human before send.

## Local development

### 1. Start PostgreSQL and Mailpit

```bash
cd infrastructure
cp env/db.env.example env/db.env
docker compose up -d
```

Mailpit UI: `http://127.0.0.1:8025`

### 2. Start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .
pip install ".[dev]"

export EMAIL_MODE=mock
export LLM_PROVIDER=mock

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend health check:

```bash
curl http://127.0.0.1:8000/health
```

### 3. Start the Streamlit UI

In a second terminal:

```bash
cd ui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export BACKEND_URL="http://127.0.0.1:8000"

streamlit run launcher.py
```

Open: `http://127.0.0.1:8501`

## AI modes

Set `LLM_PROVIDER` to one of:

- `mock` for deterministic offline development.
- `ollama` for local inference.
- `groq` for cloud inference.

See [docs/AI_PRIVACY.md](docs/AI_PRIVACY.md) for the data-sharing policy.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Development progress](docs/DEVELOPMENT_PROGRESS.md)
- [AI privacy](docs/AI_PRIVACY.md)

## Tests

From the project root:

```bash
pytest -q
```
