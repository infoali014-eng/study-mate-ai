import os
from pathlib import Path

import streamlit as st

from modules import ai_engine
from modules.auth import require_admin
from modules.database import (
    get_admin_overview_counts,
    get_branding_settings,
    get_recent_uploads,
    get_recent_users,
    init_db,
)
from modules.document_processor import ocr_status
from modules.ui import apply_theme, page_header, render_stat_card, section_title, sidebar_nav


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _storage_mb():
    total = 0
    if DATA_DIR.exists():
        for path in DATA_DIR.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
    return total / (1024 * 1024)


st.set_page_config(page_title="Admin Dashboard - StudyMate AI", layout="wide")
admin_id = require_admin()
init_db()
apply_theme()
sidebar_nav()

branding = get_branding_settings()
counts = get_admin_overview_counts()

page_header(
    "Admin Dashboard",
    "Manage app health, users, branding, and overall StudyMate activity.",
    "Owner Console",
)

metric_cols = st.columns(4)
with metric_cols[0]:
    render_stat_card("Users", counts["users"], "Registered accounts", "\U0001f465", "#14b8b4", "#d8fff6")
with metric_cols[1]:
    render_stat_card("Subjects", counts["subjects"], "Across all users", "\U0001f4da", "#2f7df6", "#e3efff")
with metric_cols[2]:
    render_stat_card("Documents", counts["documents"], "Uploaded materials", "\U0001f4c4", "#ff637d", "#ffe3e9")
with metric_cols[3]:
    render_stat_card("Quizzes", counts["quizzes"], "Total attempts", "\u2754", "#8b5cf6", "#efe7ff")

metric_cols2 = st.columns(4)
with metric_cols2[0]:
    render_stat_card("Flashcards", counts["flashcards"], "Saved cards", "\U0001f0cf", "#ffb703", "#fff3c4")
with metric_cols2[1]:
    render_stat_card("Revision Plans", counts["revision_plans"], "Saved plans", "\U0001f5d3\ufe0f", "#58c84f", "#e8ffd9")
with metric_cols2[2]:
    render_stat_card("Storage", f"{_storage_mb():.1f} MB", "Local data folder", "\U0001f4be", "#2f7df6", "#e3efff")
with metric_cols2[3]:
    render_stat_card("AI Provider", ai_engine.get_selected_provider(), "Current session", "\u2728", "#14b8b4", "#d8fff6")

left, right = st.columns(2)
with left:
    section_title("Recent Users", "\U0001f465")
    for user in get_recent_users():
        with st.container(border=True):
            st.markdown(f"**{user['name']}**")
            st.caption(f"{user['email']} | {user['role']} | {'Active' if user['is_active'] else 'Disabled'} | {user['created_at']}")

with right:
    section_title("Recent Uploads", "\U0001f5c3\ufe0f")
    uploads = get_recent_uploads()
    if not uploads:
        st.info("No uploads yet.")
    for upload in uploads:
        with st.container(border=True):
            st.markdown(f"**{upload['file_name']}**")
            st.caption(f"{upload['file_type']} | {upload['subject_name']} | {upload['email']} | {upload['uploaded_at']}")

section_title("App Health", "\U0001f6e0\ufe0f")
with st.container(border=True):
    col1, col2, col3, col4 = st.columns(4)
    col1.write("Manual auth: Active")
    col2.write(f"Google login: {branding['enable_google_login']}")
    col3.write(f"Demo Mode: {branding['enable_demo_mode']}")
    col4.write(f"OCR: {ocr_status()}")
    st.write(f"Gemini configured for current admin: {'Yes' if ai_engine.get_gemini_api_key() else 'No'}")
    st.write(f"Max upload size: {os.getenv('STUDYMATE_MAX_UPLOAD_MB', '100')} MB")
    st.write("Allowed file types: PDF, PNG, JPG, JPEG, WEBP, DOCX, PPTX, XLSX, TXT, MD, CSV, JSON")
