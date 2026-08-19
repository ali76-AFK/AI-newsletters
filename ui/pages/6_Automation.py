from __future__ import annotations

import streamlit as st

from common import api_get, api_post, get_topics


st.set_page_config(
    page_title="Automation | AI Newsletters",
    page_icon="⚙️",
    layout="wide",
)


def get_automation_status() -> dict:
    return api_get("/api/automation/status")


def start_automation() -> dict:
    return api_post("/api/automation/start")


def stop_automation() -> dict:
    return api_post("/api/automation/stop")


def run_automation_tick() -> dict:
    return api_post(
        "/api/automation/tick",
        timeout=60,
    )


def create_newsletter_from_source(
    source: str,
    topic: str,
) -> dict:
    return api_post(
        "/api/automation/create_newsletter_from_source",
        json={
            "source": source,
            "topic": topic,
        },
        timeout=60,
    )


st.title("⚙️ Automation – create from source")
st.caption(
    "Run one controlled automation cycle at a time. "
    "Safeguards enforce duplicate prevention, cooldowns, "
    "daily limits, and human review for high-risk content."
)

status_data = get_automation_status()

if status_data.get("error"):
    st.error(
        f"Could not load automation status: {status_data['error']}"
    )
    st.stop()

automation_status = status_data.get("status", "unknown")
halt_reason = status_data.get("halt_reason")

if automation_status == "running":
    st.success("● Automation is running")
elif automation_status == "halted_for_review":
    st.error("● Automation is halted for human review")
elif automation_status == "stopped":
    st.warning("● Automation is stopped")
else:
    st.error("● Automation status unavailable")

if halt_reason:
    st.warning(f"Halt reason: {halt_reason}")

control_col, details_col = st.columns([1, 2])

with control_col:
    start_disabled = automation_status == "running"

    if st.button(
        "Start automation",
        type="primary",
        disabled=start_disabled,
    ):
        result = start_automation()

        if result.get("error"):
            st.error(
                f"Could not start automation: {result['error']}"
            )
        else:
            st.success("Automation started.")
            st.rerun()

    stop_disabled = automation_status != "running"

    if st.button(
        "Stop automation",
        disabled=stop_disabled,
    ):
        result = stop_automation()

        if result.get("error"):
            st.error(
                f"Could not stop automation: {result['error']}"
            )
        else:
            st.warning("Automation stopped.")
            st.rerun()

with details_col:
    last_run_at = status_data.get("last_run_at") or "Never"
    last_newsletter_id = (
        status_data.get("last_newsletter_id") or "None"
    )
    daily_send_count = status_data.get("daily_send_count", 0)
    daily_send_limit = status_data.get("daily_send_limit", 3)

    st.info(
        f"Last automated run: {last_run_at}\n\n"
        f"Last automated newsletter: {last_newsletter_id}\n\n"
        f"Today: {daily_send_count}/{daily_send_limit} "
        "automated sends"
    )

st.divider()
st.subheader("Run one safe automation tick")

if st.button(
    "Run one automation tick",
    type="primary",
    disabled=automation_status != "running",
):
    with st.spinner("Running one controlled automation cycle..."):
        result = run_automation_tick()

    if result.get("error"):
        st.error(f"Automation tick failed: {result['error']}")

    elif result.get("status") == "skipped_no_new_articles":
        st.info(
            result.get(
                "message",
                "No new articles are available.",
            )
        )
        with st.expander("Tick result"):
            st.json(result)

    elif result.get("status") == "halted_for_review":
        st.error(
            result.get(
                "message",
                "Automation halted for human review.",
            )
        )
        with st.expander("Tick result"):
            st.json(result)
        st.rerun()

    elif result.get("status") == "skipped":
        st.warning(
            result.get(
                "message",
                "Automation is stopped.",
            )
        )

    else:
        newsletter = result.get("newsletter", {})

        st.success(
            "Tick completed: "
            f"newsletter #{newsletter.get('newsletter_id')} "
            "was created."
        )
        st.write(
            f"Risk: {newsletter.get('risk_level')} · "
            f"Auto-approved: {newsletter.get('auto_approved')}"
        )

        with st.expander("Tick result"):
            st.json(result)

        st.rerun()

st.divider()
st.subheader("Create newsletter from source")

topics = get_topics()

source = st.text_input(
    "News source",
    placeholder="e.g., Spiegel",
)

topic = st.selectbox(
    "Newsletter topic",
    options=topics,
)

if st.button("Create, classify, approve & run"):
    if not source:
        st.error("News source is required.")
    elif not topic:
        st.error("Newsletter topic is required.")
    else:
        with st.spinner(
            "Creating, classifying, approving, and running workflow..."
        ):
            result = create_newsletter_from_source(
                source,
                topic,
            )

        if result.get("error"):
            st.error(
                f"Source automation failed: {result['error']}"
            )
        else:
            st.success(
                f"Newsletter #{result.get('newsletter_id')} created."
            )
            st.write(
                f"Risk: {result.get('risk_level')} · "
                f"Auto-approved: {result.get('auto_approved')}"
            )

            with st.expander("Automation result"):
                st.json(result)