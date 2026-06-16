import streamlit as st

from modules.auth import require_login
from modules.database import get_branding_settings, init_db
from modules.ui import apply_theme, page_header, sidebar_nav


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
    st.markdown(
        """
        <div class="soft-card">
            <span class="status-pill">Step 1</span>
            <h3>Create subjects</h3>
            <p class="muted">Organize your study material before uploading notes.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="soft-card">
            <span class="status-pill">Step 2</span>
            <h3>Upload notes</h3>
            <p class="muted">Extract PDF text and store searchable chunks locally.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="soft-card">
            <span class="status-pill">Step 3</span>
            <h3>Study smarter</h3>
            <p class="muted">Chat, quiz yourself, review flashcards, and plan revision.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.info(
    "Gemini is the default AI provider. Add your API key in AI Settings. "
    "Ollama and Demo Mode are also available when enabled."
)

st.caption(f"{branding['footer_text']} | {branding['app_version']}")
