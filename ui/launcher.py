from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="AI Newsletters",
    page_icon="📰",
    layout="wide",
)

pages = [
    st.Page(
        "pages/1_Dashboard.py",
        title="Dashboard",
        icon="🏠",
        default=True,
    ),
    st.Page(
        "pages/2_Subscribers.py",
        title="Subscribers",
        icon="👥",
    ),
    st.Page(
        "pages/3_Delivery_Schedules.py",
        title="Newsletter delivery schedule",
        icon="🗓️",
    ),
    st.Page(
        "pages/4_Newsletter_Drafts.py",
        title="Newsletter drafts",
        icon="📝",
    ),
    st.Page(
        "pages/5_Human_Review.py",
        title="Human review queue",
        icon="🔎",
    ),
    st.Page(
        "pages/6_Automation.py",
        title="Automation – create from source",
        icon="⚙️",
    ),
]

navigation = st.navigation(pages)
navigation.run()
