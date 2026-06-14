import streamlit as st

from modules.auth import require_login
from modules.database import (
    create_subject,
    delete_subject,
    get_dashboard_counts,
    get_subjects,
    init_db,
)
from modules.ui import (
    apply_theme,
    page_header,
    render_empty_state,
    render_stat_card,
    render_tip,
    section_title,
    sidebar_nav,
)
from modules.security import validate_description, validate_subject_name
from modules.vector_store import VectorStoreError, delete_subject_vectors


st.set_page_config(page_title="Dashboard - StudyMate AI", layout="wide")
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

page_header(
    f"Welcome back, {st.session_state.get('user_name', 'Student')} \U0001f44b",
    "Let's organize your subjects, notes, quizzes, and revision plans.",
    "Ali's Study Command Center",
)

if "subject_pending_delete" not in st.session_state:
    st.session_state.subject_pending_delete = None
if "dashboard_success" not in st.session_state:
    st.session_state.dashboard_success = ""

if st.session_state.dashboard_success:
    st.success(st.session_state.dashboard_success)
    st.session_state.dashboard_success = ""

counts = get_dashboard_counts(user_id=user_id)
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_stat_card("Subjects", counts["subjects"], "Start your first subject", "\U0001f4da", "#14b8b4", "#d8fff6")
with col2:
    render_stat_card("PDFs", counts["documents"], "Upload your notes", "\U0001f4c4", "#ff637d", "#ffe3e9")
with col3:
    render_stat_card("Flashcards", counts["flashcards"], "Create memory cards", "\U0001f0cf", "#ffb703", "#fff3c4")
with col4:
    render_stat_card("Quiz Attempts", counts["quizzes"], "Test your knowledge", "\u2754", "#8b5cf6", "#efe7ff")

left, right = st.columns([1, 2])

with left:
    section_title("Create Subject", "\u2728")
    with st.form("create_subject_form", clear_on_submit=True):
        name = st.text_input("Subject name", placeholder="Example: Biology")
        description = st.text_area(
            "Description",
            placeholder="Optional notes about this subject",
        )
        submitted = st.form_submit_button("Create Subject", use_container_width=True)

    if submitted:
        clean_name, name_error = validate_subject_name(name)
        clean_description = validate_description(description)
        if name_error:
            st.warning(name_error)
        elif create_subject(clean_name, clean_description, user_id=user_id):
            st.success(f"Created subject: {clean_name}")
        else:
            st.error("A subject with this name already exists.")

with right:
    section_title("Your Subjects", "\U0001f4da")
    subjects = get_subjects(user_id=user_id)

    if not subjects:
        render_empty_state(
            "No subjects yet.",
            "Create your first subject to begin your learning journey.",
            "\U0001f5c2\ufe0f",
        )
        render_tip("<strong>Tip:</strong> Organize your subjects to make studying smarter and more effective.")
    else:
        for subject in subjects:
            with st.container(border=True):
                subject_header, subject_action = st.columns([4, 1])

                with subject_header:
                    st.markdown(f"### {subject['name']}")
                    if subject["description"]:
                        st.write(subject["description"])
                    st.caption(f"Created: {subject['created_at']}")

                with subject_action:
                    if st.button(
                        "Delete",
                        key=f"delete_subject_{subject['id']}",
                        help="Delete this subject and its related study data",
                        use_container_width=True,
                    ):
                        st.session_state.subject_pending_delete = subject["id"]

                if st.session_state.subject_pending_delete == subject["id"]:
                    st.warning(
                        "Are you sure you want to delete this subject? This may also "
                        "remove related uploaded documents, flashcards, quiz results, "
                        "and weak topics."
                    )

                    confirm_col, cancel_col = st.columns(2)
                    with confirm_col:
                        if st.button(
                            "Yes, delete subject",
                            key=f"confirm_delete_subject_{subject['id']}",
                            use_container_width=True,
                        ):
                            try:
                                try:
                                    delete_subject_vectors(subject["id"], user_id=user_id)
                                except VectorStoreError:
                                    st.warning("Could not clean search chunks right now.")

                                deleted = delete_subject(subject["id"], user_id=user_id)

                                if deleted:
                                    st.session_state.subject_pending_delete = None
                                    st.session_state.dashboard_success = (
                                        "Subject deleted successfully."
                                    )
                                    st.rerun()
                                else:
                                    st.error("Subject was not found or was already deleted.")
                            except Exception:
                                st.error("Could not delete this subject. Please try again.")

                    with cancel_col:
                        if st.button(
                            "Cancel",
                            key=f"cancel_delete_subject_{subject['id']}",
                            use_container_width=True,
                        ):
                            st.session_state.subject_pending_delete = None
                            st.rerun()
