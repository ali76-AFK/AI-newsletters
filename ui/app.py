from __future__ import annotations

import os
from typing import List, Optional, Any

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
GROQ_MODEL = os.getenv("GROQ_MODEL", "")


def api_request(method: str, path: str, json_body: dict | None = None, timeout: int = 10) -> dict[str, Any]:
    url = f"{BACKEND_URL}{path}"
    try:
        resp = requests.request(method, url, json=json_body, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}

    text = (resp.text or "").strip()

    if not text:
        if resp.status_code >= 400:
            return {"error": f"HTTP {resp.status_code} with empty response"}
        return {"status": "ok"}

    try:
        data = resp.json()
    except Exception:
        if resp.status_code >= 400:
            return {"error": text}
        return {"text": text}

    if resp.status_code >= 400:
        return {"error": data.get("detail") if isinstance(data, dict) and "detail" in data else data}

    return data


def api_get(path: str, timeout: int = 5) -> dict | Any:
    return api_request("GET", path, timeout=timeout)


def api_post(path: str, json: dict | None = None, timeout: int = 10) -> dict | Any:
    return api_request("POST", path, json_body=json, timeout=timeout)


def get_health() -> dict | None:
    return api_get("/health")


def get_topics() -> List[str]:
    data = api_get("/api/subscribers/topics")
    if isinstance(data, list):
        return data
    return []


def get_subscribers() -> dict | None:
    return api_get("/api/subscribers")


def subscribe(email: str, name: str | None, topics: List[str]) -> dict | None:
    return api_post("/api/subscribers", json={"email": email, "name": name or None, "topics": topics})


def unsubscribe(email: str) -> dict | None:
    return api_post("/api/subscribers/unsubscribe", json={"email": email})


def get_newsletters() -> dict | None:
    return api_get("/api/newsletters")


def create_newsletter(title: str, topic: str, body: str) -> dict | None:
    return api_post("/api/newsletters", json={"title": title, "topic": topic, "body": body})


def classify_and_store_newsletter(newsletter_id: int) -> dict | None:
    return api_post(f"/api/newsletters/{newsletter_id}/classify-and-store")


def approve_newsletter(newsletter_id: int) -> dict | None:
    return api_post(f"/api/newsletters/{newsletter_id}/approve")


def run_newsletter_workflow(newsletter_id: int) -> dict | None:
    return api_post(f"/api/workflows/newsletter/{newsletter_id}/run")


def get_drafts_for_newsletter(newsletter_id: int) -> dict | None:
    return api_get(f"/api/drafts/newsletter/{newsletter_id}")


def ai_classify_newsletter(newsletter_id: int) -> dict | None:
    return api_post(f"/api/ai/newsletters/{newsletter_id}/classify")


def ai_summarize_newsletter(newsletter_id: int) -> dict | None:
    return api_post(f"/api/ai/newsletters/{newsletter_id}/summarize")


def ai_refine_draft(draft_id: int) -> dict | None:
    return api_post(f"/api/ai/drafts/{draft_id}/refine")


def render_status_card(label: str, value: str, subvalue: str | None = None, value_class: str = "metric-badge-ok") -> None:
    st.markdown(
        f'''
        <div class="card">
            <div class="metric-label">{label}</div>
            <div class="metric-value {value_class}">{value}</div>
            {"<div class='metric-subvalue'>" + subvalue + "</div>" if subvalue else ""}
        </div>
        ''',
        unsafe_allow_html=True,
    )



