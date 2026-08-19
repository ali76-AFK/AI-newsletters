from __future__ import annotations

import streamlit as st

from common import api_get, api_post, get_topics


st.set_page_config(
    page_title="Newsletter drafts | AI Newsletters",
    page_icon="📝",
    layout="wide",
)


def list_newsletters() -> dict:
    return api_get("/api/newsletters")


def create_newsletter(payload: dict) -> dict:
    return api_post(
        "/api/newsletters",
        json=payload,
        timeout=60,
    )


def classify_and_store(newsletter_id: int) -> dict:
    return api_post(
        f"/api/newsletters/{newsletter_id}/classify-and-store",
        timeout=60,
    )


def summarize_newsletter(newsletter_id: int) -> dict:
    return api_post(
        f"/api/ai/newsletters/{newsletter_id}/summarize",
        timeout=60,
    )


def classify_preview(newsletter_id: int) -> dict:
    return api_post(
        f"/api/ai/newsletters/{newsletter_id}/classify",
        timeout=60,
    )


def run_workflow(newsletter_id: int) -> dict:
    return api_post(
        f"/api/workflows/newsletter/{newsletter_id}/run",
        timeout=60,
    )


def get_drafts(newsletter_id: int) -> dict:
    return api_get(f"/api/drafts/newsletter/{newsletter_id}")


def show_error(result: dict, action: str) -> None:
    detail = result.get("error") or result.get("detail") or "Unknown error"
    st.error(f"{action} failed: {detail}")


st.title("📝 Newsletter drafts")
st.caption(
    "Create a draft, use AI helpers, classify risk, and run the controlled "
    "newsletter workflow. High-risk content is routed to Human Review."
)

topics = get_topics()
if not topics:
    st.error("No newsletter topics are available from the backend.")
    st.stop()

st.subheader("Create a newsletter draft")

with st.form("create_newsletter_form", clear_on_submit=True):
    title = st.text_input(
        "Title",
        placeholder="e.g., AI research collaboration highlights",
    )

    create_col_1, create_col_2 = st.columns(2)

    with create_col_1:
        topic = st.selectbox(
            "Topic",
            options=topics,
        )

        source = st.text_input(
            "Source",
            placeholder="e.g., Spiegel",
        )

    with create_col_2:
        source_url = st.text_input(
            "Source URL (optional)",
            placeholder="https://example.com/article",
        )

        source_external_id = st.text_input(
            "External source ID (optional)",
            placeholder="e.g., article-2026-08-19",
        )

    body = st.text_area(
        "Newsletter body",
        placeholder=(
            "Write the newsletter content here. "
            "This content will be used by classification and AI helpers."
        ),
        height=240,
    )

    submitted = st.form_submit_button(
        "Create newsletter draft",
        type="primary",
    )

if submitted:
    if not title.strip():
        st.error("Title is required.")
    elif not body.strip():
        st.error("Newsletter body is required.")
    else:
        payload = {
            "title": title.strip(),
            "topic": topic,
            "body": body.strip(),
            "source": source.strip() or None,
            "source_external_id": source_external_id.strip() or None,
            "source_url": source_url.strip() or None,
        }

        with st.spinner("Creating newsletter draft..."):
            result = create_newsletter(payload)

        if result.get("error"):
            show_error(result, "Draft creation")
        else:
            newsletter_id = result.get("id")
            st.session_state["selected_newsletter_id"] = newsletter_id
            st.success(f"Newsletter #{newsletter_id} created.")
            st.rerun()

st.divider()
st.subheader("Existing newsletters")

newsletters_data = list_newsletters()

if newsletters_data.get("error"):
    show_error(newsletters_data, "Newsletter list")
    st.stop()

newsletters = newsletters_data.get("newsletters", [])

if not newsletters:
    st.info("No newsletters exist yet. Create one above.")
    st.stop()

newsletter_options = {
    (
        f"#{item['id']} · {item['title']} "
        f"({item.get('topic', 'unknown')} · "
        f"{item.get('risk_level', 'unknown')} risk · "
        f"{item.get('status', 'unknown')})"
    ): item
    for item in newsletters
}

selected_default = st.session_state.get("selected_newsletter_id")

labels = list(newsletter_options.keys())
default_index = 0

if selected_default is not None:
    for index, item in enumerate(newsletter_options.values()):
        if item["id"] == selected_default:
            default_index = index
            break

selected_label = st.selectbox(
    "Select a newsletter",
    options=labels,
    index=default_index,
)

newsletter = newsletter_options[selected_label]
newsletter_id = newsletter["id"]
st.session_state["selected_newsletter_id"] = newsletter_id

metric_1, metric_2, metric_3, metric_4 = st.columns(4)

with metric_1:
    st.metric("Newsletter ID", newsletter_id)

with metric_2:
    st.metric("Status", newsletter.get("status", "unknown"))

with metric_3:
    st.metric("Risk level", newsletter.get("risk_level", "unknown"))

with metric_4:
    st.metric(
        "Approved",
        "Yes" if newsletter.get("approved") else "No",
    )

