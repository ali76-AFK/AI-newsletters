from __future__ import annotations

import datetime as dt

import streamlit as st

from common import (
    create_schedule,
    disable_schedule,
    enable_schedule,
    get_schedules,
    get_topics,
)


st.set_page_config(
    page_title="Delivery Schedules | AI Newsletters",
    page_icon="🗓️",
    layout="wide",
)

st.title("Newsletter delivery schedules")
st.caption(
    "Choose when newsletters should be prepared and delivered. "
    "Enabled schedules are configuration only until the scheduler phase is added."
)

topics = get_topics()

weekday_labels = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

form_col, list_col = st.columns([1, 2])

with form_col:
    st.subheader("Create schedule")

    schedule_email = st.text_input(
        "Delivery email",
        value="ali.al-kelabi@stud.th-deg.de",
    )

    schedule_name = st.text_input(
        "Schedule name",
        value="Ali",
    )

    schedule_topics = st.multiselect(
        "Topics",
        options=topics,
        default=["ai_news"] if "ai_news" in topics else topics[:1],
    )

    schedule_sources = st.multiselect(
        "News sources",
        options=["Spiegel"],
        default=["Spiegel"],
    )

    selected_day_labels = st.multiselect(
        "Update days",
        options=list(weekday_labels.values()),
        default=["Monday", "Wednesday", "Friday"],
    )

    selected_weekdays = [
        day
        for day, label in weekday_labels.items()
        if label in selected_day_labels
    ]

    schedule_time = st.time_input(
        "Delivery time",
        value=dt.time(18, 0),
    )

    schedule_timezone = st.selectbox(
        "Timezone",
        options=["Europe/Berlin", "UTC"],
    )

    schedule_enabled = st.checkbox(
        "Enable this schedule",
        value=False,
        help="The future scheduler will honor this setting.",
    )

    if st.button("Save delivery schedule", type="primary"):
        payload = {
            "email": schedule_email,
            "name": schedule_name or None,
            "topics": schedule_topics,
            "sources": schedule_sources,
            "weekdays": selected_weekdays,
            "delivery_time": schedule_time.strftime("%H:%M"),
            "timezone": schedule_timezone,
            "enabled": schedule_enabled,
        }

        result = create_schedule(payload)

        if result.get("error"):
            st.error(f"Could not save schedule: {result['error']}")
        else:
            st.success("Delivery schedule saved.")
            st.rerun()

with list_col:
    st.subheader("Saved schedules")

    schedules_data = get_schedules()
    schedules = schedules_data.get("schedules", [])

    if schedules_data.get("error"):
        st.error(f"Could not load schedules: {schedules_data['error']}")
    elif not schedules:
        st.info("No schedules have been saved.")
    else:
        rows = []

        for schedule in schedules:
            days = ", ".join(
                weekday_labels.get(day, str(day))
                for day in schedule.get("weekdays", [])
            )

            rows.append(
                {
                    "ID": schedule.get("id"),
                    "Email": schedule.get("email"),
                    "Topics": ", ".join(schedule.get("topics", [])),
                    "Sources": ", ".join(schedule.get("sources", [])),
                    "Days": days,
                    "Time": schedule.get("delivery_time"),
                    "Timezone": schedule.get("timezone"),
                    "Enabled": schedule.get("enabled"),
                    "Last run": schedule.get("last_run_at") or "Never",
                }
            )

        st.dataframe(rows, width="stretch")

        st.write("")

        for schedule in schedules:
            schedule_id = schedule["id"]
            is_enabled = schedule.get("enabled", False)

            label = (
                f"Disable schedule #{schedule_id}"
                if is_enabled
                else f"Enable schedule #{schedule_id}"
            )

            if st.button(label, key=f"schedule_toggle_{schedule_id}"):
                result = (
                    disable_schedule(schedule_id)
                    if is_enabled
                    else enable_schedule(schedule_id)
                )

                if result.get("error"):
                    st.error(
                        f"Could not update schedule #{schedule_id}: "
                        f"{result['error']}"
                    )
                else:
                    st.success(f"Schedule #{schedule_id} updated.")
                    st.rerun()
