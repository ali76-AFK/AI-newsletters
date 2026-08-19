# Newsletter Orchestrator Architecture

## Purpose

Newsletter Orchestrator is a local-first, scheduled AI newsletter workflow.

Subscribers select topics. Administrators configure sources and delivery
schedules. At a scheduled time, the system runs one bounded workflow:

1. Select one unseen item from an allowed source.
2. Create and persist a newsletter candidate.
3. Classify its risk using the configured AI provider.
4. Route high or critical content to human review.
5. Create recipient drafts for matching active subscribers.
6. Send approved content through the configured email adapter.
7. Store run state, delivery state, and errors in PostgreSQL.

The system must not run an unrestricted or infinite AI agent loop. AI calls are
bounded to a specific newsletter task: classification, summarization, or draft
refinement.

## Components

```text
Streamlit Admin UI
        |
        | HTTP
        v
FastAPI Backend
        |
        +-- PostgreSQL
        |     subscribers, topics, schedules, newsletters, drafts,
        |     workflow executions, review decisions, and schedule runs
        |
        +-- Scheduler Worker
        |     evaluates due schedules and launches bounded schedule runs
        |
        +-- News Source Adapter
        |     local stub articles in development; RSS/API adapters later
        |
        +-- AI Provider
        |     mock, Ollama, or Groq
        |
        +-- Email Adapter
              Mailpit in development; real SMTP/API provider later
```

## Main data flow

```text
Subscriber preferences + delivery schedule
        |
        v
Scheduler identifies a due schedule
        |
        v
Bounded source ingestion and duplicate check
        |
        v
Newsletter creation and AI classification
        |
        +-- low/medium --> approved workflow --> recipient drafts --> send
        |
        +-- high/critical --> pending review --> human decision --> send/reject
```

## Technology choices

| Area | Current choice |
|---|---|
| Admin UI | Streamlit |
| Backend API | FastAPI |
| Database | PostgreSQL with SQLAlchemy |
| Workflow orchestration | LangGraph |
| AI providers | Mock, Ollama, Groq |
| Development email | Mailpit SMTP |
| Production email | SMTP or provider API, not yet implemented |
| Development news source | Deterministic local stub articles |
| Future news sources | Allowlisted RSS or API adapters |
| Scheduler | Separate worker process, planned |

## Safety rules

- Every workflow run is finite and tied to a newsletter or schedule run.
- A schedule run processes a bounded number of source items.
- Source external IDs and content hashes prevent duplicate processing.
- Low and medium risk content may be auto-approved under backend policy.
- High and critical risk content requires explicit human review.
- The backend, not only the UI, enforces send approval and risk checks.
- Mock email is the default development mode.
- Real delivery remains disabled until a real email adapter is implemented.
- Schedule-run idempotency prevents duplicate delivery in the same time window.

## Current limitations

- Delivery schedules are persisted but are not yet executed by a scheduler.
- News ingestion currently uses local stub articles only.
- Real email delivery is not implemented.
- Authentication and role-based authorization are not implemented.
- Schedule-run history and idempotency need to be completed.
