import html
import logging
import os
import time

logger = logging.getLogger("studymate.auth")

import streamlit as st
from passlib.hash import pbkdf2_sha256

from modules.database import (
    get_app_setting,
    init_db,
    get_or_create_oauth_user,
)
from modules.user_repository import (
    create_remember_session,
    create_user,
    delete_remember_session,
    ensure_admin_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_remember_token,
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
    "user_role",
    "gemini_api_key",
    "ai_provider",
    "gemini_model",
    "ollama_model",
    "ai_request_times",
    "profile_image_url",
    "user_username",
    "user_bio",
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


def _set_code_verifier_cookie(verifier: str):
    """Save the PKCE code verifier in a browser cookie for OAuth callback."""
    if not verifier:
        return
    controller = _get_cookie_controller()
    if controller:
        try:
            controller.set("sb_code_verifier", verifier, max_age=600) # Valid for 10 minutes
        except Exception:
            pass


def _read_code_verifier_cookie() -> str:
    """Retrieve the PKCE code verifier from browser cookies."""
    controller = _get_cookie_controller()
    if controller:
        try:
            return controller.get("sb_code_verifier") or ""
        except Exception:
            return ""
    try:
        return st.context.cookies.get("sb_code_verifier", "")
    except Exception:
        return ""


def _clear_code_verifier_cookie():
    """Clear the PKCE code verifier cookie."""
    controller = _get_cookie_controller()
    if controller:
        try:
            controller.remove("sb_code_verifier")
        except Exception:
            pass


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
    user["auth_provider"] = "google" if user.get("password_hash") == "OAUTH_GOOGLE" else "email"
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
        "role": st.session_state.get("user_role", "student"),
        "auth_provider": st.session_state.get("auth_provider", "email"),
    }


def is_admin():
    """Return True when the current signed-in user is an admin."""
    return is_authenticated() and st.session_state.get("user_role") == "admin"


def require_admin():
    """Block a page unless the current user is an admin."""
    require_login()
    if not is_admin():
        apply_theme()
        st.error("Access denied.")
        st.stop()
    return st.session_state.get("user_id")


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
    st.session_state.auth_provider = user.get("auth_provider", "email")
    st.session_state.user_id = user["id"]
    st.session_state.user_name = user["name"]
    st.session_state.user_email = user["email"]
    st.session_state.user_role = user["role"] if "role" in user.keys() else "student"
    st.session_state.failed_login_attempts = []
    
    # Cache user profile settings
    from modules.profile_repository import ProfileRepository
    profile = ProfileRepository.get_profile(user["id"])
    if profile:
        st.session_state.user_username = profile.get("username")
        st.session_state.profile_image_url = profile.get("profile_image_url")
        st.session_state.user_bio = profile.get("bio")
    else:
        st.session_state.user_username = None
        st.session_state.profile_image_url = None
        st.session_state.user_bio = None

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
    _clear_remember_cookie()
    _clear_user_session_state()
    st.session_state.auth_message = "You have been logged out safely."
    
    try:
        from modules.supabase_client import get_supabase_client
        client = get_supabase_client()
        if client:
            client.auth.sign_out()
    except Exception:
        pass
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


def get_redirect_url() -> str:
    """Determine the OAuth callback redirect URL with priority and log environment info."""
    import os
    
    # Priority 1: st.secrets["APP_URL"]
    url = None
    source = "default"
    try:
        url = (
            st.secrets.get("APP_URL") 
            or st.secrets.get("SUPABASE_AUTH_REDIRECT_URL") 
            or st.secrets.get("OAUTH_REDIRECT_URL")
        )
        if url:
            source = "streamlit_secrets"
    except Exception:
        pass

    # Priority 2: Environment variables
    if not url:
        url = (
            os.getenv("APP_URL") 
            or os.getenv("SUPABASE_AUTH_REDIRECT_URL") 
            or os.getenv("OAUTH_REDIRECT_URL")
        )
        if url:
            source = "env_variables"

    # Priority 3: Auto-detect from request headers (works on Streamlit Cloud)
    if not url:
        try:
            headers = {k.lower(): v for k, v in st.context.headers.items()}
            host = headers.get("x-forwarded-host") or headers.get("host")
            if host and "localhost" not in host and "127.0.0.1" not in host:
                url = f"https://{host}/"
                source = "auto_detect_headers"
        except Exception as e:
            logger.error(f"[AUTH] Failed auto-detecting host from headers: {e}")

    # Priority 4: Fallback to localhost (local development only)
    if not url:
        url = "http://localhost:8501/"
        source = "fallback_localhost"

    if not url.endswith("/"):
        url += "/"

    logger.info(
        f"[AUTH] OAuth Redirect URL: {url} | "
        f"Source: {source} | "
        f"Provider: google"
    )
    return url


