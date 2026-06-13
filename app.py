import streamlit as st

from modules.database import init_db
from modules.ui import apply_theme, page_header, sidebar_nav


st.set_page_config(
    page_title="StudyMate AI",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
apply_theme()
sidebar_nav()

page_header(
    "StudyMate AI",
    "A local study assistant for notes, quizzes, flashcards, and revision planning.",
    "Offline AI Study Workspace",
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
    "Gemini is the default AI provider. Add your API key in AI Settings, `.env`, "
    "Streamlit secrets, or an environment variable. Ollama and Demo Mode are also available."
)
