import time

import streamlit as st
from passlib.hash import pbkdf2_sha256

from modules.database import create_user, get_user_by_email, init_db
from modules.security import validate_email, validate_full_name, validate_password
from modules.ui import apply_theme


FAILED_LOGIN_LIMIT = 5
FAILED_LOGIN_WAIT_SECONDS = 60


USER_SESSION_KEYS = {
    "user_id",
    "user_name",
    "user_email",
    "gemini_api_key",
    "groq_api_key",
    "ai_provider",
    "gemini_model",
    "groq_model",
    "ollama_model",
    "ai_request_times",
}

STUDY_SESSION_PREFIXES = (
    "study_chat_",
    "chat_prefill_",
    "quiz_prefill_",
    "flashcard_prefill_",
    "library_",
)

STUDY_SESSION_KEYS = {
    "subject_pending_delete",
    "dashboard_success",
    "quiz_data",
    "quiz_feedback",
    "flashcard_review_index",
    "show_flashcard_answer",
    "latest_revision_plan",
}


def hash_password(password):
    """Hash a password with passlib before storing it."""
    return pbkdf2_sha256.hash(password)


def verify_password(password, password_hash):
    """Verify a password without exposing whether an email exists."""
    try:
        return pbkdf2_sha256.verify(password, password_hash)
    except Exception:
        return False


def is_logged_in():
    """Return True when a user profile is present in session state."""
    return bool(st.session_state.get("user_id"))


def current_user_id():
    """Return the current user id from Streamlit session state."""
    return st.session_state.get("user_id")


def _clear_study_session_state():
    """Remove user-specific page state during logout."""
    keys_to_remove = []
    for key in st.session_state.keys():
        if key in USER_SESSION_KEYS or key in STUDY_SESSION_KEYS:
            keys_to_remove.append(key)
            continue
        if key.startswith(STUDY_SESSION_PREFIXES):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        st.session_state.pop(key, None)


def logout():
    """Log out and remove user-related session values."""
    _clear_study_session_state()
    st.session_state.auth_message = "You have been logged out safely."
    st.rerun()


def _record_failed_login():
    """Track failed logins in this browser session."""
    attempts = st.session_state.get("failed_login_attempts", [])
    now = time.time()
    attempts = [
        attempt_time
        for attempt_time in attempts
        if now - attempt_time < FAILED_LOGIN_WAIT_SECONDS
    ]
    attempts.append(now)
    st.session_state.failed_login_attempts = attempts


def _login_is_rate_limited():
    """Return True when too many failed login attempts happened recently."""
    attempts = st.session_state.get("failed_login_attempts", [])
    now = time.time()
    attempts = [
        attempt_time
        for attempt_time in attempts
        if now - attempt_time < FAILED_LOGIN_WAIT_SECONDS
    ]
    st.session_state.failed_login_attempts = attempts
    return len(attempts) >= FAILED_LOGIN_LIMIT


def _set_logged_in_user(user):
    """Save only safe profile fields in session state."""
    st.session_state.user_id = user["id"]
    st.session_state.user_name = user["name"]
    st.session_state.user_email = user["email"]
    st.session_state.failed_login_attempts = []


def _login_form():
    """Render the login form."""
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)

    if submitted:
        if _login_is_rate_limited():
            st.warning("Too many failed attempts. Please wait a moment and try again.")
            return

        clean_email, email_error = validate_email(email)
        if email_error:
            _record_failed_login()
            st.error("Invalid email or password.")
            return

        user = get_user_by_email(clean_email)
        if not user or not verify_password(password, user["password_hash"]):
            _record_failed_login()
            st.error("Invalid email or password.")
            return

        _set_logged_in_user(user)
        st.success("Logged in successfully.")
        st.rerun()


def _signup_form():
    """Render the signup form."""
    with st.form("signup_form"):
        full_name = st.text_input("Full name", placeholder="Ali Shair")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)

    if submitted:
        clean_name, name_error = validate_full_name(full_name)
        clean_email, email_error = validate_email(email)
        password_error = validate_password(password)

        if name_error:
            st.warning(name_error)
            return
        if email_error:
            st.warning(email_error)
            return
        if password_error:
            st.warning(password_error)
            return
        if password != confirm_password:
            st.warning("Passwords do not match.")
            return

        user_id = create_user(
            name=clean_name,
            email=clean_email,
            password_hash=hash_password(password),
        )
        if not user_id:
            st.error("Could not create this account. Please check your details or try again.")
            return

        user = get_user_by_email(clean_email)
        _set_logged_in_user(user)
        st.success("Account created successfully.")
        st.rerun()


def render_auth_screen():
    """Render login/signup when no user is logged in."""
    apply_theme()
    st.markdown(
        """
        <div class="auth-shell">
            <div class="auth-card">
                <div class="hero-kicker">SECURE STUDY WORKSPACE</div>
                <h1>StudyMate AI</h1>
                <p>Log in to keep your notes, quizzes, flashcards, and plans separate from other users.</p>
                <div class="auth-note">Your notes are kept separate from other users.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("auth_message"):
        st.info(st.session_state.pop("auth_message"))

    login_tab, signup_tab = st.tabs(["Log In", "Sign Up"])
    with login_tab:
        _login_form()
    with signup_tab:
        _signup_form()


def require_login():
    """Block a page until the visitor logs in."""
    init_db()
    if is_logged_in():
        return current_user_id()

    render_auth_screen()
    st.stop()