def sync_supabase_google_user(user) -> Optional[Dict[str, Any]]:
    """
    Synchronize Google OAuth authenticated user profile with public.users.
    Links existing profiles by email to prevent duplicate accounts and preserve all user data.
    """
    from datetime import datetime
    from modules.supabase_client import get_supabase_admin_client
    
    email = (user.email or "").strip().lower()
    if not email:
        return None

    # Check if user already exists by email in public.users
    local_user = get_user_by_email(email)
    
    display_name = (
        user.user_metadata.get("full_name")
        or user.user_metadata.get("name")
        or email.split("@")[0]
    )
    avatar_url = (
        user.user_metadata.get("avatar_url")
        or user.user_metadata.get("picture")
    )
    
    admin_client = get_supabase_admin_client()
    if not admin_client:
        return local_user

    try:
        if not local_user:
            # Create a new user record in public.users using the Supabase Auth UUID
            user_data = {
                "id": user.id,
                "full_name": display_name[:80],
                "email": email,
                "password_hash": "OAUTH_GOOGLE",
                "profile_picture": avatar_url,
                "profile_image_url": avatar_url,
                "is_admin": False,
                "is_active": True,
                "email_verified": True
            }
            admin_client.table("users").insert(user_data).execute()

            # Create default preferences
            pref_data = {
                "id": user.id,
                "theme": "light",
                "language": "en",
                "sidebar_state": "expanded",
                "default_ai_provider": "Gemini",
                "default_model": "gemini-2.0-flash",
                "teach_me_level": "Normal",
                "voice_enabled": False,
                "notifications": True,
                "timezone": "UTC"
            }
            admin_client.table("user_preferences").insert(pref_data).execute()
            
            # Log audit trail event
            from modules.user_repository import log_audit_event
            log_audit_event(user.id, "ACCOUNT_CREATED", "users", user.id)
            
            # Fetch the newly created profile
            local_user = get_user_by_email(email)
        else:
            # User already exists by email - map them to the session!
            # To preserve all customizations and prevent duplicate account creation,
            # we keep their existing ID (UUID_OLD) and only update the avatar picture and updated_at.
            updates = {
                "profile_picture": avatar_url,
                "profile_image_url": avatar_url,
                "updated_at": datetime.utcnow().isoformat()
            }
            admin_client.table("users").update(updates).eq("id", local_user["id"]).execute()
            from modules.user_repository import log_audit_event
            log_audit_event(local_user["id"], "LOGIN_SUCCESS", "auth", local_user["id"])
            
        # Ensure correct auth_provider is set in returning dictionary
        if local_user:
            local_user["auth_provider"] = "google"

        return local_user
    except Exception as e:
        logger.error(f"Error synchronizing Google user: {e}")
        return local_user


def _google_login_button(key="google_login_btn"):
    """Render the Google login button using a direct Supabase authorize URL (no PKCE)."""
    from modules.supabase_client import load_supabase_credentials
    import urllib.parse

    supabase_url, _, _ = load_supabase_credentials()
    if not supabase_url:
        return

    try:
        redirect_url = get_redirect_url()
        # Construct the authorize URL manually — NO code_challenge means no PKCE verifier needed
        params = urllib.parse.urlencode({
            "provider": "google",
            "redirect_to": redirect_url,
            "scopes": "email profile",
        })
        authorize_url = f"{supabase_url}/auth/v1/authorize?{params}"
        st.link_button("🔐 Continue with Google", authorize_url, use_container_width=True, type="primary")
        # Temporary debug: show the URL so we can verify it
        st.caption(f"Debug: redirect → `{redirect_url}` | [Test authorize URL]({authorize_url})")
    except Exception as e:
        logger.error(f"[AUTH] Failed to render Google login button: {e}")
        st.info("Google login is temporarily unavailable.")




def _login_form():
    """Render and process manual email/password login."""
    # Debug panel if DEBUG environment variable or st.secrets or query parameter is set to true
    debug_mode = (
        str(os.getenv("DEBUG", "false")).lower() == "true"
        or str(st.query_params.get("debug", "false")).lower() == "true"
    )
    if debug_mode:
        from modules.supabase_client import get_supabase_client
        client = get_supabase_client()
        connected = "True" if client else "False"
        
        provider = st.session_state.get("auth_provider", "Not logged in")
        uuid_val = st.session_state.get("user_id", "Not logged in")
        email_val = st.session_state.get("user_email", "Not logged in")
        
        st.write("### 🛠️ Auth Debug Panel")
        st.write(f"**Supabase Auth Connected:** {connected}")
        st.write(f"**Current Provider:** {provider}")
        st.write(f"**Current User UUID:** {uuid_val}")
        st.write(f"**Email:** {email_val}")
        st.write(f"**OAuth Redirect URL:** `{get_redirect_url()}`")
        st.divider()

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(
            "Log In",
            type="primary",
            use_container_width=True,
        )

    if submitted:
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

        user = verify_user_login(clean_email, password, verify_password, hash_password)
        if not user:
            _record_failed_login()
            st.error("Invalid email or password.")
            return

        login_user(user, message=f"Welcome back, {user['name']}!")
        st.rerun()

    st.markdown('<div style="text-align: center; margin: 16px 0; color: var(--color-text-secondary); font-size: 0.8rem; font-weight: 500;">─ OR ─</div>', unsafe_allow_html=True)
    _google_login_button(key="google_login_from_login_tab")


