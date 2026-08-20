from __future__ import annotations

import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from common import (
    api_get,
    get_schedule_runs,
    get_schedules,
)


load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
GROQ_MODEL = os.getenv("GROQ_MODEL", "")


st.set_page_config(
    page_title="Dashboard | AI Newsletters",
    page_icon="🏠",
    layout="wide",
)


def render_status_card(
    label: str,
    value: str,
    subvalue: str,
    value_class: str = "",
) -> None:
    st.markdown(
        f"""
        <div class="card">
            <div class="metric-label">{label}</div>
            <div class="metric-value {value_class}">{value}</div>
            <div class="metric-subvalue">{subvalue}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_timestamp(value: str | None) -> str:
    if not value:
        return "Never"

    try:
        timestamp = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value


def run_sort_value(run: dict) -> str:
    return run.get("started_at") or ""


def run_status_label(status: str) -> str:
    labels = {
        "sent": "✅ Sent",
        "pending_review": "🟠 Pending review",
        "skipped_no_new_articles": "ℹ️ No new articles",
        "already_processed": "↩️ Already processed",
        "failed": "❌ Failed",
        "running": "⏳ Running",
    }
    return labels.get(status, status.replace("_", " ").title())


st.markdown(
    """
    <style>
        .main {
            background-color: #050816;
        }
        .hero-title {
            font-size: 42px;
            font-weight: 700;
            color: #ff4b9a;
            text-align: center;
            margin-bottom: 8px;
        }
        .hero-subtitle {
            font-size: 18px;
            color: #d1d5db;
            text-align: center;
            margin-bottom: 24px;
        }
        .card {
            background-color: #0b1020;
            border-radius: 14px;
            padding: 18px;
            border: 1px solid #1f2937;
            min-height: 120px;
        }
        .metric-label {
            font-size: 13px;
            color: #9ca3af;
            line-height: 1.2;
            margin-bottom: 10px;
        }
        .metric-value {
            font-size: 22px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.2;
            margin-bottom: 10px;
        }
        .metric-subvalue {
            font-size: 14px;
            color: #cbd5e1;
            line-height: 1.3;
        }
        .metric-badge-ok {
            color: #22c55e;
        }
        .metric-badge-warn {
            color: #f97316;
        }
        .metric-badge-error {
            color: #ef4444;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-title">AI newsletters</div>
    <div class="hero-subtitle">
        Local-first, bounded newsletter orchestration with scheduled workflows.
    </div>
    """,
    unsafe_allow_html=True,
)

health = api_get("/health")
schedules_data = get_schedules()
reviews_data = api_get("/api/reviews/pending")

if health.get("error"):
    backend_status = "Unavailable"
    backend_subvalue = health["error"]
    backend_class = "metric-badge-error"
else:
    backend_is_ok = health.get("status") == "ok"
    backend_status = "OK" if backend_is_ok else "Degraded"
    backend_subvalue = (
        "Backend API and database are reachable"
        if backend_is_ok
        else "Check backend connectivity"
    )
    backend_class = (
        "metric-badge-ok"
        if backend_is_ok
        else "metric-badge-warn"
    )

schedules = schedules_data.get("schedules", [])
enabled_schedules = [
    schedule
    for schedule in schedules
    if schedule.get("enabled")
]

pending_review_count = reviews_data.get("count", 0)
all_runs: list[dict] = []
run_lookup_error = None

if schedules_data.get("error"):
    run_lookup_error = schedules_data["error"]
else:
    for schedule in schedules:
        schedule_id = schedule["id"]
        runs_data = get_schedule_runs(schedule_id)

        if runs_data.get("error"):
            run_lookup_error = runs_data["error"]
            continue

        for run in runs_data.get("runs", []):
            all_runs.append(
                {
                    **run,
                    "schedule_email": schedule.get("email"),
                }
            )

all_runs.sort(
    key=run_sort_value,
    reverse=True,
)

latest_run = all_runs[0] if all_runs else None
failed_or_skipped_count = sum(
    1
    for run in all_runs
    if run.get("status")
    in {
        "failed",
        "skipped_no_new_articles",
    }
)

top_row = st.columns(3)

with top_row[0]:
    render_status_card(
        "Backend status",
        backend_status,
        backend_subvalue,
        backend_class,
    )

with top_row[1]:
    db_status = (
        "Healthy"
        if health.get("db") == "healthy"
        else "Unhealthy"
    )
    db_class = (
        "metric-badge-ok"
        if db_status == "Healthy"
        else "metric-badge-error"
    )

    render_status_card(
        "Database status",
        db_status,
        "PostgreSQL connection status",
        db_class,
    )

with top_row[2]:
    provider = LLM_PROVIDER.lower()

    if provider == "mock":
        provider_text = "Mock deterministic"
    elif provider == "ollama":
        provider_text = "Ollama local"
    elif provider == "groq":
        provider_text = (
            f"Groq ({GROQ_MODEL})"
            if GROQ_MODEL
            else "Groq"
        )
    else:
        provider_text = f"Provider: {LLM_PROVIDER}"

    render_status_card(
        "AI provider",
        provider_text,
        "AI calls occur only in bounded workflows",
        "metric-badge-ok",
    )

st.divider()
st.subheader("Schedule operations")

operations_row = st.columns(4)

with operations_row[0]:
    render_status_card(
        "Enabled schedules",
        str(len(enabled_schedules)),
        f"{len(schedules)} saved schedule(s)",
        (
            "metric-badge-ok"
            if enabled_schedules
            else "metric-badge-warn"
        ),
    )

with operations_row[1]:
    review_class = (
        "metric-badge-error"
        if pending_review_count
        else "metric-badge-ok"
    )

    render_status_card(
        "Pending human review",
        str(pending_review_count),
        (
            "Review required before sending"
            if pending_review_count
            else "No newsletters waiting for review"
        ),
        review_class,
    )

with operations_row[2]:
    if latest_run:
        render_status_card(
            "Latest schedule run",
            run_status_label(
                latest_run.get("status", "unknown")
            ),
            (
                f"Schedule #{latest_run.get('schedule_id')} · "
                f"{format_timestamp(latest_run.get('started_at'))}"
            ),
            "metric-badge-ok",
        )
    else:
        render_status_card(
            "Latest schedule run",
            "Never",
            "No schedule runs recorded",
            "metric-badge-warn",
        )

with operations_row[3]:
    failure_class = (
        "metric-badge-error"
        if failed_or_skipped_count
        else "metric-badge-ok"
    )

    render_status_card(
        "Failed or skipped runs",
        str(failed_or_skipped_count),
        "Across retained schedule-run history",
        failure_class,
    )

if run_lookup_error:
    st.warning(
        "Some schedule-run history could not be loaded: "
        f"{run_lookup_error}"
    )

st.info(
    "Timed delivery requires the separate scheduler worker. Start it from "
    "the backend environment with `python -m app.scheduler_worker`. "
    "The worker scans enabled schedules once per minute and launches "
    "only due, bounded workflows."
)

if latest_run:
    st.subheader("Most recent schedule result")

    latest_message = latest_run.get("message") or "No message recorded."

    st.write(
        f"**Status:** {run_status_label(latest_run.get('status', 'unknown'))}"
    )
    st.write(
        f"**Schedule:** #{latest_run.get('schedule_id')} · "
        f"{latest_run.get('schedule_email', 'Unknown recipient')}"
    )
    st.write(
        f"**Started:** {format_timestamp(latest_run.get('started_at'))}"
    )
    st.write(f"**Message:** {latest_message}")