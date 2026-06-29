"""
StudyMate AI – Sidebar Navigation Component
"""
import html as _html
import streamlit as st
from modules.icons import icon

# Grouped professional information architecture for sidebar links
NAVIGATION = {
    "Study": [
        ("Upload Notes",     "pages/2_Upload_Notes.py",      "upload-cloud"),
        ("Study Library",    "pages/7_Study_Library.py",     "library"),
        ("Chat With Notes",  "pages/3_Chat_With_Notes.py",   "message-circle"),
    ],
    "Learning": [
        ("Quiz Mode",        "pages/4_Quiz_Mode.py",         "help-circle"),
        ("Flashcards",       "pages/5_Flashcards.py",        "layers"),
        ("Revision Planner", "pages/6_Revision_Planner.py",  "calendar"),
        ("Pomodoro Timer",   "pages/9_Pomodoro_Timer.py",    "timer"),
    ],
    "Community": [
        ("Study Groups",     "pages/14_Study_Groups.py",     "users"),
    ],
    "Analytics": [
        ("Dashboard Analytics", "pages/1_Dashboard.py",      "bar-chart-2"),
        ("Performance",       "pages/1_Dashboard.py",      "bar-chart-2"),
        ("Weak Topics",       "pages/1_Dashboard.py",      "bar-chart-2"),
        ("Learning Progress", "pages/1_Dashboard.py",      "bar-chart-2"),
        ("Achievements",      "pages/1_Dashboard.py",      "award"),
    ],
    "Account": [
        ("Profile",          "pages/Profile.py",             "user"),
        ("AI Settings",      "pages/8_AI_Settings.py",       "settings"),
        ("About",            "pages/10_About.py",            "info"),
    ]
}

# Flat list of items for backward compatibility with older page imports
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
    ("Profile",          "pages/Profile.py",             "user"),
    ("About",            "pages/10_About.py",            "info"),
]

ADMIN_NAV_ITEMS = [
    ("Admin Dashboard",  "pages/11_Admin_Dashboard.py",          "shield"),
    ("Branding",         "pages/12_Admin_Branding_Settings.py",  "star"),
    ("Users",            "pages/13_Admin_User_Management.py",    "users"),
]

# Map Lucide icon names to standard Google Material Symbols used by st.page_link natively
MATERIAL_ICON_MAP = {
    "home": "home",
    "user": "person",
    "library": "library_books",
    "upload-cloud": "cloud_upload",
    "message-circle": "forum",
    "users": "group",
    "help-circle": "quiz",
    "layers": "layers",
    "calendar": "calendar_today",
    "timer": "alarm",
    "settings": "settings",
    "info": "info",
    "shield": "shield",
    "star": "star",
    "bar-chart-2": "bar_chart",
    "award": "award"
}

PAGE_PARENTS = {
    "pages/2_Upload_Notes.py": "Study",
    "pages/7_Study_Library.py": "Study",
    "pages/3_Chat_With_Notes.py": "Study",
    "pages/4_Quiz_Mode.py": "Learning",
    "pages/5_Flashcards.py": "Learning",
    "pages/6_Revision_Planner.py": "Learning",
    "pages/9_Pomodoro_Timer.py": "Learning",
    "pages/14_Study_Groups.py": "Community",
    "pages/Profile.py": "Account",
    "pages/8_AI_Settings.py": "Account",
    "pages/10_About.py": "Account",
}


def _page_url_from_path(page_path: str) -> str:
    """Build Streamlit's page URL from a pages/*.py path."""
    page_name = page_path.rsplit("/", 1)[-1].removesuffix(".py")
    parts = page_name.split("_", 1)
    if parts[0].isdigit() and len(parts) == 2:
        page_name = parts[1]
    return f"/{page_name}"


