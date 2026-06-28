import streamlit as st

from modules.auth import require_login
from modules.database import get_branding_settings, init_db
from modules.ui import apply_theme, page_header, sidebar_nav, render_feature_card


st.set_page_config(
    page_title="StudyMate AI",
    layout="wide",
    initial_sidebar_state="expanded",
)

user_id = require_login()
init_db()
apply_theme()
sidebar_nav()
branding = get_branding_settings()

page_header(
    f"Welcome back, {st.session_state.get('user_name', 'Student')}",
    branding["product_tagline"],
    branding["app_subtitle"],
)

col1, col2, col3 = st.columns(3)

with col1:
    render_feature_card(
        "Create Subjects",
        "Organize your study material before uploading notes.",
        icon_name="book",
        accent="#14B8A6",
        accent_bg="#F0FDFA",
    )

with col2:
    render_feature_card(
        "Upload Notes",
        "Extract PDF text and store searchable chunks in the cloud.",
        icon_name="upload-cloud",
        accent="#3B82F6",
        accent_bg="#EFF6FF",
    )

with col3:
    render_feature_card(
        "Study Smarter",
        "Chat, quiz yourself, review flashcards, and plan revision.",
        icon_name="brain",
        accent="#8B5CF6",
        accent_bg="#F5F3FF",
    )

st.info(
    "Gemini and OpenAI API providers are available in AI Settings. "
    "Ollama Local and Demo Mode are also available when enabled."
)

st.caption(f"{branding['footer_text']} | {branding['app_version']}")
