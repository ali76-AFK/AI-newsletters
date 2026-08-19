from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from common import api_get


load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
GROQ_MODEL = os.getenv("GROQ_MODEL", "")


st.set_page_config(
    page_title="AI Newsletters",
    page_icon="📰",
    layout="wide",
)


def render_status_card(
    label: str,
    value: str,
    subvalue: str,
    value_class: str,
) -> None:
    st.markdown(
        f"""
        <div style="
            background:#0b1020;
            border-radius:14px;
            padding:18px;
            border:1px solid #1f2937;
            min-height:120px;
        ">
            <div style="color:#9ca3af;font-size:13px;">{label}</div>
            <div style="
                color:{value_class};
                font-size:22px;
                font-weight:700;
                margin-top:10px;
            ">{value}</div>
            <div style="color:#cbd5e1;font-size:14px;margin-top:10px;">
                {subvalue}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <h1 style="text-align:center;color:#ff4b9a;">
        AI newsletters
    </h1>
    <p style="text-align:center;color:#cbd5e1;">
        Local-first, agentic newsletter orchestration with
        LangGraph-ready workflows.
    </p>
    """,
    unsafe_allow_html=True,
)

health = api_get("/health")

if isinstance(health, dict) and not health.get("error"):
    backend_status = health.get("status", "unknown")
    db_status = health.get("db", "unknown")
else:
    backend_status = "unknown"
    db_status = "unknown"

if backend_status == "ok":
    backend_value = "OK"
    backend_color = "#22c55e"
    backend_subvalue = "Backend API is reachable"
else:
    backend_value = "UNKNOWN"
    backend_color = "#f97316"
    backend_subvalue = "Check backend connectivity"

if db_status in ("healthy", True):
    db_value = "Healthy"
    db_color = "#22c55e"
else:
    db_value = "Unhealthy"
    db_color = "#ef4444"

provider = LLM_PROVIDER.lower()

if provider == "groq":
    provider_value = "– Groq integration"
    provider_subvalue = f"Groq ({GROQ_MODEL})"
else:
    provider_value = f"– {provider} integration"
    provider_subvalue = provider

col1, col2, col3 = st.columns(3)

with col1:
    render_status_card(
        "Backend status",
        backend_value,
        backend_subvalue,
        backend_color,
    )

with col2:
    render_status_card(
        "DB status",
        db_value,
        "PostgreSQL connection status",
        db_color,
    )

with col3:
    render_status_card(
        "Phase & AI provider",
        provider_value,
        provider_subvalue,
        "#22c55e",
    )

st.divider()
st.info(
    "Use the navigation menu on the left to manage subscribers, "
    "schedules, newsletters, reviews, and automation."
)