def sidebar_nav():
    """Render the professional grouped and collapsible sidebar navigation."""
    from modules.database import get_branding_settings

    branding = get_branding_settings()
    user_name  = st.session_state.get("user_name", "Student")
    user_email = st.session_state.get("user_email", "")
    user_role  = st.session_state.get("user_role", "student")
    initials   = "".join(p[0] for p in user_name.split()[:2]).upper() or "ST"

    # ── Time Spent Tracking (5 Min Milestone) ─────────────────────────────────
    import time
    user_id = st.session_state.get("user_id")
    if user_id:
        if "session_start_time" not in st.session_state:
            st.session_state["session_start_time"] = time.time()
        
        if not st.session_state.get("session_streak_logged", False):
            elapsed = time.time() - st.session_state["session_start_time"]
            if elapsed >= 300:  # 5 minutes
                st.session_state["session_streak_logged"] = True
                from modules.analytics_repository import AnalyticsRepository
                AnalyticsRepository.log_activity_session(
                    owner_id=user_id,
                    session_type="App Usage",
                    duration_minutes=5,
                    notes="Daily application usage milestone (5 minutes completed)"
                )
                st.toast("🎉 Bazinga! You've stayed on the app for 5 minutes today. Your study streak has been updated!")
            else:
                remaining_ms = int((300 - elapsed) * 1000)
                st.sidebar.markdown(
                    f"""
                    <script>
                    if (window.appUsageTimer) {{
                        clearTimeout(window.appUsageTimer);
                    }}
                    window.appUsageTimer = setTimeout(function() {{
                        window.parent.location.reload();
                    }}, {remaining_ms});
                    </script>
                    """,
                    unsafe_allow_html=True
                )

    app_name = _html.escape(branding.get("app_name", "StudyMate AI"))
    subtitle = _html.escape(branding.get("app_subtitle", "AI Study Assistant"))

    # ── Brand Logo ────────────────────────────────────────────────────────────
    cap_icon = icon("graduation-cap", size=20, color="#FFFFFF")
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

    # ── Inspect Current Page Path ─────────────────────────────────────────────
    import inspect
    caller_filename = ""
    for frame_info in inspect.stack():
        fn = frame_info.filename.replace("\\", "/")
        if "pages/" in fn or fn.endswith(".py"):
            caller_filename = fn
            break

    current_page = ""
    if "pages/" in caller_filename:
        current_page = "pages/" + caller_filename.split("pages/")[-1]
    elif "app.py" in caller_filename:
        current_page = "app.py"

    # Auto-expand the parent section of the currently active page
    active_parent = PAGE_PARENTS.get(current_page)
    if active_parent:
        st.session_state[f"expanded_{active_parent}"] = True

    # ── Navigation Links ──────────────────────────────────────────────────────
    # 1. Dashboard is always visible at the top
    try:
        st.sidebar.page_link("pages/1_Dashboard.py", label=" Dashboard", icon=f":material/{MATERIAL_ICON_MAP.get('home')}:")
    except Exception:
        url = _page_url_from_path("pages/1_Dashboard.py")
        st.sidebar.markdown(
            f'<a class="sm-nav-link" href="{url}">'
            f'<span class="sm-nav-icon">{icon("home", size=18, color="currentColor")}</span>'
            f'<span class="sm-nav-label">Dashboard</span>'
            f'</a>',
            unsafe_allow_html=True,
        )

    # 2. Render collapsible categories using page-nested context (removing st.sidebar prefix in with blocks)
    for category, items in NAVIGATION.items():
        is_expanded = st.session_state.get(f"expanded_{category}", False)
        
        with st.sidebar.expander(category, expanded=is_expanded):
            for label, page, icon_name in items:
                material_icon = f":material/{MATERIAL_ICON_MAP.get(icon_name, 'file_text')}:"
                
                # Check for coming soon badges on Analytics sub-elements
                if category == "Analytics" and label != "Dashboard Analytics":
                    try:
                        st.page_link("pages/1_Dashboard.py", label=f" {label}", icon=material_icon, disabled=True)
                    except Exception:
                        st.markdown(
                            f'<div class="sm-nav-link" style="opacity:0.5; cursor:not-allowed; display:flex; align-items:center; gap:8px; padding:6px 12px;">'
                            f'<span class="sm-nav-icon">{icon(icon_name, size=18, color="#6B7280")}</span>'
                            f'<span class="sm-nav-label">{label}</span>'
                            f'<span style="background:var(--color-border); font-size:0.625rem; padding:1px 4px; border-radius:3px; font-weight:600; color:var(--color-text-secondary); margin-left:auto;">SOON</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                else:
                    try:
                        st.page_link(page, label=f" {label}", icon=material_icon)
                    except Exception:
                        url = _page_url_from_path(page)
                        st.markdown(
                            f'<a class="sm-nav-link" href="{url}">'
                            f'<span class="sm-nav-icon">{icon(icon_name, size=18, color="currentColor")}</span>'
                            f'<span class="sm-nav-label">{_html.escape(label)}</span>'
                            f'</a>',
                            unsafe_allow_html=True,
                        )

            # Logout button rendered inside the Account section
            if category == "Account" and st.session_state.get("user_id"):
                st.markdown('<hr style="margin:8px 0; border:none; border-top:1px solid var(--color-border);">', unsafe_allow_html=True)
                if st.button("Sign Out", use_container_width=True, key="sidebar_logout_btn"):
                    from modules.auth import logout
                    logout()

    # ── Admin Section ─────────────────────────────────────────────────────────
    if user_role == "admin":
        with st.sidebar.expander("Admin Settings", expanded=False):
            for label, page, icon_name in ADMIN_NAV_ITEMS:
                material_icon = f":material/{MATERIAL_ICON_MAP.get(icon_name, 'file_text')}:"
                try:
                    st.page_link(page, label=f" {label}", icon=material_icon)
                except Exception:
                    url = _page_url_from_path(page)
                    st.markdown(
                        f'<a class="sm-nav-link" href="{url}">'
                        f'<span class="sm-nav-icon">{icon(icon_name, size=18, color="currentColor")}</span>'
                        f'<span class="sm-nav-label">{_html.escape(label)}</span>'
                        f'</a>',
                        unsafe_allow_html=True,
                    )

    # ── Divider ───────────────────────────────────────────────────────────────
    st.sidebar.markdown('<hr style="margin:12px 0;">', unsafe_allow_html=True)

    # ── Profile Card ──────────────────────────────────────────────────────────
    avatar_url = st.session_state.get("profile_image_url")
    if avatar_url:
        avatar_html = f'<img src="{_html.escape(avatar_url)}" class="sm-profile-avatar" style="width:34px; height:34px; border-radius:var(--radius-md); object-fit:cover; flex-shrink:0;">'
    else:
        avatar_html = f'<div class="sm-profile-avatar">{_html.escape(initials)}</div>'

    st.sidebar.markdown(
        f"""
        <div class="sm-profile">
            {avatar_html}
            <div class="sm-profile-info">
                <div class="sm-profile-name">{_html.escape(user_name)}</div>
                <div class="sm-profile-role">{_html.escape(user_email or "Student")}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Supabase Status ───────────────────────────────────────────────────────
    from modules.debug import render_supabase_status
    render_supabase_status()

    # ── Custom JS Category Icons (Dynamic Loader) ─────────────────────────────
    import json
    from modules.icons import ICONS
    
    js_mapping = {}
    color_map = {
        "study": "#14B8A6",
        "learning": "#9333EA",
        "community": "#3B82F6",
        "analytics": "#2563EB",
        "account": "#0F9D8C"
    }
    
    for name in ["study", "learning", "community", "analytics", "account"]:
        svg_content = ICONS.get(name, "")
        color = color_map.get(name, "currentColor")
        js_mapping[name] = (
            f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round" style="margin-right:8px; flex-shrink:0;" '
            f'role="img" aria-label="{name.capitalize()}">{svg_content}</svg>'
        )
        
    admin_svg = ICONS.get("admin", "")
    js_mapping["admin settings"] = (
        f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
        f'stroke="#EF4444" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" style="margin-right:8px; flex-shrink:0;" '
        f'role="img" aria-label="Admin Settings">{admin_svg}</svg>'
    )
    
    js_mapping_json = json.dumps(js_mapping)

    import streamlit.components.v1 as components
    components.html(
        f"""
        <script>
        const mapping = {js_mapping_json};
        function applyIcons() {{
            try {{
                const summaries = window.parent.document.querySelectorAll('div[data-testid="stSidebar"] [data-testid="stExpander"] summary');
                summaries.forEach(summary => {{
                    const text = summary.textContent.replace(/[▶▼]/g, "").trim().toLowerCase();
                    if (mapping[text]) {{
                        if (!summary.querySelector('.sm-custom-icon')) {{
                            const div = window.parent.document.createElement('div');
                            div.className = 'sm-custom-icon';
                            div.style.display = 'inline-flex';
                            div.style.alignItems = 'center';
                            div.style.justifyContent = 'center';
                            div.style.flexShrink = '0';
                            div.innerHTML = mapping[text];
                            summary.insertBefore(div, summary.firstChild);
                        }}
                    }}
                }});
            }} catch (e) {{
                console.error("Sidebar custom icon injection error:", e);
            }}
        }}
        applyIcons();
        if (!window.sidebarIconInterval) {{
            window.sidebarIconInterval = setInterval(applyIcons, 500);
        }}
        </script>
        """,
        height=0,
        width=0
    )
