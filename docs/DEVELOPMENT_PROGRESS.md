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

## 2026-08-19 — Safety policy enforcement

### Completed

- Blocked direct approval for both high-risk and critical-risk newsletters.
- Blocked direct LangGraph sends for both high-risk and critical-risk newsletters.
- Reserved high/critical approval and sending for the Human Review route.
- Added explicit `classified`, `pending_review`, `approved`, and `sent`
  newsletter workflow states where applicable.
- Updated successful LangGraph workflow completion to mark newsletters `sent`.
- Added automated regression tests for critical approval blocking, direct
  workflow blocking, low-risk approved delivery, and human-review routing.

## 2026-08-20 — Bounded schedule run-now API

### Completed

- Added persisted `ScheduleRun.run_key` values for run identification.
- Added a bounded schedule execution service using saved schedule sources and topics.
- Added `POST /api/schedules/{schedule_id}/run-now` for controlled execution.
- Added `GET /api/schedules/{schedule_id}/runs` for run history.
- Reused existing duplicate prevention, classification, human-review, and send policy.
- Kept execution finite: one saved schedule and at most one unseen local article.
- Added tests for disabled schedules and persisted schedule-run results.

### Not included yet

- No continuous scheduler worker.
- No timezone-based due-schedule evaluation.
- No real RSS/API news ingestion.
