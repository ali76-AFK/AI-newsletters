from __future__ import annotations

import streamlit as st

from common import api_get, api_post


st.set_page_config(
    page_title="Subscribers | AI Newsletters",
    page_icon="👥",
    layout="wide",
)


def get_topics() -> list[str]:
    data = api_get("/api/subscribers/topics")
    return data if isinstance(data, list) else []


def get_subscribers() -> dict:
    return api_get("/api/subscribers")


def subscribe(
    email: str,
    name: str,
    topics: list[str],
) -> dict:
    return api_post(
        "/api/subscribers",
        json={
            "email": email,
            "name": name or None,
            "topics": topics,
        },
    )


def unsubscribe(email: str) -> dict:
    return api_post(
        "/api/subscribers/unsubscribe",
        json={"email": email},
    )


st.title("👥 Subscribers")
st.caption(
    "Manage newsletter recipients and choose the topics they receive."
)

topics = get_topics()
subscribers_data = get_subscribers()

if subscribers_data.get("error"):
    st.error(
        f"Could not load subscribers: {subscribers_data['error']}"
    )
    subscribers = []
else:
    subscribers = subscribers_data.get("subscribers", [])

form_col, table_col = st.columns([1, 2])

with form_col:
    st.subheader("Subscribe or update")

    email = st.text_input(
        "Email",
        key="subscriber_email",
    )

    name = st.text_input(
        "Name (optional)",
        key="subscriber_name",
    )

    selected_topics = st.multiselect(
        "Topics",
        options=topics,
        default=["ai_news"] if "ai_news" in topics else topics[:1],
        key="subscriber_topics",
    )

    if st.button(
        "Subscribe / Update",
        type="primary",
        key="save_subscriber",
    ):
        if not email:
            st.error("Email is required.")
        elif not selected_topics:
            st.error("Select at least one topic.")
        else:
            result = subscribe(email, name, selected_topics)

            if result.get("error"):
                st.error(f"Could not save subscriber: {result['error']}")
            else:
                st.success("Subscriber saved.")
                st.rerun()

    st.divider()
    st.subheader("Unsubscribe")

    unsubscribe_email = st.text_input(
        "Email to unsubscribe",
        key="unsubscribe_email",
    )

    if st.button(
        "Unsubscribe",
        key="unsubscribe_subscriber",
    ):
        if not unsubscribe_email:
            st.error("Email is required.")
        else:
            result = unsubscribe(unsubscribe_email)

            if result.get("error"):
                st.error(
                    f"Could not unsubscribe: {result['error']}"
                )
            else:
                st.success("Subscriber unsubscribed.")
                st.rerun()

with table_col:
    st.subheader("Current subscribers")

    if not subscribers:
        st.info("No subscribers yet.")
    else:
        rows = []

        for subscriber in subscribers:
            rows.append(
                {
                    "Email": subscriber.get("email"),
                    "Name": subscriber.get("name"),
                    "Active": subscriber.get("is_active"),
                    "Topics": ", ".join(
                        subscriber.get("topics", [])
                    ),
                }
            )

        st.dataframe(rows, width="stretch")