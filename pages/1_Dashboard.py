import streamlit as st

from modules.database import create_subject, get_dashboard_counts, get_subjects, init_db


st.set_page_config(page_title="Dashboard - StudyMate AI", page_icon="📚", layout="wide")
init_db()

st.sidebar.title("StudyMate AI")
st.sidebar.page_link("pages/1_Dashboard.py", label="Dashboard")
st.sidebar.page_link("pages/2_Upload_Notes.py", label="Upload Notes")
st.sidebar.page_link("pages/3_Chat_With_Notes.py", label="Chat With Notes")
st.sidebar.page_link("pages/4_Quiz_Mode.py", label="Quiz Mode")
st.sidebar.page_link("pages/5_Flashcards.py", label="Flashcards")
st.sidebar.page_link("pages/6_Revision_Planner.py", label="Revision Planner")

st.title("Dashboard")
st.caption("Create subjects and track your local study library.")

counts = get_dashboard_counts()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Subjects", counts["subjects"])
col2.metric("PDFs", counts["documents"])
col3.metric("Flashcards", counts["flashcards"])
col4.metric("Quiz Attempts", counts["quizzes"])

st.divider()

left, right = st.columns([1, 2])

with left:
    st.subheader("Create Subject")
    with st.form("create_subject_form", clear_on_submit=True):
        name = st.text_input("Subject name", placeholder="Example: Biology")
        description = st.text_area("Description", placeholder="Optional notes about this subject")
        submitted = st.form_submit_button("Create Subject", use_container_width=True)

    if submitted:
        if not name.strip():
            st.warning("Please enter a subject name.")
        elif create_subject(name, description):
            st.success(f"Created subject: {name.strip()}")
        else:
            st.error("A subject with this name already exists.")

with right:
    st.subheader("Your Subjects")
    subjects = get_subjects()

    if not subjects:
        st.info("No subjects yet. Create your first subject to begin.")
    else:
        for subject in subjects:
            with st.container(border=True):
                st.markdown(f"### {subject['name']}")
                if subject["description"]:
                    st.write(subject["description"])
                st.caption(f"Created: {subject['created_at']}")

