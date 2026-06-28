"""
StudyMate AI – Sidebar Navigation Component
"""
import html as _html
import streamlit as st
from modules.icons import icon


NAV_ITEMS = [
    ("Dashboard",        "pages/1_Dashboard.py",         "home"),
    ("Study Library",    "pages/7_Study_Library.py",     "library"),
    ("Upload Notes",     "pages/2_Upload_Notes.py",      "upload-cloud"),
    ("Chat With Notes",  "pages/3_Chat_With_Notes.py",   "message-circle"),
    ("Study Groups",     "pages/14_Study_Groups.py",     "users"),
    ("Quiz Mode",        "pages/4_Quiz_Mode.py",         "help-circle"),
    ("Flashcards",       "pages/5_Flashcards.py",        "layers"),
    ("Revision Planner", "pages/6_Revision_Planner.py",  "calendar"),
    ("Pomodoro Timer",   "pages/9_Pomodoro_Timer.py",    "timer"),
    ("AI Settings",      "pages/8_AI_Settings.py",       "settings"),
    ("About",            "pages/10_About.py",            "info"),
]

ADMIN_NAV_ITEMS = [
    ("Admin Dashboard",  "pages/11_Admin_Dashboard.py",          "shield"),
    ("Branding",         "pages/12_Admin_Branding_Settings.py",  "star"),
    ("Users",            "pages/13_Admin_User_Management.py",    "users"),
]


def _page_url_from_path(page_path: str) -> str:
    """Build Streamlit's page URL from a pages/*.py path."""
    page_name = page_path.rsplit("/", 1)[-1].removesuffix(".py")
    parts = page_name.split("_", 1)
    if parts[0].isdigit() and len(parts) == 2:
        page_name = parts[1]
    return f"/{page_name}"


def sidebar_nav():
    """Render the professional fixed sidebar navigation."""
    from modules.database import get_branding_settings

    branding = get_branding_settings()
    user_name  = st.session_state.get("user_name", "Student")
    user_email = st.session_state.get("user_email", "")
    user_role  = st.session_state.get("user_role", "student")
    initials   = "".join(p[0] for p in user_name.split()[:2]).upper() or "ST"

    app_name = _html.escape(branding.get("app_name", "StudyMate AI"))
    subtitle = _html.escape(branding.get("app_subtitle", "AI Study Assistant"))

    # ── Brand Logo ────────────────────────────────────────────────────────────
    cap_icon = icon("graduation-cap", size=18, color="#FFFFFF")
    st.sidebar.markdown(
        f"""
        <div class="sm-brand">
            <div class="sm-brand-logo">{cap_icon}</div>
            <div>
                <div class="sm-brand-name">{app_name}</div>
                <div class="sm-brand-tagline">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Navigation Links ──────────────────────────────────────────────────────
    for label, page, icon_name in NAV_ITEMS:
        nav_icon = icon(icon_name, size=18, color="currentColor")
        try:
            st.sidebar.page_link(page, label=f"   {label}")
        except Exception:
            url = _page_url_from_path(page)
            st.sidebar.markdown(
                f'<a class="sm-nav-link" href="{url}">'
                f'<span class="sm-nav-icon">{nav_icon}</span>'
                f'<span class="sm-nav-label">{_html.escape(label)}</span>'
                f'</a>',
                unsafe_allow_html=True,
            )

    # ── Admin Section ─────────────────────────────────────────────────────────
    if user_role == "admin":
        shield_icon = icon("shield", size=12, color="#6B7280")
        st.sidebar.markdown(
            f'<div class="sm-nav-section">{shield_icon} Admin</div>',
            unsafe_allow_html=True,
        )
        for label, page, icon_name in ADMIN_NAV_ITEMS:
            nav_icon = icon(icon_name, size=18, color="currentColor")
            try:
                st.sidebar.page_link(page, label=f"   {label}")
            except Exception:
                url = _page_url_from_path(page)
                st.sidebar.markdown(
                    f'<a class="sm-nav-link" href="{url}">'
                    f'<span class="sm-nav-icon">{nav_icon}</span>'
                    f'<span class="sm-nav-label">{_html.escape(label)}</span>'
                    f'</a>',
                    unsafe_allow_html=True,
                )

    # ── Divider ───────────────────────────────────────────────────────────────
    st.sidebar.markdown('<hr style="margin:12px 0;">', unsafe_allow_html=True)

    # ── Profile Card ──────────────────────────────────────────────────────────
    role_badge = (
        f'<span class="sm-pill sm-pill-info" style="font-size:0.6875rem;">Admin</span>'
        if user_role == "admin"
        else f'<span class="sm-pill sm-pill-teal" style="font-size:0.6875rem;">Student</span>'
    )
    st.sidebar.markdown(
        f"""
        <div class="sm-profile">
            <div class="sm-profile-avatar">{_html.escape(initials)}</div>
            <div class="sm-profile-info">
                <div class="sm-profile-name">{_html.escape(user_name)}</div>
                <div class="sm-profile-role">{_html.escape(user_email or "Student")}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Logout ────────────────────────────────────────────────────────────────
    if st.session_state.get("user_id"):
        logout_icon = icon("log-out", size=16, color="#6B7280")
        if st.sidebar.button("Sign Out", use_container_width=True, key="sidebar_logout_btn"):
            from modules.auth import logout
            logout()

    # ── Supabase Status ───────────────────────────────────────────────────────
    from modules.debug import render_supabase_status
    render_supabase_status()
