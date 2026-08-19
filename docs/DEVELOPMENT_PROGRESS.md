# Development Progress

## 2026-08-19 — UI consolidation and scheduler planning

### Completed

- Implemented and compiled Streamlit pages for:
  - Subscribers
  - Delivery schedules
  - Newsletter drafts
  - Human review
  - Automation
- Verified FastAPI connectivity from the UI.
- Verified newsletter listing and recipient draft listing.
- Verified Human Review rejection and automation resume flows.
- Verified automation status and safe tick behavior.
- Confirmed Mailpit mock SMTP configuration.
- Reconciled the implemented MVP with the project goal.

### Current architecture status

- FastAPI, Streamlit, PostgreSQL, LangGraph, and Mailpit are connected.
- AI provider support includes mock, Ollama, and Groq modes.
- Delivery schedules are stored but not yet executed automatically.
- News ingestion is deterministic local stub data.
- Real email delivery, authentication, and role separation remain future work.

### Next milestone

Implement bounded scheduled delivery:

1. Register schedule routes.
2. Stabilize policy checks and statuses.
3. Extend schedule-run persistence.
4. Add schedule execution service.
5. Add separate scheduler worker.
6. Add tests and dashboard visibility.