def _signup_form():
    """Render and process manual email/password signup."""
    if str(get_app_setting("enable_public_signup", "true")).lower() != "true":
        st.info("Public signup is currently disabled.")
        return

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

    st.markdown('<div style="text-align: center; margin: 16px 0; color: var(--color-text-secondary); font-size: 0.8rem; font-weight: 500;">─ OR ─</div>', unsafe_allow_html=True)
    _google_login_button(key="google_login_from_signup_tab")


def render_auth_screen():
    """Render login/signup when no user is logged in."""
    apply_theme()
    try:
        from modules.database import get_branding_settings

        branding = get_branding_settings()
    except Exception:
        branding = {
            "app_name": "StudyMate AI",
            "app_subtitle": "AI Study Assistant",
            "product_tagline": "Learn smarter. Revise faster. Prepare better.",
        }

    from modules.icons import icon as _icon
    cap_svg = _icon("graduation-cap", size=20, color="#FFFFFF")
    st.markdown(
        f"""
        <div class="sm-auth-shell">
            <div class="sm-auth-card">
                <div class="sm-auth-logo">
                    <div class="sm-auth-logo-icon">{cap_svg}</div>
                    <div>
                        <div style="font-size:1.125rem; font-weight:700; color:#111827; line-height:1.2;">
                            {html.escape(branding["app_name"])}
                        </div>
                        <div style="font-size:0.75rem; color:#6B7280;">{html.escape(branding.get("app_subtitle","AI Study Assistant"))}</div>
                    </div>
                </div>
                <div class="sm-auth-title">Welcome back</div>
                <div class="sm-auth-subtitle">{html.escape(branding["product_tagline"])}</div>
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
    ensure_admin_user(hash_password)

    # Handle Supabase OAuth callback code (non-PKCE direct exchange)
    if "code" in st.query_params:
        code = st.query_params["code"]
        # Clear query parameters immediately to prevent infinite reload loops
        st.query_params.clear()
        
        from modules.supabase_client import load_supabase_credentials
        supabase_url, anon_key, _ = load_supabase_credentials()
        if supabase_url and anon_key:
            try:
                import httpx
                logger.info("[AUTH] Detected OAuth callback code. Exchanging via direct HTTP POST (no PKCE)...")
                token_url = f"{supabase_url}/auth/v1/token"
                resp = httpx.post(
                    token_url,
                    params={"grant_type": "pkce"},
                    json={"auth_code": code, "code_verifier": ""},
                    headers={
                        "apikey": anon_key,
                        "Content-Type": "application/json",
                    },
                    timeout=15,
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    # Build a minimal user object from the token response
                    user_data = data.get("user", {})
                    user_email = (user_data.get("email") or "").strip().lower()
                    user_id = user_data.get("id")
                    user_metadata = user_data.get("user_metadata", {})
                    
                    if user_email and user_id:
                        logger.info(f"[AUTH] Token exchange succeeded. Email: {user_email} | Supabase UID: {user_id}")
                        
                        # Build a simple namespace object for sync_supabase_google_user
                        class _OAuthUser:
                            pass
                        oauth_user = _OAuthUser()
                        oauth_user.id = user_id
                        oauth_user.email = user_email
                        oauth_user.user_metadata = user_metadata
                        
                        local_user = sync_supabase_google_user(oauth_user)
                        if local_user:
                            login_user(local_user, message="Welcome back!", remember=True)
                            logger.info(f"[AUTH] Profile synced for {local_user['email']} (ID: {local_user['id']}). Redirecting to dashboard.")
                            st.rerun()
                    else:
                        logger.error(f"[AUTH] Token response missing user email or id: {data}")
                        st.error("Authentication succeeded but user profile was incomplete.")
                else:
                    error_msg = resp.json().get("msg", resp.text)
                    logger.error(f"[AUTH] Token exchange failed ({resp.status_code}): {error_msg}")
                    st.error(f"Authentication failed: {error_msg}")
            except Exception as e:
                logger.error(f"[AUTH] Exception during token exchange: {e}")
                st.error(f"Authentication failed: {e}")

    _restore_login_from_cookie()

    if is_authenticated():
        if st.session_state.get("auth_message"):
            st.success(st.session_state.pop("auth_message"))
        return get_current_user_id()

    render_auth_screen()
    st.stop()
