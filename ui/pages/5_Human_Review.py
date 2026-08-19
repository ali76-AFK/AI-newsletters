from __future__ import annotations

import streamlit as st

from common import api_get, api_post


st.set_page_config(
    page_title="Human review | AI Newsletters",
    page_icon="🔎",
    layout="wide",
)


def get_pending_reviews() -> dict:
    return api_get("/api/reviews/pending")


def approve_and_send(
    newsletter_id: int,
    review_note: str,
) -> dict:
    return api_post(
        f"/api/reviews/newsletters/{newsletter_id}/approve-and-send",
        json={"review_note": review_note or None},
        timeout=60,
    )


def reject_newsletter(
    newsletter_id: int,
    review_note: str,
) -> dict:
    return api_post(
        f"/api/reviews/newsletters/{newsletter_id}/reject",
        json={"review_note": review_note or None},
    )


def resume_automation() -> dict:
    return api_post("/api/reviews/resume-automation")


st.title("🔎 Human review queue")
st.caption(
    "High-risk and critical newsletters must be reviewed before sending."
)

reviews_data = get_pending_reviews()

if reviews_data.get("error"):
    st.error(
        f"Could not load review queue: {reviews_data['error']}"
    )
    st.stop()

pending_reviews = reviews_data.get("pending_reviews", [])
pending_count = reviews_data.get("count", 0)

if pending_count:
    st.error(
        f"{pending_count} newsletter(s) require human review before sending."
    )

    for item in pending_reviews:
        newsletter_id = item["id"]
        risk_level = item.get("risk_level", "unknown").upper()

        with st.expander(
            f"Newsletter #{newsletter_id}: "
            f"{item.get('title')} ({risk_level} risk)",
            expanded=True,
        ):
            st.write(f"**Topic:** {item.get('topic')}")
            st.write(f"**Risk reason:** {item.get('risk_reason')}")
            st.write(f"**Created:** {item.get('created_at')}")

            st.text_area(
                "Newsletter content",
                value=item.get("body", ""),
                height=220,
                disabled=True,
                key=f"review_content_{newsletter_id}",
            )

            review_note = st.text_area(
                "Review note",
                placeholder=(
                    "Explain why you approve or reject this newsletter."
                ),
                key=f"review_note_{newsletter_id}",
            )

            approve_col, reject_col = st.columns(2)

            with approve_col:
                if st.button(
                    "Approve & send",
                    type="primary",
                    key=f"approve_review_{newsletter_id}",
                ):
                    with st.spinner(
                        f"Approving newsletter #{newsletter_id}..."
                    ):
                        result = approve_and_send(
                            newsletter_id,
                            review_note,
                        )

                    if result.get("error"):
                        st.error(
                            f"Approval/send failed: {result['error']}"
                        )
                    else:
                        st.success(
                            f"Newsletter #{newsletter_id} approved and sent."
                        )
                        st.rerun()

            with reject_col:
                if st.button(
                    "Reject newsletter",
                    key=f"reject_review_{newsletter_id}",
                ):
                    result = reject_newsletter(
                        newsletter_id,
                        review_note,
                    )

                    if result.get("error"):
                        st.error(
                            f"Rejection failed: {result['error']}"
                        )
                    else:
                        st.success(
                            f"Newsletter #{newsletter_id} rejected."
                        )
                        st.rerun()
else:
    st.success("No newsletters are waiting for human review.")

    if st.button(
        "Resume automation after review",
        type="primary",
        key="resume_automation_after_review",
    ):
        result = resume_automation()

        if result.get("error"):
            st.error(
                f"Could not resume automation: {result['error']}"
            )
        else:
            st.success("Automation resumed.")
            st.rerun()
