import time

import streamlit as st
from passlib.hash import pbkdf2_sha256

from modules.database import (
    create_remember_session,
    create_user,
    delete_remember_session,
    get_user_by_email,
    get_user_by_id,
    get_user_by_remember_token,
    init_db,
    verify_user_login,
)
from modules.security import validate_email, validate_full_name, validate_password
from modules.ui import apply_theme


FAILED_LOGIN_LIMIT = 5
FAILED_LOGIN_WAIT_SECONDS = 60
GOOGLE_DISABLED_MESSAGE = (
    "Google login is temporarily disabled. Please use email/password login."
)
REMEMBER_COOKIE_NAME = "studymate_remember_token"
REMEMBER_COOKIE_DAYS = 30


USER_SESSION_KEYS = {
    "authenticated",
    "auth_provider",
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
    """Hash a password before it is saved in SQLite."""
    return pbkdf2_sha256.hash(password)


def verify_password(password, password_hash):
    """Verify a password without exposing whether the account exists."""
    try:
        return pbkdf2_sha256.verify(password, password_hash or "")
    except Exception:
        return False


def is_authenticated():
    """Return True when a local email/password user is signed in."""
    return bool(
        st.session_state.get("authenticated")
        and st.session_state.get("user_id")
    )


def _get_cookie_controller():
    """Return the optional cookie controller used for persistent login."""
    try:
        from streamlit_cookies_controller import CookieController

        return CookieController()
    except Exception:
        return None


def _read_remember_cookie():
    """Read the persistent login cookie without crashing if cookies are unavailable."""
    controller = _get_cookie_controller()
    if controller:
        try:
            return controller.get(REMEMBER_COOKIE_NAME) or ""
        except Exception:
            return ""

    try:
        return st.context.cookies.get(REMEMBER_COOKIE_NAME, "")
    except Exception:
        return ""


def _set_remember_cookie(token):
    """Save a persistent login cookie for this browser."""
    if not token:
        return
    controller = _get_cookie_controller()
    if controller:
        try:
            controller.set(
                REMEMBER_COOKIE_NAME,
                token,
                max_age=REMEMBER_COOKIE_DAYS * 24 * 60 * 60,
                secure=False,
                same_site="strict",
            )
        except TypeError:
            controller.set(REMEMBER_COOKIE_NAME, token)
        except Exception:
            return


def _clear_remember_cookie():
    """Remove the persistent login cookie when the user logs out."""
    token = _read_remember_cookie()
    if token:
        delete_remember_session(token)
    controller = _get_cookie_controller()
    if controller:
        try:
            controller.remove(REMEMBER_COOKIE_NAME)
        except Exception:
            pass


def _restore_login_from_cookie():
    """Restore a user session after refresh when a remember cookie is valid."""
    if is_authenticated():
        return True
    token = _read_remember_cookie()
    if not token:
        return False
    user = get_user_by_remember_token(token)
    if not user:
        _clear_remember_cookie()
        return False
    login_user(user, remember=False)
    return True


def is_logged_in():
    """Compatibility helper used by older pages."""
    return is_authenticated()


def get_current_user_id():
    """Return the current signed-in user's id."""
    return st.session_state.get("user_id")


def current_user_id():
    """Compatibility helper used by older pages."""
    return get_current_user_id()


def get_current_user():
    """Return the current signed-in user's safe profile fields."""
    if not is_authenticated():
        return None
    return {
        "id": st.session_state.get("user_id"),
        "name": st.session_state.get("user_name", ""),
        "email": st.session_state.get("user_email", ""),
        "auth_provider": st.session_state.get("auth_provider", "email"),
    }


def get_current_user_display_name():
    """Return the signed-in user's name, with a generic fallback."""
    session_name = str(st.session_state.get("user_name", "")).strip()
    if session_name:
        return session_name

    user = get_user_by_id(st.session_state.get("user_id"))
    if user and str(user["name"]).strip():
        st.session_state.user_name = user["name"]
        return str(user["name"]).strip()

    return "Student"


def _clear_user_session_state():
    """Remove user-specific state during logout."""
    keys_to_remove = []
    for key in list(st.session_state.keys()):
        if key in USER_SESSION_KEYS or key in STUDY_SESSION_KEYS:
            keys_to_remove.append(key)
            continue
        if key.startswith(STUDY_SESSION_PREFIXES):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        st.session_state.pop(key, None)


def login_user(user, message=None, remember=True):
    """Store the authenticated user's safe profile in session state."""
    st.session_state.authenticated = True
    st.session_state.auth_provider = "email"
    st.session_state.user_id = user["id"]
    st.session_state.user_name = user["name"]
    st.session_state.user_email = user["email"]
    st.session_state.failed_login_attempts = []
    if remember:
        token = create_remember_session(user["id"], days=REMEMBER_COOKIE_DAYS)
        _set_remember_cookie(token)
    if message:
        st.session_state.auth_message = message


def logout_user():
    """Clear the local email/password session and return to login."""
    _clear_remember_cookie()
    _clear_user_session_state()
    st.session_state.auth_message = "You have been logged out safely."
    st.rerun()


def logout():
    """Compatibility helper used by the sidebar logout button."""
    logout_user()


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


def _disabled_google_note():
    """Show the current temporary Google login status."""
    st.info(GOOGLE_DISABLED_MESSAGE)


def _login_form():
    """Render and process manual email/password login."""
    _disabled_google_note()
    st.divider()

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(
            "Log In",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    if _login_is_rate_limited():
        st.warning("Too many failed attempts. Please wait a moment and try again.")
        return

    clean_email, email_error = validate_email(email)
    if email_error:
        _record_failed_login()
        st.error("Invalid email or password.")
        return

    if not password:
        _record_failed_login()
        st.error("Invalid email or password.")
        return

    user = verify_user_login(clean_email, password, verify_password)
    if not user:
        _record_failed_login()
        st.error("Invalid email or password.")
        return

    login_user(user, message=f"Welcome back, {user['name']}!")
    st.rerun()


def _signup_form():
    """Render and process manual email/password signup."""
    _disabled_google_note()
    st.divider()

    with st.form("signup_form"):
        full_name = st.text_input("Full name", placeholder="Your full name")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button(
            "Create Account",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

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

    if get_user_by_email(clean_email):
        st.warning("An account with this email already exists. Please log in.")
        return

    password_hash = hash_password(password)
    user_id = create_user(
        name=clean_name,
        email=clean_email,
        password_hash=password_hash,
        auth_provider="email",
    )
    if not user_id:
        st.error("Could not create this account. Please try again.")
        return

    user = get_user_by_email(clean_email)
    if not user:
        st.error("Account created, but login could not start. Please log in.")
        return

    login_user(user, message=f"Account created successfully. Welcome, {clean_name}!")
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
                <div class="auth-note">Manual email/password login is active.</div>
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

    _restore_login_from_cookie()

    if is_authenticated():
        if st.session_state.get("auth_message"):
            st.success(st.session_state.pop("auth_message"))
        return get_current_user_id()

    render_auth_screen()
    st.stop()
