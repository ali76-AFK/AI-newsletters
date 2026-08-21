from __future__ import annotations

import datetime as dt

import streamlit as st

from common import (
    create_schedule,
    disable_schedule,
    enable_schedule,
    get_schedule_runs,
    get_schedules,
    get_topics,
    run_schedule_now,
)


st.set_page_config(
    page_title="Delivery Schedules | AI Newsletters",
    page_icon="🗓️",
    layout="wide",
)


WEEKDAY_LABELS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def show_error(result: dict, action: str) -> None:
    message = result.get("error", "Unknown error")
    st.error(f"{action} failed: {message}")


def format_weekdays(days: list[int]) -> str:
    return ", ".join(
        WEEKDAY_LABELS.get(day, str(day))
        for day in days
    )


def status_label(status: str) -> str:
    labels = {
        "sent": "✅ Sent",
        "pending_review": "🟠 Pending review",
        "skipped_no_new_articles": "ℹ️ No new articles",
        "skipped_no_relevant_articles": "🔎 No relevant articles",
        "already_processed": "↩️ Already processed",
        "failed": "❌ Failed",
        "running": "⏳ Running",
    }
    return labels.get(status, status.replace("_", " ").title())


st.title("🗓️ Newsletter delivery schedules")
st.caption(
    "Configure delivery preferences and inspect schedule runs."
)

st.info(
    "Timed delivery requires the separate scheduler worker process. "
    "Run it with `python -m app.scheduler_worker` from the backend "
    "environment. The worker scans enabled schedules once per minute."
)

topics = get_topics()

if not topics:
    st.warning(
        "No topics are available from the backend yet."
    )

st.subheader("Create schedule")

with st.form("create_schedule_form", clear_on_submit=True):
    email = st.text_input(
        "Delivery email",
        placeholder="you@example.com",
    )

    name = st.text_input(
        "Name (optional)",
        placeholder="Newsletter recipient",
    )

    selected_topics = st.multiselect(
        "Topics",
        options=topics,
        default=topics[:1],
    )

    sources_text = st.text_input(
        "News sources",
        placeholder="e.g., Spiegel",
    )

    selected_days = st.multiselect(
        "Delivery days",
        options=list(WEEKDAY_LABELS.keys()),
        default=[0, 2, 4],
        format_func=lambda day: WEEKDAY_LABELS[day],
    )

    left_col, right_col = st.columns(2)

    with left_col:
        delivery_time = st.time_input(
            "Delivery time",
            value=dt.time(18, 0),
        )

    with right_col:
        timezone = st.selectbox(
            "Timezone",
            options=["Europe/Berlin", "UTC"],
            index=0,
        )

    enabled = st.checkbox(
        "Enable this schedule",
        value=False,
    )

    submitted = st.form_submit_button(
        "Save delivery schedule",
        type="primary",
    )

if submitted:
    sources = [
        source.strip()
        for source in sources_text.split(",")
        if source.strip()
    ]

    if not email.strip():
        st.error("Delivery email is required.")
    elif not selected_topics:
        st.error("Select at least one topic.")
    elif not sources:
        st.error("Enter at least one source.")
    elif not selected_days:
        st.error("Select at least one delivery day.")
    else:
        payload = {
            "email": email.strip(),
            "name": name.strip() or None,
            "topics": selected_topics,
            "sources": sources,
            "weekdays": selected_days,
            "delivery_time": delivery_time.strftime("%H:%M"),
            "timezone": timezone,
            "enabled": enabled,
        }

        result = create_schedule(payload)

        if result.get("error"):
            show_error(result, "Saving schedule")
        else:
            st.success("Delivery schedule saved.")
            st.rerun()

st.divider()
st.subheader("Saved schedules")

schedules_data = get_schedules()

if schedules_data.get("error"):
    show_error(schedules_data, "Loading schedules")
    st.stop()

schedules = schedules_data.get("schedules", [])

