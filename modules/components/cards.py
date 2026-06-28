"""
StudyMate AI – General Card Components
"""
import html as _html
import streamlit as st
from modules.icons import icon
from modules.theme import SUBJECT_ACCENTS, FILE_TYPE_COLORS


def render_feature_card(
    title: str,
    text: str,
    icon_name: str = "zap",
    accent: str = "#14B8A6",
    accent_bg: str = "#F0FDFA",
):
    """Render a clean feature card with icon, title, and description."""
    svg = icon(icon_name, size=22, color=accent)
    st.markdown(
        f"""
        <div class="sm-feature-card" style="--card-accent:{accent}; --card-accent-bg:{accent_bg};">
            <div class="sm-feature-icon">{svg}</div>
            <div class="sm-feature-title">{_html.escape(title)}</div>
            <div class="sm-feature-text">{_html.escape(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_subject_card(subject: dict, document_count: int = 0):
    """Render a clean subject card with deterministic accent color."""
    visual = subject_visual(subject.get("subject_name") or subject.get("name", "Subject"))
    description = subject.get("description") or "No description added yet."
    book_icon = icon("book", size=18, color=visual["accent"])
    file_icon = icon("file-text", size=12, color=visual["accent"])
    calendar_icon = icon("calendar", size=12, color="#9CA3AF")
    created = str(subject.get("created_at", ""))[:10]

    st.markdown(
        f"""
        <div class="sm-subject-card" style="--card-accent:{visual['accent']}; --card-accent-bg:{visual['bg']};">
            <div class="sm-subject-header">
                <div class="sm-subject-icon">{book_icon}</div>
                <div class="sm-subject-name">{_html.escape(subject.get('subject_name') or subject.get('name', 'Subject'))}</div>
            </div>
            <div class="sm-subject-desc">{_html.escape(description)}</div>
            <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:8px;">
                <span class="sm-pill sm-pill-teal" style="background:{visual['bg']}; color:{visual['accent']}; border-color:{visual['border']};">
                    {file_icon} {int(document_count or 0)} docs
                </span>
                <span class="sm-pill sm-pill-default">
                    {calendar_icon} {_html.escape(created)}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_progress_panel(title: str, rows: list):
    """Render a clean progress bar card."""
    rows_html = []
    for row in rows:
        label = _html.escape(str(row.get("label", "Item")))
        value = max(0, min(100, int(row.get("value", 0))))
        count = _html.escape(str(row.get("count", "")))
        accent = row.get("accent", "#14B8A6")
        rows_html.append(
            f'<div class="sm-progress-row">'
            f'<div class="sm-progress-label"><span>{label}</span><span>{count}</span></div>'
            f'<div class="sm-progress-track">'
            f'<div class="sm-progress-fill" style="width:{value}%; background:{accent};"></div>'
            f'</div></div>'
        )

    body = "".join(rows_html) if rows_html else (
        '<p style="font-size:0.875rem; color:#9CA3AF; margin:0;">No progress data yet.</p>'
    )
    st.markdown(
        f'<div class="sm-progress-card">'
        f'<div style="font-size:0.875rem; font-weight:600; color:#111827; margin-bottom:12px;">{_html.escape(title)}</div>'
        f'{body}</div>',
        unsafe_allow_html=True,
    )


def subject_visual(subject_name: str) -> dict:
    """Return deterministic accent colors for a subject name."""
    name = subject_name or "Subject"
    lowered = name.lower()
    keyword_map = [
        (["database", "dbms", "sql"], SUBJECT_ACCENTS[2]),   # blue
        (["oop", "object", "java", "c++", "python"], SUBJECT_ACCENTS[1]),  # purple
        (["dld", "digital", "logic", "circuit"], SUBJECT_ACCENTS[4]),  # orange
        (["math", "calculus", "algebra", "statistics"], SUBJECT_ACCENTS[0]),  # teal
        (["english", "communication", "writing"], SUBJECT_ACCENTS[3]),  # rose
        (["physics", "chemistry", "biology", "science"], SUBJECT_ACCENTS[5]),  # green
    ]
    for keywords, visual in keyword_map:
        if any(kw in lowered for kw in keywords):
            return visual
    index = sum(ord(c) for c in name) % len(SUBJECT_ACCENTS)
    return SUBJECT_ACCENTS[index]


def file_type_visual(file_type: str) -> dict:
    """Return color/icon data for a file type."""
    clean = (file_type or "PDF").upper()
    return FILE_TYPE_COLORS.get(
        clean,
        {"accent": "#6B7280", "bg": "#F9FAFB", "icon_key": "file-text"},
    )
