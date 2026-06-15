import time

import streamlit as st

from modules.auth import require_login
from modules.database import get_study_sessions, get_subjects, init_db, save_study_session
from modules.ui import (
    apply_theme,
    page_header,
    render_empty_state,
    render_feature_card,
    render_success_state,
    section_title,
    sidebar_nav,
)


MODES = {
    "Focus": 25,
    "Short Break": 5,
    "Long Break": 15,
}


def _timer_key(name):
    return f"pomodoro_{name}"


def _reset_timer(mode):
    st.session_state[_timer_key("mode")] = mode
    st.session_state[_timer_key("duration")] = MODES[mode] * 60
    st.session_state[_timer_key("remaining")] = MODES[mode] * 60
    st.session_state[_timer_key("running")] = False
    st.session_state[_timer_key("started_at")] = None


def _ensure_timer():
    if _timer_key("mode") not in st.session_state:
        _reset_timer("Focus")


def _current_remaining():
    if not st.session_state.get(_timer_key("running")):
        return int(st.session_state.get(_timer_key("remaining"), 0))

    started_at = st.session_state.get(_timer_key("started_at")) or time.time()
    duration = int(st.session_state.get(_timer_key("duration"), 25 * 60))
    elapsed = int(time.time() - started_at)
    remaining = max(0, duration - elapsed)
    st.session_state[_timer_key("remaining")] = remaining
    if remaining <= 0:
        st.session_state[_timer_key("running")] = False
    return remaining


def _format_time(seconds):
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"


st.set_page_config(page_title="Pomodoro Timer - StudyMate AI", layout="wide")
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()
_ensure_timer()

page_header(
    "Pomodoro Timer",
    "Stay focused with timed study sessions and save your completed study minutes.",
    "Focus Lab",
)

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card("Focus cycles", "Use 25 minute study blocks with short breaks.", "\u23f1\ufe0f", "#14b8b4", "#d8fff6")
with feature2:
    render_feature_card("Subject tracking", "Save each completed session under a subject.", "\U0001f4da", "#2f7df6", "#e3efff")
with feature3:
    render_feature_card("Study record", "See your latest completed Pomodoro sessions.", "\U0001f4c8", "#ffb703", "#fff3c4")

subjects = get_subjects(user_id=user_id)
subject_options = {"No subject": None}
subject_options.update({subject["name"]: subject for subject in subjects})

section_title("Timer", "\u23f1\ufe0f")
with st.container(border=True):
    mode = st.radio("Mode", list(MODES.keys()), horizontal=True)
    if mode != st.session_state.get(_timer_key("mode")):
        _reset_timer(mode)

    selected_subject_name = st.selectbox("Subject", list(subject_options.keys()))
    selected_subject = subject_options[selected_subject_name]
    notes = st.text_input("Session note", placeholder="Example: revised normalization examples")

    remaining = _current_remaining()
    st.markdown(
        f"""
        <div class="soft-card" style="text-align:center;">
            <span class="status-pill">{st.session_state[_timer_key('mode')]}</span>
            <h1 style="font-size:4rem; margin:0.4rem 0;">{_format_time(remaining)}</h1>
            <p class="muted">Keep this tab open while studying. Use Refresh if you want to update the countdown display.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    start_col, pause_col, reset_col, save_col = st.columns(4)
    with start_col:
        if st.button("Start", type="primary", use_container_width=True):
            st.session_state[_timer_key("duration")] = remaining or MODES[mode] * 60
            st.session_state[_timer_key("started_at")] = time.time()
            st.session_state[_timer_key("running")] = True
            st.rerun()
    with pause_col:
        if st.button("Pause", use_container_width=True):
            st.session_state[_timer_key("remaining")] = _current_remaining()
            st.session_state[_timer_key("running")] = False
            st.rerun()
    with reset_col:
        if st.button("Reset", use_container_width=True):
            _reset_timer(mode)
            st.rerun()
    with save_col:
        if st.button("Save Session", use_container_width=True):
            duration_minutes = MODES[mode] if remaining == 0 else max(1, int((MODES[mode] * 60 - remaining) / 60))
            session_id = save_study_session(
                user_id=user_id,
                subject_id=selected_subject["id"] if selected_subject else None,
                duration_minutes=duration_minutes,
                session_type=mode,
                notes=notes,
            )
            if session_id:
                render_success_state("Study session saved", f"{duration_minutes} minute(s) added to your record.")
                _reset_timer(mode)
            else:
                st.error("Could not save this study session.")

section_title("Recent Sessions", "\U0001f4c8")
sessions = get_study_sessions(user_id=user_id, limit=15)
if not sessions:
    render_empty_state(
        "No Pomodoro sessions yet.",
        "Complete and save a focus session to build your study record.",
        "\u23f1\ufe0f",
    )
else:
    for session in sessions:
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([2, 1, 2])
            with col_a:
                st.markdown(f"**{session['session_type']}**")
                st.caption(session["completed_at"])
            with col_b:
                st.metric("Minutes", session["duration_minutes"])
            with col_c:
                st.write(session["subject_name"] or "No subject")
                if session["notes"]:
                    st.caption(session["notes"])
