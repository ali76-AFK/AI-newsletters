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

## 2026-08-20 — Timezone-aware schedule scanning

### Completed

- Added a versioned database migration for `ScheduleRun.run_key`.
- Added timezone-aware due-time evaluation for `Europe/Berlin` and `UTC`.
- Added deterministic local delivery-window keys.
- Added an idempotent due-schedule scan service.
- Added `POST /api/schedules/scan-due` for controlled scan testing.
- Verified that a repeated scan for the same schedule window reports
  `already_processed` instead of creating another run.
- Added tests for due-time matching, timezone handling, skipped schedules,
  and delivery-window idempotency.

### Not included yet

- No continuously running scheduler process yet.
- No scheduler health/status persistence yet.
- No real RSS/API ingestion yet.

## 2026-08-20 — Separate scheduler worker

### Completed

- Added a standalone scheduler worker process.
- The worker opens a fresh database session for every scan.
- The worker calls the tested due-schedule scan service once per minute.
- The worker logs scan outcomes and handles Ctrl+C / SIGTERM shutdown.
- The worker remains separate from FastAPI/Uvicorn and Streamlit.

### Operational run commands

```bash
# Terminal 1
cd infrastructure && docker compose up -d

# Terminal 2
cd backend && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 3
cd ui && source .venv/bin/activate
streamlit run launcher.py

# Terminal 4
cd backend && source .venv/bin/activate
python -m app.scheduler_worker
```

## 2026-08-20 — Schedule-run visibility in Streamlit

### Completed

- Added schedule run-history visibility to the Delivery Schedules page.
- Added controlled Run now actions for enabled schedules.
- Displayed sent, pending-review, skipped, failed, and already-processed states.
- Added a clear worker-process reminder for timed delivery.
- Kept UI actions routed through existing bounded backend endpoints.

## 2026-08-20 — Dashboard schedule operations

### Completed

- Added read-only schedule operations indicators to the Dashboard.
- Added enabled-schedule, pending-review, latest-run, and
  failed/skipped-run indicators.
- Added the latest schedule-run message and worker start reminder.
- Kept all state-changing actions on Delivery Schedules, Automation,
  and Human Review pages.

## 2026-08-20 — Allowlisted RSS ingestion adapter

### Completed

- Added `NEWS_SOURCE_MODE` with deterministic `stub` mode as the default.
- Added an allowlisted RSS adapter for `Spiegel` and the `ai_news` topic.
- Added HTTPS validation, a response-size limit, a timeout, and bounded RSS entry processing.
- Normalized RSS entries into the existing `NewsArticle` model.
- Updated schedule execution and automation ticks to select stub or RSS articles through one source selector.
- Retained deterministic local stubs for tests and demos.
- Added mocked RSS tests with no network dependency.

### Activation

Set `NEWS_SOURCE_MODE=rss` in the backend environment to use the allowlisted live feed.
Keep `NEWS_SOURCE_MODE=stub` for deterministic local testing.

### Current RSS topic behavior

The initial `Spiegel` RSS mapping uses the SPIEGEL science/technology feed for
the existing `ai_news` routing category. Feed entries can include broader
technology and science coverage; strict article-level topic relevance filtering
is a future enhancement. The system still processes only one bounded unseen
article per schedule run.

## 2026-08-21 — Topic-aware RSS relevance filtering

### Completed

- Added technology/science, business, and world-news subscriber topics.
- Added a source/topic RSS allowlist registry.
- Added deterministic bounded keyword relevance filtering for technical topics.
- Added broad `technology_science` routing without keyword restriction.
- Added `skipped_no_relevant_articles` schedule-run outcomes.
- Updated dashboard and schedule UI labels for relevance skips.
- Added tests for new topics, relevance filtering, RSS filtering, and feed allowlisting.

### Current feed coverage

The SPIEGEL science/technology RSS feed currently supports:
`ai_news`, `robotics`, `data_eng`, `devops`, `llm_workflows`, and
`technology_science`.

`business` and `world_news` are valid subscriber topics but require dedicated
allowlisted feeds before RSS-mode scheduled delivery can use them.
