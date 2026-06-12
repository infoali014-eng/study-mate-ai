import streamlit as st

from modules.database import init_db


st.set_page_config(
    page_title="StudyMate AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

st.title("StudyMate AI")
st.subheader("Offline AI Study Assistant")

st.write(
    "Use the sidebar to create subjects, upload PDF notes, chat with your notes, "
    "practice quizzes, review flashcards, and plan revision."
)

st.info(
    "Before chatting, install Ollama and pull a model such as `llama3.2` "
    "or set `OLLAMA_MODEL` to the model you want to use."
)

st.sidebar.title("StudyMate AI")
st.sidebar.page_link("pages/1_Dashboard.py", label="Dashboard")
st.sidebar.page_link("pages/2_Upload_Notes.py", label="Upload Notes")
st.sidebar.page_link("pages/3_Chat_With_Notes.py", label="Chat With Notes")
st.sidebar.page_link("pages/4_Quiz_Mode.py", label="Quiz Mode")
st.sidebar.page_link("pages/5_Flashcards.py", label="Flashcards")
st.sidebar.page_link("pages/6_Revision_Planner.py", label="Revision Planner")

