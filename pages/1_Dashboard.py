import html

import streamlit as st

from modules.auth import get_current_user_display_name, require_login
from modules.database import init_db

# Redefine dashboard counts for Supabase (Phase 4D)
def get_dashboard_counts(user_id):
    from modules.analytics_repository import AnalyticsRepository
    return AnalyticsRepository.get_dashboard_statistics(user_id)
from modules.library_repository import (
    create_subject,
    delete_subject,
    get_subject_document_counts,
    get_subjects,
)
from modules.ui import (
    apply_theme,
    page_header,
    render_empty_state,
    render_progress_panel,
    render_stat_card,
    render_tip,
    section_title,
    sidebar_nav,
    subject_visual,
)
from modules.security import validate_description, validate_subject_name
from modules.vector_store import VectorStoreError, delete_subject_vectors
from modules.icons import icon as _icon


st.set_page_config(page_title="Dashboard - StudyMate AI", layout="wide")
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

from modules.analytics_repository import AnalyticsRepository
AnalyticsRepository.log_activity_session(user_id, session_type="App Usage", duration_minutes=5)

page_header(
    f"Welcome back, {get_current_user_display_name()}",
    "Here's your learning overview for today.",
    "Dashboard",
)

if "subject_pending_delete" not in st.session_state:
    st.session_state.subject_pending_delete = None
if "dashboard_success" not in st.session_state:
    st.session_state.dashboard_success = ""

if st.session_state.dashboard_success:
    st.success(st.session_state.dashboard_success)
    st.session_state.dashboard_success = ""

counts = get_dashboard_counts(user_id=user_id)
subject_document_counts = get_subject_document_counts(user_id=user_id)

col1, col2, col3, col4 = st.columns(4)
with col1:
    render_stat_card("Subjects", counts["subjects"], "Start your first subject", "book", "#14B8A6", "#F0FDFA")
with col2:
    render_stat_card("Notes", counts["documents"], "Upload your notes", "file-text", "#EF4444", "#FEF2F2")
with col3:
    render_stat_card("Flashcards", counts["flashcards"], "Create memory cards", "layers", "#F59E0B", "#FFFBEB")
with col4:
    render_stat_card("Quiz Attempts", counts["quizzes"], "Test your knowledge", "help-circle", "#8B5CF6", "#F5F3FF")

st.divider()

col_i1, col_i2, col_i3, col_i4 = st.columns(4)
with col_i1:
    render_stat_card("Study Streak", f"{counts.get('current_streak', 0)} days", f"Longest: {counts.get('longest_streak', 0)} days", "flame", "#EA580C", "#FFF7ED")
with col_i2:
    render_stat_card("Quiz Accuracy", f"{counts.get('overall_accuracy', 0.0)}%", f"Level: {counts.get('study_level', 'Beginner')}", "target", "#2563EB", "#EFF6FF")
with col_i3:
    render_stat_card("Retention Score", f"{counts.get('retention_score', 0.0)}%", f"Strongest: {counts.get('strongest_subject', 'None')}", "brain", "#9333EA", "#F5F3FF")
with col_i4:
    render_stat_card("Study Time Today", f"{counts.get('study_hours_today', 0.0)} hrs", "Pomodoro Sessions", "clock", "#16A34A", "#F0FDF4")

st.divider()

ach_col, prog_col = st.columns([1, 1])
with ach_col:
    section_title("Unlocked Badges", "award")
    unlocked = counts.get("achievements", [])
    if not unlocked:
        st.info("No achievements unlocked yet. Keep studying to unlock milestone awards!")
    else:
        for ach in unlocked:
            st.success(f"**{ach}**")

with prog_col:
    if subject_document_counts:
        section_title("Study Progress", "bar-chart-2")
        max_documents = max(int(row["document_count"] or 0) for row in subject_document_counts) or 1
        progress_rows = []
        for row in subject_document_counts[:6]:
            visual = subject_visual(row["name"])
            document_count = int(row["document_count"] or 0)
            progress_rows.append(
                {
                    "label": row["name"],
                    "count": f"{document_count} material(s)",
                    "value": max(7, int((document_count / max_documents) * 100)) if document_count else 4,
                    "accent": visual["accent"],
                }
            )
        render_progress_panel("Documents per subject", progress_rows)

left, right = st.columns([1, 2])

with left:
    section_title("Create Subject", "plus")
    with st.form("create_subject_form", clear_on_submit=True):
        name = st.text_input("Subject name", placeholder="Example: Biology")
        description = st.text_area(
            "Description",
            placeholder="Optional notes about this subject",
        )
        submitted = st.form_submit_button("Create Subject", use_container_width=True, type="primary")

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
    section_title("Your Subjects", "book")
    subjects = get_subjects(user_id=user_id)

    if not subjects:
        render_empty_state(
            "No subjects yet.",
            "Create your first subject to begin your learning journey.",
            "book",
        )
        render_tip("<strong>Tip:</strong> Organize your subjects to make studying smarter and more effective.")
    else:
        for subject in subjects:
            with st.container(border=True):
                subject_header, subject_action = st.columns([5, 1])

                with subject_header:
                    document_count = next(
                        (
                            int(row["document_count"] or 0)
                            for row in subject_document_counts
                            if row["id"] == subject["id"]
                        ),
                        0,
                    )
                    visual = subject_visual(subject["name"])
                    description = subject["description"] or "No description added yet."
                    book_svg = _icon("book", size=16, color=visual["accent"])
                    file_svg = _icon("file-text", size=12, color=visual["accent"])
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:10px;padding:4px 0;">'
                        f'<div style="width:36px;height:36px;border-radius:8px;background:{visual["bg"]};display:flex;align-items:center;justify-content:center;flex-shrink:0;">{book_svg}</div>'
                        f'<div style="min-width:0;">'
                        f'<div style="font-size:0.9375rem;font-weight:600;color:#111827;">{html.escape(subject["name"])}</div>'
                        f'<div style="font-size:0.8125rem;color:#6B7280;">{html.escape(description[:80])}</div>'
                        f'<div style="margin-top:4px;">'
                        f'<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:9999px;background:{visual["bg"]};color:{visual["accent"]};font-size:0.75rem;font-weight:500;">'
                        f'{file_svg} {document_count} doc(s)</span>'
                        f'<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:9999px;background:#F9FAFB;color:#6B7280;font-size:0.75rem;font-weight:500;margin-left:6px;">'
                        f'{html.escape(str(subject["created_at"])[:10])}</span>'
                        f'</div></div></div>',
                        unsafe_allow_html=True,
                    )

                with subject_action:
                    st.write("")
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