st.divider()
st.subheader("AI and workflow actions")

st.info(
    "Classification determines the safety route. "
    "Do not use the workflow action for high-risk material until it has been "
    "handled through the Human Review queue."
)

helper_col, workflow_col = st.columns(2)

with helper_col:
    if st.button(
        "Preview AI classification",
        key=f"classify_preview_{newsletter_id}",
    ):
        with st.spinner("Generating classification preview..."):
            result = classify_preview(newsletter_id)

        if result.get("error"):
            show_error(result, "Classification preview")
        else:
            classification = result.get("classification", {})
            st.success("Classification preview generated.")
            st.write(
                f"**Risk level:** {classification.get('risk_level', 'unknown')}"
            )
            st.write(
                f"**Reason:** {classification.get('reason', 'No reason returned.')}"
            )

    if st.button(
        "Classify and store risk",
        type="primary",
        key=f"classify_store_{newsletter_id}",
    ):
        with st.spinner("Classifying and storing risk..."):
            result = classify_and_store(newsletter_id)

        if result.get("error"):
            show_error(result, "Classification")
        else:
            classification = result.get("classification", {})
            st.success(
                "Classification stored: "
                f"{classification.get('risk_level', 'unknown')} risk."
            )
            st.write(
                classification.get("reason", "No reason returned.")
            )
            st.rerun()

    if st.button(
        "Generate AI summary",
        key=f"summarize_{newsletter_id}",
    ):
        with st.spinner("Generating summary..."):
            result = summarize_newsletter(newsletter_id)

        if result.get("error"):
            show_error(result, "Summary generation")
        else:
            st.success("Summary generated.")
            st.text_area(
                "AI summary",
                value=result.get("summary", ""),
                height=180,
                disabled=True,
                key=f"summary_result_{newsletter_id}",
            )

with workflow_col:
    risk_level = newsletter.get("risk_level", "unknown").lower()

    workflow_disabled = risk_level in {"high", "critical"}

    if workflow_disabled:
        st.warning(
            "Workflow run is disabled for high/critical-risk content. "
            "Use Human Review after classification."
        )

    if st.button(
        "Run controlled workflow",
        type="primary",
        disabled=workflow_disabled,
        key=f"run_workflow_{newsletter_id}",
    ):
        with st.spinner("Running the controlled workflow..."):
            result = run_workflow(newsletter_id)

        if result.get("error"):
            show_error(result, "Workflow")
        else:
            workflow_result = result.get("result", {})
            st.success("Workflow completed.")

            st.write(
                f"Created drafts: {workflow_result.get('created_drafts', 0)}"
            )
            st.write(
                f"Matched subscribers: "
                f"{workflow_result.get('subscriber_count', 0)}"
            )

            send_summary = workflow_result.get("send_summary")

            if send_summary:
                st.success(
                    f"Simulated send completed for "
                    f"{send_summary.get('count', 0)} recipient(s)."
                )
                st.write(
                    f"**Subject:** {send_summary.get('subject', '')}"
                )
            else:
                st.info(
                    "The workflow completed without a send summary. "
                    "The newsletter may require approval or review."
                )

            with st.expander("Workflow result"):
                st.json(result)

st.divider()
st.subheader("Recipient drafts")

drafts_data = get_drafts(newsletter_id)

if drafts_data.get("error"):
    show_error(drafts_data, "Recipient draft lookup")
else:
    drafts = drafts_data.get("drafts", [])

    if not drafts:
        st.info(
            "No recipient drafts exist yet. "
            "Run the workflow to create or refresh recipient drafts."
        )
    else:
        st.caption(f"{len(drafts)} recipient draft(s) found.")

        st.dataframe(
            drafts,
            width="stretch",
            hide_index=True,
        )

        draft_choices = {
            (
                f"Draft #{item['id']} · "
                f"{item.get('subscriber_email') or 'No subscriber'} · "
                f"{item.get('status', 'unknown')}"
            ): item
            for item in drafts
        }

        selected_draft_label = st.selectbox(
            "Select a recipient draft for AI refinement",
            options=list(draft_choices.keys()),
        )

        selected_draft = draft_choices[selected_draft_label]
        selected_draft_id = selected_draft["id"]

        if st.button(
            "Suggest AI refinement",
            key=f"refine_draft_{selected_draft_id}",
        ):
            with st.spinner("Generating refinement suggestion..."):
                result = api_post(
                    f"/api/ai/drafts/{selected_draft_id}/refine",
                    timeout=60,
                )

            if result.get("error"):
                show_error(result, "Draft refinement")
            else:
                refined = result.get("refined", {})

                st.success("AI refinement suggestion generated.")

                st.text_input(
                    "Suggested subject",
                    value=refined.get("subject", ""),
                    disabled=True,
                    key=f"refined_subject_{selected_draft_id}",
                )

                st.text_area(
                    "Suggested body",
                    value=refined.get("body", ""),
                    height=240,
                    disabled=True,
                    key=f"refined_body_{selected_draft_id}",
                )