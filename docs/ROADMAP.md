# Newsletter Orchestrator Roadmap

## Product goal

Build a local-first scheduled AI newsletter system.

Subscribers choose topics and receive newsletters at configured local times.
Administrators manage schedules, sources, newsletters, AI assistance, and
human review. The system uses AI only for bounded tasks and never operates as
an unrestricted continuous agent.

## Completed

- FastAPI backend with PostgreSQL connectivity and health endpoint.
- Streamlit administration UI.
- Subscriber creation, update, topic selection, and unsubscribe.
- Newsletter creation and list endpoints.
- Per-subscriber newsletter draft creation.
- AI classification, summarization, and refinement helpers.
- LangGraph workflow for bounded newsletter processing.
- Human review queue for high and critical content.
- Automation state, cooldown, daily-limit, and duplicate-prevention logic.
- Persisted delivery schedule configuration.
- Mailpit mock email delivery.
- Local deterministic article ingestion for development and demos.

## Current milestone: scheduled delivery

### Objective

Connect persisted delivery schedules to a bounded backend scheduler.

### Required work

1. Register and verify schedule routes.
2. Correct backend send policy for both high and critical content.
3. Define newsletter lifecycle statuses.
4. Extend schedule-run persistence for idempotency and audit history.
5. Implement a schedule execution service.
6. Implement a separate scheduler worker process.
7. Add run-now and schedule-run history API endpoints.
8. Add scheduler visibility to the Streamlit dashboard.
9. Add tests for schedule timing, idempotency, safety, and delivery outcomes.

### Acceptance criteria

- An enabled schedule runs only on its chosen weekday, local time, and timezone.
- The same schedule cannot send twice within one scheduled delivery window.
- The worker processes a bounded number of source items per run.
- No unseen article produces a recorded skipped run without an email.
- Low/medium content is sent only after backend approval checks.
- High/critical content enters Human Review and is not sent automatically.
- Schedule runs are visible in the database and API.
- The scheduler never invokes the LLM unless a schedule is actually due.

## Future milestones

### Real source adapters

- Keep deterministic stubs for tests.
- Add one allowlisted RSS source.
- Normalize source data and retain source identity/hash deduplication.
- Add source timeout, retry, and failure recording.

### Production readiness

- Implement real SMTP or provider API delivery.
- Add authentication and administrator roles.
- Add source and user-level authorization.
- Add structured audit logs, monitoring, and alerting.
- Deploy API, worker, UI, and PostgreSQL separately.