def render_header() -> None:
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
            padding: 18px 18px 16px 18px;
            border: 1px solid #1f2937;
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            gap: 10px;
        }
        .metric-label {
            font-size: 13px;
            color: #9ca3af;
            line-height: 1.2;
            margin: 0;
        }
        .metric-value {
            font-size: 22px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.2;
            margin: 0;
        }
        .metric-subvalue {
            font-size: 14px;
            color: #cbd5e1;
            line-height: 1.3;
            margin: 0;
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
        .metric-pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: #111827;
            border: 1px solid #263244;
            color: #e5e7eb;
            font-size: 12px;
            margin-top: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="hero-title">
            AI newsletters
        </div>
        <div class="hero-subtitle">
            Local-first, agentic newsletter orchestration with LangGraph-ready workflows.
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Newsletter Orchestrator", page_icon="📧", layout="wide")

    render_header()

    health = get_health()
    columns = st.columns(3)

    backend_status = "unknown"
    db_status = "unknown"

    if isinstance(health, dict):
        backend_status = health.get("status", "unknown")
        db_status = health.get("db", "unknown")

    backend_color_class = "metric-badge-ok" if backend_status == "ok" else "metric-badge-warn"
    db_color_class = "metric-badge-ok" if db_status in ("healthy", True) else "metric-badge-error"

    provider_label = LLM_PROVIDER.lower()
    if provider_label == "mock":
        provider_text = "Mock (deterministic)"
    elif provider_label == "ollama":
        provider_text = "Ollama (local)"
    elif provider_label == "groq":
        provider_text = f"Groq ({GROQ_MODEL})" if GROQ_MODEL else "Groq"
    else:
        provider_text = f"Provider: {LLM_PROVIDER}"

    phase_text = " – Groq integration" if provider_label == "groq" else " – "


    with columns[0]:
        render_status_card(
            "Backend status",
            "OK" if backend_status == "ok" else backend_status.upper(),
            "Backend API is reachable" if backend_status == "ok" else "Check backend connectivity",
            "metric-badge-ok" if backend_status == "ok" else "metric-badge-warn",
        )

    with columns[1]:
        render_status_card(
            "DB status",
            "Healthy" if db_status in ("healthy", True) else "Unhealthy",
            "PostgreSQL connection status",
            "metric-badge-ok" if db_status in ("healthy", True) else "metric-badge-error",
        )

    with columns[2]:
        render_status_card(
            "Phase & AI provider",
            phase_text,
            provider_text,
            "metric-badge-ok",
        )

    st.write("")
    st.write("")

    # The rest of the file continues with Subscribe, Subscribers, Newsletter drafts, etc.
    # (We will append UI polish for AI outputs below.)

    topics = get_topics()
    subscribers_data = get_subscribers()
    subscribers = subscribers_data.get("subscribers", []) if isinstance(subscribers_data, dict) else []

    col_form, col_table = st.columns([1, 2])

    with col_form:
        st.subheader("Subscribe")

        email = st.text_input("Email")
        name = st.text_input("Name (optional)")

        selected_topics = st.multiselect(
            "Topics",
            options=topics,
            default=topics[:2] if topics else [],
        )

        if st.button("Subscribe / Update", type="primary"):
            if not email:
                st.error("Email is required.")
            else:
                result = subscribe(email, name, selected_topics)
                if result and "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.success("Subscriber saved. Refresh the page to see updates.")

        st.subheader("Unsubscribe")
        unsub_email = st.text_input("Email to unsubscribe")

        if st.button("Unsubscribe"):
            if not unsub_email:
                st.error("Email is required.")
            else:
                result = unsubscribe(unsub_email)
                if result and "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.success("Subscriber unsubscribed (if existed).")

    with col_table:
        st.subheader("Subscribers")

        if not subscribers:
            st.info("No subscribers yet.")
        else:
            table_rows = []
            for s in subscribers:
                topics_str = ", ".join(s.get("topics", []))
                table_rows.append(
                    {
                        "Email": s.get("email"),
                        "Name": s.get("name"),
                        "Active": s.get("is_active"),
                        "Topics": topics_str,
                    }
                )
            st.dataframe(table_rows, width="stretch")

    st.write("")
    st.write("---")
    st.subheader("Newsletter drafts")

    st.write("")
    st.write("---")
    st.subheader("Automation – create from source")

    auto_source = st.text_input("News source (e.g., Spiegel, Guardian)")
    auto_topic = st.selectbox("Automation topic", options=topics)

    if st.button("Create, classify, approve & run from source"):
        if not auto_source or not auto_topic:
            st.error("Source and topic are required.")
        else:
            result = api_post(
                "/api/automation/create_newsletter_from_source",
                json={"source": auto_source, "topic": auto_topic},
            )
            if result and "error" in result:
                st.error(f"Error: {result['error']}")
            elif isinstance(result, dict) and result.get("detail"):
                st.error(f"Error: {result['detail']}")
            else:
                st.success(
                    f"Automation created newsletter #{result.get('newsletter_id')} from source '{auto_source}'."
                )
                st.write(
                    f"Risk level: {result.get('risk_level')} | auto-approved: {result.get('auto_approved')}"
                )
                with st.expander("Automation result (JSON)"):
                    st.json(result)



    newsletters_data = get_newsletters()
    newsletters = newsletters_data.get("newsletters", []) if isinstance(newsletters_data, dict) else []

    col_news_form, col_news_table = st.columns([1, 2])

    with col_news_form:
        title = st.text_input("Newsletter title")
        topic = st.selectbox(
            "Newsletter topic",
            options=topics,
            index=0 if topics else None,
        )
        body = st.text_area("Newsletter body", height=200)

        if st.button("Create newsletter draft", type="primary"):
            if not title or not topic or not body:
                st.error("Title, topic, and body are required.")
            else:
                result = create_newsletter(title, topic, body)
                if result and "error" in result:
                    st.error(f"Error: {result['error']}")
                elif isinstance(result, dict) and result.get("detail"):
                    st.error(f"Error: {result['detail']}")
                else:
                    st.success("Newsletter draft created. Refresh to see in the list.")

    with col_news_table:
        if not newsletters:
            st.info("No newsletters yet.")
        else:
            n_rows = []
            ids = []
            for n in newsletters:
                nid = n.get("id")
                ids.append(nid)
                n_rows.append(
                    {
                        "ID": nid,
                        "Title": n.get("title"),
                        "Topic": n.get("topic"),
                        "Status": n.get("status"),
                        "Risk": n.get("risk_level"),
                        "Approved": n.get("approved"),
                    }
                )
            st.dataframe(n_rows, width="stretch")

            st.write("")
            st.subheader("Run workflow & AI helpers")

            selected_id: Optional[int] = None
            if ids:
                selected_id = st.selectbox(
                    "Select newsletter ID",
                    options=ids,
                    format_func=lambda x: f"Newsletter #{x}",
                )

            drafts = []
            latest_draft_id: Optional[int] = None

            if selected_id is not None:
                drafts_resp = get_drafts_for_newsletter(selected_id)
                if drafts_resp and isinstance(drafts_resp, dict):
                    drafts = drafts_resp.get("drafts", [])
                    if drafts:
                        latest_draft_id = drafts[0]["id"]

            # Classification & approval
            if st.button("Classify & store risk"):
                if selected_id is None:
                    st.error("No newsletter selected.")
                else:
                    result = classify_and_store_newsletter(selected_id)
                    if result and "classification" in result:
                        c = result["classification"]
                        risk_text = c.get("risk_level", "unknown")
                        topic_text = c.get("topic", "unknown")
                        reason_text = c.get("reason", "")
                        st.success(f"Risk classification stored: {risk_text} (topic: {topic_text}).")
                        st.write(reason_text)
                        with st.expander("Raw classification (JSON)"):
                            st.json(c)
                    else:
                        st.error(f"Error: {result}")

            if st.button("Approve newsletter"):
                if selected_id is None:
                    st.error("No newsletter selected.")
                else:
                    result = approve_newsletter(selected_id)
                    if result and "status" in result and result["status"] == "ok":
                        st.success("Newsletter approved.")
                    elif result and "detail" in result:
                        st.error(f"Error: {result['detail']}")
                    else:
                        st.error(f"Error: {result}")

            if st.button("Run deterministic workflow"):
                if selected_id is None:
                    st.error("No newsletter selected.")
                else:
                    result = run_newsletter_workflow(selected_id)
                    if result and "error" in result:
                        st.error(f"Error: {result['error']}")
                    elif isinstance(result, dict) and result.get("detail"):
                        st.error(f"Error: {result['detail']}")
                    else:
                        st.success("Workflow executed successfully.")
                        summary = result.get("result", {})
                        st.write(
                            f"Newsletter {summary.get('newsletter_id')} "
                            f"workflow {summary.get('workflow_id')} created {summary.get('created_drafts')} draft(s) "
                            f"for {summary.get('subscriber_count')} subscriber(s)."
                        )
                        send_summary = summary.get("send_summary")
                        if send_summary:
                            st.write(
                                f"Simulated send: {send_summary.get('count',0)} email(s) "
                                f"from {send_summary.get('sender')} "
                                f"with subject '{send_summary.get('subject')}'."
                            )
                            with st.expander("Simulated recipients"):
                                st.write("\n".join(send_summary.get("recipients", [])))

                        with st.expander("Raw workflow result (JSON)"):
                            st.json(result)

                        drafts_resp = get_drafts_for_newsletter(selected_id)
                        if drafts_resp and isinstance(drafts_resp, dict):
                            ds = drafts_resp.get("drafts", [])
                            if ds:
                                st.subheader("Draft emails")
                                st.dataframe(ds, width="stretch")

            st.write("")
            st.subheader("AI suggestions")

            if selected_id is not None:
                # AI classification suggestion
                if st.button("Classify (suggestion)"):
                    cls = ai_classify_newsletter(selected_id)
                    if cls and "classification" in cls:
                        c = cls["classification"]
                        st.write(f"Suggested risk: {c.get('risk_level','unknown')} (topic: {c.get('topic','unknown')}).")
                        st.write(c.get("reason",""))
                        with st.expander("Suggested classification (JSON)"):
                            st.json(c)
                    else:
                        st.error(f"Error: {cls}")

                # AI summary suggestion
                if st.button("Summarize newsletter"):
                    summ = ai_summarize_newsletter(selected_id)
                    if summ and "summary" in summ:
                        st.text_area("AI summary (not stored)", summ["summary"], height=150)
                    else:
                        st.error(f"Error: {summ}")

                # AI draft refinement suggestion
                if latest_draft_id is not None and st.button("Refine latest draft"):
                    refined = ai_refine_draft(latest_draft_id)
                    if refined and "refined" in refined:
                        r = refined["refined"]
                        st.write(f"Suggested subject: {r.get('subject')}")
                        st.text_area("Suggested body (not stored)", r.get("body",""), height=200)
                        with st.expander("Suggested refined draft (JSON)"):
                            st.json(r)
                    else:
                        st.error(f"Error: {refined}")
            else:
                st.info("Select a newsletter to use AI helpers.")

if __name__ == "__main__":
    main()
