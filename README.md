# Newsletter Orchestrator (Phase 1)

Locally hosted agentic newsletter orchestration system with FastAPI, LangGraph (planned), Streamlit, PostgreSQL, and multi-LLM support (Ollama, Groq).

## Phase 1 status

This phase includes:

- Backend skeleton (FastAPI, structured logging, DB health check).
- Streamlit UI skeleton (backend health status).
- Docker Compose for PostgreSQL and Mailpit (mock SMTP).

## Quickstart

```bash
# From project root
cd infrastructure
cp env/db.env.example env/db.env
docker compose up -d

cd ../backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .
pip install ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# In another terminal
cd ../ui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BACKEND_URL="http://127.0.0.1:8000"
streamlit run app.py
```

Then open Streamlit at http://localhost:8501.