if not schedules:
    st.info("No delivery schedules have been saved yet.")
    st.stop()

enabled_count = sum(
    1 for schedule in schedules if schedule.get("enabled")
)

metric_one, metric_two = st.columns(2)

with metric_one:
    st.metric("Saved schedules", len(schedules))

with metric_two:
    st.metric("Enabled schedules", enabled_count)

for schedule in schedules:
    schedule_id = schedule["id"]
    enabled = schedule.get("enabled", False)
    state = "Enabled" if enabled else "Disabled"

    with st.expander(
        f"Schedule #{schedule_id} · "
        f"{schedule.get('email')} · {state}",
        expanded=False,
    ):
        info_col, actions_col = st.columns([3, 1])

        with info_col:
            st.write(
                f"**Topics:** "
                f"{', '.join(schedule.get('topics', []))}"
            )
            st.write(
                f"**Sources:** "
                f"{', '.join(schedule.get('sources', []))}"
            )
            st.write(
                f"**Days:** "
                f"{format_weekdays(schedule.get('weekdays', []))}"
            )
            st.write(
                f"**Time:** {schedule.get('delivery_time')} "
                f"({schedule.get('timezone')})"
            )
            st.write(
                f"**Last schedule run:** "
                f"{schedule.get('last_run_at') or 'Never'}"
            )

        with actions_col:
            if enabled:
                if st.button(
                    "Disable",
                    key=f"disable_{schedule_id}",
                ):
                    result = disable_schedule(schedule_id)

                    if result.get("error"):
                        show_error(result, "Disabling schedule")
                    else:
                        st.warning(
                            f"Schedule #{schedule_id} disabled."
                        )
                        st.rerun()
            else:
                if st.button(
                    "Enable",
                    type="primary",
                    key=f"enable_{schedule_id}",
                ):
                    result = enable_schedule(schedule_id)

                    if result.get("error"):
                        show_error(result, "Enabling schedule")
                    else:
                        st.success(
                            f"Schedule #{schedule_id} enabled."
                        )
                        st.rerun()

        st.divider()
        st.markdown("### Controlled execution")

        if not enabled:
            st.caption(
                "Enable this schedule before using Run now."
            )
        else:
            if st.button(
                "Run now",
                type="primary",
                key=f"run_now_{schedule_id}",
            ):
                with st.spinner(
                    f"Running schedule #{schedule_id}..."
                ):
                    result = run_schedule_now(schedule_id)

                if result.get("error"):
                    show_error(result, "Run now")
                else:
                    run = result.get("run", {})
                    run_status = result.get(
                        "status",
                        run.get("status", "unknown"),
                    )

                    st.success(
                        f"Schedule run completed: "
                        f"{status_label(run_status)}"
                    )

                    message = run.get("message")
                    if message:
                        st.write(message)

                    newsletter = result.get("newsletter")
                    if newsletter:
                        st.write(
                            f"**Newsletter:** "
                            f"#{newsletter.get('id')} · "
                            f"{newsletter.get('title')}"
                        )
                        st.write(
                            f"**Risk:** "
                            f"{newsletter.get('risk_level')}"
                        )

                    st.rerun()

        st.markdown("### Recent run history")

        runs_data = get_schedule_runs(schedule_id)

        if runs_data.get("error"):
            show_error(runs_data, "Loading run history")
            continue

        runs = runs_data.get("runs", [])

        if not runs:
            st.info("No runs recorded for this schedule.")
            continue

        history_rows = [
            {
                "Status": status_label(
                    run.get("status", "unknown")
                ),
                "Newsletter ID": run.get("newsletter_id"),
                "Message": run.get("message"),
                "Started": run.get("started_at"),
                "Completed": run.get("completed_at"),
                "Run key": run.get("run_key"),
            }
            for run in runs[:10]
        ]

        st.dataframe(
            history_rows,
            width="stretch",
            hide_index=True,
        )