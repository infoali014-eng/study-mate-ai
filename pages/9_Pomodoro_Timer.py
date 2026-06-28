import time

import streamlit as st
import streamlit.components.v1 as components

from modules.auth import require_login
from modules.database import init_db
from modules.library_repository import get_subjects

# Redefine study session functions for Supabase (Phase 4D)
def save_study_session(user_id, subject_id=None, duration_minutes=25, session_type="Focus", notes=""):
    from modules.supabase_client import get_supabase_admin_client
    from datetime import datetime
    from services.event_dispatcher import dispatch_event
    client = get_supabase_admin_client()
    if not client:
        return None
    try:
        data = {
            "owner_id": user_id,
            "subject_id": subject_id,
            "duration_minutes": int(duration_minutes),
            "session_type": session_type,
            "notes": notes.strip() if notes else "",
            "completed_at": datetime.utcnow().isoformat()
        }
        resp = client.table("study_sessions").insert(data).execute()
        if resp.data:
            session_uuid = resp.data[0]["id"]
            # Dispatch event
            dispatch_event("POMODORO_COMPLETED", user_id, {
                "session_id": session_uuid,
                "subject_id": subject_id,
                "duration_minutes": duration_minutes,
                "session_type": session_type
            })
            return session_uuid
        return None
    except Exception as e:
        print(f"Error saving study session: {e}")
        return None

def get_study_sessions(user_id, limit=20):
    from modules.supabase_client import get_supabase_admin_client
    client = get_supabase_admin_client()
    if not client:
        return []
    try:
        resp = client.table("study_sessions") \
            .select("*, subjects(name)") \
            .eq("owner_id", user_id) \
            .order("completed_at", desc=True) \
            .limit(limit) \
            .execute()
        
        results = []
        for r in (resp.data or []):
            subject_info = r.get("subjects")
            r["subject_name"] = subject_info.get("name") if subject_info else "No Subject"
            results.append(r)
        return results
    except Exception as e:
        print(f"Error fetching study sessions: {e}")
        return []
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


def _render_live_timer(mode, remaining, running):
    """Render a live countdown in the browser without rerunning Streamlit every second."""
    end_at_ms = int((time.time() + remaining) * 1000) if running else 0
    running_js = "true" if running else "false"
    components.html(
        f"""
        <div class="timer-card">
            <div class="timer-pill">{mode}</div>
            <div id="studymate-timer" class="timer-time">{_format_time(remaining)}</div>
            <div id="studymate-timer-note" class="timer-note">
                {"Counting down live. Keep this tab open while studying." if running else "Press Start to begin a live countdown."}
            </div>
        </div>
        <style>
            .timer-card {{
                text-align: center;
                border-radius: 24px;
                padding: 1.35rem 1rem;
                background:
                    radial-gradient(circle at 92% 12%, rgba(20, 184, 180, 0.12), transparent 24%),
                    linear-gradient(135deg, #ffffff, #f5fbff);
                border: 1px solid rgba(220, 231, 247, 0.95);
                box-shadow: 0 12px 34px rgba(57, 76, 119, 0.10);
                font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }}
            .timer-pill {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 0.34rem 0.78rem;
                border-radius: 999px;
                background: linear-gradient(135deg, #d9fbf4, #e9f3ff);
                color: #087c78;
                font-size: 0.8rem;
                font-weight: 850;
            }}
            .timer-time {{
                margin: 0.45rem 0 0.15rem;
                color: #111936;
                font-size: clamp(3rem, 14vw, 5rem);
                line-height: 1;
                font-weight: 900;
                letter-spacing: 0;
            }}
            .timer-note {{
                color: #5f6f91;
                font-size: 0.95rem;
                font-weight: 650;
            }}
            .timer-complete {{
                color: #0f766e;
            }}
        </style>
        <script>
            const timerEl = document.getElementById("studymate-timer");
            const noteEl = document.getElementById("studymate-timer-note");
            const running = {running_js};
            const endAt = {end_at_ms};
            let initialRemaining = {int(remaining)};

            function formatTime(totalSeconds) {{
                const safeSeconds = Math.max(0, Math.floor(totalSeconds));
                const minutes = String(Math.floor(safeSeconds / 60)).padStart(2, "0");
                const seconds = String(safeSeconds % 60).padStart(2, "0");
                return `${{minutes}}:${{seconds}}`;
            }}

            function updateTimer() {{
                let remaining = initialRemaining;
                if (running) {{
                    remaining = Math.max(0, Math.ceil((endAt - Date.now()) / 1000));
                }}
                timerEl.textContent = formatTime(remaining);
                if (running && remaining <= 0) {{
                    timerEl.classList.add("timer-complete");
                    noteEl.textContent = "Session complete. Click Save Session to record it.";
                    if (intervalId) {{
                        clearInterval(intervalId);
                    }}
                }}
            }}

            let intervalId = null;
            updateTimer();
            if (running) {{
                intervalId = setInterval(updateTimer, 1000);
            }}
        </script>
        """,
        height=230,
    )


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
    _render_live_timer(
        st.session_state[_timer_key("mode")],
        remaining,
        st.session_state.get(_timer_key("running"), False),
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
