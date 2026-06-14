import html

import streamlit as st


NAV_ITEMS = [
    ("Dashboard", "pages/1_Dashboard.py", "\U0001f3e0"),
    ("Study Library", "pages/7_Study_Library.py", "\U0001f5c3\ufe0f"),
    ("Upload Notes", "pages/2_Upload_Notes.py", "\u2601\ufe0f"),
    ("Chat With Notes", "pages/3_Chat_With_Notes.py", "\U0001f4ac"),
    ("Quiz Mode", "pages/4_Quiz_Mode.py", "\u2754"),
    ("Flashcards", "pages/5_Flashcards.py", "\U0001f4d8"),
    ("Revision Planner", "pages/6_Revision_Planner.py", "\U0001f5d3\ufe0f"),
    ("AI Settings", "pages/8_AI_Settings.py", "\u2699\ufe0f"),
]


def _page_url_from_path(page_path):
    """Build Streamlit's friendly page URL from a pages/*.py path."""
    page_name = page_path.rsplit("/", 1)[-1].removesuffix(".py")
    parts = page_name.split("_", 1)
    if parts[0].isdigit() and len(parts) == 2:
        page_name = parts[1]
    return f"/{page_name}"


def apply_theme():
    """Apply the shared Candy Pop Scholar / Aqua Peach Glass theme."""
    st.markdown(
        """
        <style>
            :root {
                --sm-bg: #fbfcff;
                --sm-bg-2: #f3f8ff;
                --sm-card: rgba(255, 255, 255, 0.92);
                --sm-ink: #111936;
                --sm-charcoal: #1f2a44;
                --sm-muted: #5f6f91;
                --sm-placeholder: #8a9ab8;
                --sm-line: #dfe9f7;
                --sm-teal: #14b8b4;
                --sm-mint: #8ef1d2;
                --sm-sky: #60a5fa;
                --sm-blue: #2f7df6;
                --sm-lavender: #a78bfa;
                --sm-pink: #fb7bbf;
                --sm-coral: #ff637d;
                --sm-mango: #ffb703;
                --sm-lime: #8bd94f;
                --sm-success-bg: #e7fbf5;
                --sm-info-bg: #eaf4ff;
                --sm-warning-bg: #fff5d6;
                --sm-error-bg: #ffe8ee;
                --sm-shadow: 0 20px 55px rgba(57, 76, 119, 0.13);
                --sm-soft-shadow: 0 12px 34px rgba(57, 76, 119, 0.10);
                --sm-radius: 22px;
            }

            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;650;750;850&display=swap');

            html, body, [class*="css"] {
                font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }

            .stApp {
                background:
                    radial-gradient(circle at 8% 12%, rgba(20, 184, 180, 0.14), transparent 24%),
                    radial-gradient(circle at 92% 10%, rgba(251, 123, 191, 0.13), transparent 22%),
                    radial-gradient(circle at 78% 86%, rgba(255, 183, 3, 0.13), transparent 25%),
                    linear-gradient(135deg, #ffffff 0%, var(--sm-bg-2) 48%, #fff9fb 100%);
                color: var(--sm-ink);
            }

            header[data-testid="stHeader"] {
                background:
                    linear-gradient(90deg, rgba(255, 255, 255, 0.86), rgba(245, 252, 255, 0.82), rgba(255, 247, 251, 0.84)) !important;
                border-bottom: 1px solid rgba(216, 228, 243, 0.72);
                box-shadow: 0 8px 28px rgba(57, 76, 119, 0.08);
                backdrop-filter: blur(18px);
                -webkit-backdrop-filter: blur(18px);
            }

            header[data-testid="stHeader"] * {
                color: #17213a !important;
            }

            [data-testid="stToolbar"] {
                right: 0.85rem;
            }

            [data-testid="stAppViewContainer"] > .main {
                background: transparent;
            }

            .block-container {
                max-width: 1200px;
                padding-top: 3rem;
                padding-bottom: 3.5rem;
            }

            p, li, label, span, div {
                color: inherit;
            }

            h1, h2, h3, h4, h5, h6,
            [data-testid="stMarkdownContainer"] h1,
            [data-testid="stMarkdownContainer"] h2,
            [data-testid="stMarkdownContainer"] h3 {
                color: var(--sm-ink);
                letter-spacing: 0;
            }

            [data-testid="stSidebar"] {
                background:
                    linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(247, 251, 255, 0.95)),
                    radial-gradient(circle at 20% 10%, rgba(20, 184, 180, 0.12), transparent 26%);
                border-right: 1px solid rgba(214, 225, 241, 0.9);
                box-shadow: 16px 0 45px rgba(57, 76, 119, 0.08);
            }

            [data-testid="stSidebarNav"] {
                display: none;
            }

            [data-testid="stSidebar"] > div:first-child {
                padding: 1.25rem 1rem;
            }

            [data-testid="stSidebar"] * {
                color: var(--sm-ink);
            }

            [data-testid="stSidebar"] [data-testid="stPageLink"] {
                margin: 0.35rem 0;
            }

            [data-testid="stSidebar"] [data-testid="stPageLink"] a,
            [data-testid="stSidebar"] .fallback-nav-link {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                min-height: 3rem;
                border-radius: 18px;
                padding: 0.7rem 0.85rem;
                color: #485775 !important;
                font-weight: 820;
                transition: all 170ms ease;
                border: 1px solid transparent;
                text-decoration: none !important;
            }

            [data-testid="stSidebar"] a {
                min-height: 3rem;
                border-radius: 16px;
                padding: 0.7rem 0.85rem;
                margin: 0.35rem 0;
                color: #485775;
                font-weight: 780;
                transition: all 170ms ease;
                border: 1px solid transparent;
                text-decoration: none;
            }

            [data-testid="stSidebar"] a p,
            [data-testid="stSidebar"] a span {
                color: inherit;
                font-weight: inherit;
            }

            [data-testid="stSidebar"] a:hover {
                background: rgba(20, 184, 180, 0.10);
                border-color: rgba(20, 184, 180, 0.18);
                color: #0d8f8b;
                transform: translateX(3px);
            }

            [data-testid="stSidebar"] a[aria-current="page"],
            [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
                background: linear-gradient(135deg, rgba(213, 251, 244, 0.95), rgba(232, 244, 255, 0.98));
                color: #087c78 !important;
                border-color: rgba(20, 184, 180, 0.32);
                box-shadow: 0 10px 22px rgba(20, 184, 180, 0.14);
            }

            .study-brand {
                display: flex;
                gap: 0.78rem;
                align-items: center;
                padding: 0.85rem 0.55rem 1.2rem;
                margin-bottom: 0.75rem;
            }

            .study-logo {
                width: 48px;
                height: 48px;
                border-radius: 16px;
                display: grid;
                place-items: center;
                font-size: 1.7rem;
                background: linear-gradient(135deg, #9ff6e4, #72b7ff 55%, #f7a8dc);
                box-shadow: 0 12px 24px rgba(20, 184, 180, 0.22);
            }

            .study-brand-title {
                font-size: 1.06rem;
                line-height: 1.12;
                font-weight: 850;
                letter-spacing: 0;
                color: var(--sm-ink);
            }

            .study-brand-title span {
                color: var(--sm-blue);
            }

            .study-brand-subtitle {
                color: var(--sm-muted);
                font-size: 0.78rem;
                margin-top: 0.25rem;
                font-weight: 650;
            }

            .sidebar-helper {
                margin: 1.5rem 0.35rem 1rem;
                padding: 1rem;
                border-radius: 20px;
                text-align: center;
                background: linear-gradient(155deg, rgba(238, 232, 255, 0.94), rgba(218, 249, 246, 0.9));
                border: 1px solid rgba(224, 231, 255, 0.95);
                box-shadow: var(--sm-soft-shadow);
            }

            .sidebar-helper-icon {
                font-size: 2rem;
                margin-bottom: 0.35rem;
            }

            .sidebar-helper strong {
                display: block;
                color: #0b8f8a;
                margin-bottom: 0.25rem;
            }

            .sidebar-helper p {
                color: var(--sm-muted);
                font-size: 0.82rem;
                margin: 0;
            }

            .profile-card {
                margin: 0.95rem 0.35rem 0.75rem;
                padding: 0.95rem;
                border-radius: 20px;
                background:
                    radial-gradient(circle at 88% 12%, rgba(255, 183, 3, 0.20), transparent 28%),
                    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(235, 255, 250, 0.94));
                border: 1px solid rgba(216, 228, 243, 0.95);
                box-shadow: var(--sm-soft-shadow);
            }

            .profile-top {
                display: flex;
                gap: 0.75rem;
                align-items: center;
                margin-bottom: 0.65rem;
            }

            .profile-avatar {
                width: 44px;
                height: 44px;
                border-radius: 16px;
                display: grid;
                place-items: center;
                color: #ffffff;
                font-weight: 900;
                background: linear-gradient(135deg, var(--sm-coral), var(--sm-lavender));
                box-shadow: 0 12px 22px rgba(167, 139, 250, 0.22);
            }

            .profile-name {
                font-weight: 850;
                color: var(--sm-ink);
                line-height: 1.05;
            }

            .profile-role {
                color: var(--sm-muted);
                font-size: 0.78rem;
                font-weight: 650;
                margin-top: 0.2rem;
            }

            .profile-mode {
                display: inline-flex;
                align-items: center;
                padding: 0.28rem 0.58rem;
                border-radius: 999px;
                background: linear-gradient(135deg, #d8fff6, #eff0ff);
                color: #087c78;
                font-size: 0.74rem;
                font-weight: 850;
            }

            .hero {
                position: relative;
                overflow: hidden;
                min-height: 245px;
                padding: clamp(1.45rem, 3vw, 2.6rem);
                margin-bottom: 1.25rem;
                border-radius: 28px;
                color: var(--sm-ink);
                background:
                    radial-gradient(circle at 90% 20%, rgba(255, 255, 255, 0.55), transparent 15%),
                    radial-gradient(circle at 82% 72%, rgba(20, 184, 180, 0.28), transparent 5%),
                    radial-gradient(circle at 12% 18%, rgba(255, 99, 125, 0.22), transparent 4%),
                    linear-gradient(135deg, #bdfcf0 0%, #c6efff 52%, #a9d3ff 100%);
                border: 1px solid rgba(139, 211, 246, 0.75);
                box-shadow: var(--sm-shadow);
            }

            .hero::before {
                content: "\\2726";
                position: absolute;
                left: 5.5%;
                top: 8%;
                color: #d92f57;
                font-size: 2.3rem;
                filter: drop-shadow(0 8px 12px rgba(255, 99, 125, 0.25));
                transform: rotate(-16deg);
            }

            .hero::after {
                content: "\\1F4DA";
                position: absolute;
                right: 6.5%;
                bottom: 10%;
                font-size: clamp(5rem, 12vw, 8.5rem);
                filter: drop-shadow(0 18px 22px rgba(47, 125, 246, 0.18));
                transform: rotate(-4deg);
            }

            .hero-content {
                position: relative;
                z-index: 2;
                max-width: 660px;
                padding-left: clamp(0.25rem, 3vw, 2rem);
            }

            .hero-kicker {
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                font-size: 0.76rem;
                text-transform: uppercase;
                letter-spacing: 0.14em;
                color: #15213d;
                font-weight: 850;
                margin-bottom: 0.75rem;
            }

            .hero h1 {
                margin: 0;
                font-size: clamp(2.3rem, 6vw, 4.25rem);
                line-height: 0.96;
                color: #101832;
                font-weight: 900;
            }

            .hero p {
                margin: 1rem 0 0;
                max-width: 520px;
                color: #27334f;
                font-size: 1.08rem;
                line-height: 1.58;
                font-weight: 600;
            }

            .section-title {
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                font-size: 1.22rem;
                font-weight: 850;
                color: var(--sm-ink);
                margin: 1.25rem 0 0.7rem;
            }

            .section-title::after {
                content: "";
                width: 42px;
                height: 4px;
                border-radius: 999px;
                background: linear-gradient(90deg, var(--sm-teal), var(--sm-sky));
            }

            .feature-card,
            .soft-card,
            div[data-testid="stForm"],
            div[data-testid="stVerticalBlockBorderWrapper"] {
                border: 1px solid rgba(220, 231, 247, 0.95);
                border-radius: 24px;
                box-shadow: var(--sm-soft-shadow);
                background: rgba(255, 255, 255, 0.92);
                backdrop-filter: blur(18px);
            }

            .feature-card,
            .library-card,
            .soft-card {
                padding: 1.2rem;
                margin-bottom: 0.85rem;
            }

            .library-card {
                border: 1px solid rgba(220, 231, 247, 0.95);
                border-radius: 24px;
                box-shadow: var(--sm-soft-shadow);
                background: rgba(255, 255, 255, 0.94);
                color: var(--sm-ink);
            }

            .library-header {
                padding: 0.25rem 0 1.15rem;
            }

            .library-header h1 {
                margin: 0;
                color: var(--sm-ink);
                font-size: clamp(2rem, 4vw, 3.1rem);
                line-height: 1.05;
                font-weight: 900;
            }

            .library-header p {
                margin: 0.6rem 0 0;
                color: var(--sm-muted);
                font-size: 1.04rem;
                font-weight: 650;
            }

            .filter-card-title {
                color: var(--sm-ink);
                font-weight: 850;
                font-size: 1.02rem;
                margin-bottom: 0.7rem;
            }

            .material-row-info {
                min-width: 0;
            }

            .material-file-line {
                display: flex;
                align-items: center;
                gap: 0.65rem;
                min-width: 0;
                margin-bottom: 0.45rem;
            }

            .material-file-icon {
                width: 2.15rem;
                height: 2.15rem;
                display: inline-grid;
                place-items: center;
                border-radius: 12px;
                background: linear-gradient(135deg, #d8fff6, #eef4ff);
                flex: 0 0 auto;
            }

            .material-file-name {
                display: block;
                min-width: 0;
                max-width: 100%;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                color: var(--sm-ink);
                font-size: 1.02rem;
                font-weight: 850;
            }

            .material-row-meta,
            .material-row-description {
                color: var(--sm-muted);
                font-size: 0.86rem;
                font-weight: 650;
                line-height: 1.45;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .material-row-meta span {
                color: #9aa8c0;
                padding: 0 0.25rem;
            }

            .material-row-description {
                margin-top: 0.2rem;
                color: #53617d;
            }

            .material-card {
                min-height: 214px;
                display: flex;
                flex-direction: column;
                gap: 0.72rem;
                padding: 1.05rem;
                margin-bottom: 0.72rem;
                border: 1px solid rgba(220, 231, 247, 0.95);
                border-radius: 24px;
                box-shadow: var(--sm-soft-shadow);
                background:
                    radial-gradient(circle at 90% 10%, rgba(20, 184, 180, 0.10), transparent 26%),
                    rgba(255, 255, 255, 0.96);
                color: var(--sm-ink);
            }

            .material-title {
                min-height: 2.8rem;
                color: var(--sm-ink);
                font-size: 1.02rem;
                font-weight: 880;
                line-height: 1.35;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
                text-overflow: ellipsis;
                word-break: break-word;
            }

            .material-description {
                min-height: 2.8rem;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
                color: var(--sm-muted);
                margin: 0;
                line-height: 1.42;
            }

            .material-date {
                margin-top: auto;
                color: #53617d;
                font-size: 0.82rem;
                font-weight: 650;
            }

            .library-card h3 {
                margin: 0 0 0.35rem;
                color: var(--sm-ink);
                font-size: 1.05rem;
            }

            .library-card p {
                color: var(--sm-muted);
                margin: 0.2rem 0;
                line-height: 1.45;
            }

            .library-meta {
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
                margin-top: 0.75rem;
            }

            .library-chip {
                display: inline-flex;
                padding: 0.28rem 0.6rem;
                border-radius: 999px;
                background: linear-gradient(135deg, #d8fff6, #eef4ff);
                color: #17486b;
                font-size: 0.76rem;
                font-weight: 820;
            }

            .preview-frame {
                overflow: hidden;
                border-radius: 22px;
                border: 1px solid rgba(216, 228, 243, 0.95);
                background: #ffffff;
                box-shadow: var(--sm-soft-shadow);
            }

            .preview-frame iframe {
                display: block;
                border: none;
                background: #ffffff;
            }

            .text-preview {
                max-height: 620px;
                overflow: auto;
                border-radius: 22px;
                border: 1px solid rgba(216, 228, 243, 0.95);
                background: #ffffff;
                box-shadow: var(--sm-soft-shadow);
                padding: 1rem;
            }

            .text-preview pre {
                margin: 0;
                white-space: pre-wrap;
                word-break: break-word;
                color: #14213d;
                font-size: 0.94rem;
                line-height: 1.6;
                font-family: "Consolas", "Cascadia Mono", monospace;
            }

            .feature-card {
                position: relative;
                overflow: hidden;
                min-height: 132px;
            }

            .feature-card::after {
                content: "";
                position: absolute;
                right: -20px;
                top: -22px;
                width: 86px;
                height: 86px;
                border-radius: 999px;
                background: var(--soft);
                opacity: 0.85;
            }

            .feature-icon {
                width: 48px;
                height: 48px;
                display: grid;
                place-items: center;
                border-radius: 17px;
                font-size: 1.45rem;
                background: var(--soft);
                color: var(--accent);
                margin-bottom: 0.85rem;
            }

            .feature-card h3,
            .soft-card h3 {
                position: relative;
                z-index: 1;
                margin: 0 0 0.35rem;
                color: var(--sm-ink);
                font-size: 1.05rem;
            }

            .feature-card p,
            .soft-card p {
                position: relative;
                z-index: 1;
                color: var(--sm-muted);
                margin: 0;
                line-height: 1.5;
                font-weight: 560;
            }

            .stButton > button,
            .stDownloadButton > button {
                border-radius: 16px;
                border: 1px solid rgba(20, 184, 180, 0.28);
                color: #14213d;
                font-weight: 820;
                min-height: 2.85rem;
                transition: all 160ms ease;
                background: #ffffff;
                box-shadow: 0 8px 18px rgba(57, 76, 119, 0.08);
            }

            .stButton > button *,
            .stDownloadButton > button * {
                white-space: nowrap !important;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .stButton > button p,
            .stDownloadButton > button p {
                color: inherit;
                font-weight: inherit;
            }

            .stButton > button:hover,
            .stDownloadButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 14px 28px rgba(20, 184, 180, 0.18);
                border-color: rgba(20, 184, 180, 0.62);
                color: #0b3b5a;
            }

            .stButton > button[kind="primary"],
            button[kind="primary"],
            button[data-testid="stBaseButton-primary"],
            button[data-testid="stBaseButton-primaryFormSubmit"],
            button[data-testid="stBaseButton-secondaryFormSubmit"] {
                background: linear-gradient(135deg, #0fb8b3, #2f7df6) !important;
                border: none !important;
                color: #ffffff !important;
            }

            .stButton > button[kind="primary"] p,
            button[kind="primary"] p,
            button[data-testid="stBaseButton-primary"] *,
            button[data-testid="stBaseButton-primaryFormSubmit"] *,
            button[data-testid="stBaseButton-secondaryFormSubmit"] * {
                color: #ffffff !important;
            }

            .stTextInput,
            .stTextArea,
            .stNumberInput,
            .stDateInput,
            .stSelectbox,
            .stMultiSelect,
            .stFileUploader,
            [data-testid="stChatInput"] {
                color: #14213d;
            }

            .stTextInput > div,
            .stTextArea > div,
            .stNumberInput > div,
            .stDateInput > div,
            .stSelectbox > div,
            .stMultiSelect > div,
            [data-testid="stChatInput"] > div {
                border-radius: 18px !important;
            }

            div[data-baseweb="input"],
            div[data-baseweb="textarea"],
            div[data-baseweb="select"] > div,
            [data-testid="stChatInput"] div[data-baseweb="textarea"],
            .stFileUploader section {
                overflow: hidden;
                border: 1px solid #dbe7ff !important;
                border-radius: 18px !important;
                background: #ffffff !important;
                color: #14213d !important;
                box-shadow: 0 8px 20px rgba(31, 78, 121, 0.06) !important;
                transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
            }

            div[data-baseweb="input"]:focus-within,
            div[data-baseweb="textarea"]:focus-within,
            div[data-baseweb="select"]:focus-within > div,
            [data-testid="stChatInput"] div[data-baseweb="textarea"]:focus-within {
                border-color: var(--sm-teal) !important;
                box-shadow: 0 0 0 4px rgba(20, 184, 180, 0.12), 0 12px 26px rgba(31, 78, 121, 0.08) !important;
            }

            .stTextInput input,
            .stTextArea textarea,
            .stNumberInput input,
            .stDateInput input,
            div[data-baseweb="select"] input,
            [data-testid="stChatInput"] textarea {
                border: 0 !important;
                outline: 0 !important;
                box-shadow: none !important;
                background: transparent !important;
                color: #14213d !important;
                caret-color: #14213d !important;
                font-weight: 650;
            }

            .stTextArea textarea,
            [data-testid="stChatInput"] textarea {
                resize: vertical;
            }

            .stTextInput input::placeholder,
            .stTextArea textarea::placeholder,
            .stNumberInput input::placeholder,
            .stDateInput input::placeholder,
            [data-testid="stChatInput"] textarea::placeholder {
                color: var(--sm-placeholder) !important;
                opacity: 1 !important;
                font-weight: 600;
            }

            div[data-baseweb="select"] *,
            div[data-baseweb="popover"] *,
            [role="listbox"] *,
            [role="option"] {
                color: #14213d !important;
            }

            div[data-baseweb="select"] svg,
            div[data-baseweb="select"] [aria-hidden="true"] {
                color: #52617d !important;
                fill: #52617d !important;
            }

            div[data-baseweb="popover"],
            [role="listbox"] {
                overflow: hidden;
                background: #ffffff !important;
                border: 1px solid #dbe7ff;
                border-radius: 18px !important;
                box-shadow: var(--sm-soft-shadow) !important;
            }

            [role="option"]:hover,
            [role="option"][aria-selected="true"] {
                background: #eefaff !important;
            }

            [data-testid="stChatInput"] {
                margin-top: 0.75rem;
            }

            [data-testid="stChatInput"] > div {
                background: rgba(255, 255, 255, 0.82);
                border-radius: 22px !important;
                padding: 0.25rem;
                box-shadow: 0 18px 45px rgba(57, 76, 119, 0.10);
            }

            .stFileUploader section,
            .stFileUploader label,
            .stFileUploader p,
            .stFileUploader small {
                color: #33415f;
            }

            .stRadio label,
            .stCheckbox label,
            .stSlider label,
            .stSelectbox label,
            .stTextInput label,
            .stTextArea label,
            .stNumberInput label,
            .stDateInput label {
                color: #26334f;
                font-weight: 730;
            }

            .stRadio p,
            .stCheckbox p {
                color: #26334f;
            }

            [data-testid="stAlert"] {
                border-radius: 18px;
                border: 1px solid rgba(216, 228, 243, 0.9);
                box-shadow: 0 10px 24px rgba(57, 76, 119, 0.08);
            }

            [data-testid="stAlert"] *,
            [data-testid="stException"] * {
                color: #14213d;
            }

            [data-testid="stAlert"][kind="success"] {
                background: var(--sm-success-bg);
            }

            [data-testid="stAlert"][kind="info"] {
                background: var(--sm-info-bg);
            }

            [data-testid="stAlert"][kind="warning"] {
                background: var(--sm-warning-bg);
            }

            [data-testid="stAlert"][kind="error"] {
                background: var(--sm-error-bg);
            }

            [data-testid="stChatMessage"] {
                border-radius: 22px;
                border: 1px solid rgba(220, 231, 247, 0.95);
                box-shadow: 0 10px 24px rgba(57, 76, 119, 0.08);
                background: rgba(255, 255, 255, 0.92);
                color: #14213d;
                margin-bottom: 0.9rem;
            }

            [data-testid="stChatMessage"] * {
                color: #14213d;
            }

            [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
                background: linear-gradient(135deg, #e8fff9, #eef6ff);
                border-color: rgba(20, 184, 180, 0.25);
            }

            [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
                background: linear-gradient(135deg, #ffffff, #fff8fb);
                border-color: rgba(167, 139, 250, 0.25);
            }

            [data-testid="stChatInput"] textarea,
            [data-testid="stChatInput"] input {
                background: #ffffff;
                color: #14213d;
            }

            div[data-testid="stMetric"] {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid rgba(220, 231, 247, 0.95);
                border-radius: 22px;
                padding: 1rem;
                box-shadow: var(--sm-soft-shadow);
            }

            div[data-testid="stMetric"] * {
                color: #14213d;
            }

            .stat-card {
                position: relative;
                overflow: hidden;
                min-height: 142px;
                border-radius: 24px;
                padding: 1.25rem;
                background: rgba(255, 255, 255, 0.94);
                border: 1px solid rgba(220, 231, 247, 0.95);
                box-shadow: var(--sm-soft-shadow);
            }

            .stat-card::after {
                content: "";
                position: absolute;
                right: -22px;
                top: -28px;
                width: 98px;
                height: 98px;
                border-radius: 999px;
                opacity: 0.25;
                background: var(--accent);
            }

            .stat-top {
                display: flex;
                gap: 0.9rem;
                align-items: center;
                position: relative;
                z-index: 2;
            }

            .stat-icon {
                width: 54px;
                height: 54px;
                border-radius: 19px;
                display: grid;
                place-items: center;
                font-size: 1.55rem;
                background: var(--soft);
                color: var(--accent);
            }

            .stat-label {
                color: var(--sm-muted);
                font-weight: 780;
                font-size: 0.95rem;
            }

            .stat-value {
                margin-top: 0.4rem;
                color: var(--accent);
                font-size: 2.45rem;
                line-height: 1;
                font-weight: 900;
            }

            .stat-hint {
                position: relative;
                z-index: 2;
                margin-top: 0.8rem;
                color: #53617d;
                font-size: 0.9rem;
                font-weight: 650;
            }

            .status-pill {
                display: inline-flex;
                align-items: center;
                padding: 0.28rem 0.65rem;
                border-radius: 999px;
                background: linear-gradient(135deg, #d9fbf4, #e9f3ff);
                color: #087c78;
                font-size: 0.76rem;
                font-weight: 850;
            }

            .empty-state {
                border: 2px dashed #d8e4f3;
                border-radius: 24px;
                padding: 2.1rem 1.25rem;
                text-align: center;
                background:
                    radial-gradient(circle at 12% 12%, rgba(20, 184, 180, 0.09), transparent 18%),
                    radial-gradient(circle at 88% 82%, rgba(251, 123, 191, 0.10), transparent 20%),
                    rgba(255, 255, 255, 0.84);
            }

            .empty-icon {
                width: 72px;
                height: 72px;
                margin: 0 auto 0.8rem;
                border-radius: 22px;
                display: grid;
                place-items: center;
                font-size: 2.1rem;
                background: linear-gradient(135deg, #d8fff6, #ddebff);
                box-shadow: 0 14px 26px rgba(20, 184, 180, 0.14);
            }

            .empty-state strong {
                display: block;
                color: #087c78;
                font-size: 1.05rem;
                margin-bottom: 0.25rem;
            }

            .empty-state p,
            .muted {
                color: var(--sm-muted);
            }

            .tip-card {
                margin-top: 1rem;
                display: flex;
                gap: 0.85rem;
                align-items: center;
                border-radius: 20px;
                padding: 1rem;
                background: linear-gradient(135deg, rgba(217, 251, 244, 0.94), rgba(232, 244, 255, 0.94));
                border: 1px solid rgba(151, 221, 229, 0.55);
                color: #26334f;
            }

            .tip-card * {
                color: #26334f;
            }

            .tip-icon {
                width: 42px;
                height: 42px;
                display: grid;
                place-items: center;
                border-radius: 16px;
                color: #ffffff;
                background: linear-gradient(135deg, var(--sm-teal), var(--sm-sky));
                flex: 0 0 auto;
            }

            .stTabs [data-baseweb="tab"] {
                background: #ffffff;
                border: 1px solid var(--sm-line);
                border-radius: 999px;
                padding: 0.45rem 0.9rem;
                color: #26334f;
            }

            .stTabs [data-baseweb="tab"] * {
                color: #26334f;
            }

            .stTabs [aria-selected="true"] {
                background: linear-gradient(135deg, #d8fff6, #eff0ff);
                border-color: rgba(20, 184, 180, 0.28);
            }

            hr {
                border: none;
                border-top: 1px solid var(--sm-line);
            }

            .auth-shell {
                max-width: 760px;
                margin: 2rem auto 1rem;
            }

            .auth-card {
                border-radius: 28px;
                padding: 2rem;
                background:
                    radial-gradient(circle at 85% 15%, rgba(255,255,255,0.6), transparent 24%),
                    linear-gradient(135deg, #cbfff3 0%, #dff0ff 48%, #ffe0ef 100%);
                border: 1px solid rgba(255,255,255,0.9);
                box-shadow: var(--sm-shadow);
            }

            .auth-card h1 {
                margin: 0.35rem 0 0.4rem;
                font-size: clamp(2rem, 5vw, 4rem);
            }

            .auth-card p {
                color: var(--sm-charcoal);
                font-weight: 700;
                max-width: 620px;
            }

            .auth-note {
                display: inline-flex;
                margin-top: 0.8rem;
                padding: 0.7rem 1rem;
                border-radius: 999px;
                background: rgba(255,255,255,0.76);
                color: var(--sm-ink);
                font-weight: 850;
                border: 1px solid rgba(255,255,255,0.95);
            }

            @media (max-width: 760px) {
                .block-container {
                    padding-left: 1rem;
                    padding-right: 1rem;
                }

                .hero {
                    min-height: 220px;
                    border-radius: 22px;
                }

                .hero::after {
                    opacity: 0.20;
                    right: 0;
                    bottom: 0;
                }

                .hero-content {
                    padding-left: 0;
                }

                .stat-card,
                .feature-card {
                    min-height: 132px;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_nav():
    """Render shared sidebar navigation."""
    user_name = st.session_state.get("user_name", "Ali Shair")
    user_email = st.session_state.get("user_email", "")
    initials = "".join(part[0] for part in user_name.split()[:2]).upper() or "AS"
    escaped_name = html.escape(user_name)
    escaped_email = html.escape(user_email)

    st.sidebar.markdown(
        f"""
        <div class="study-brand">
            <div class="study-logo">&#127891;</div>
            <div>
                <div class="study-brand-title">{escaped_name}'s <span>AI</span> Study Assistant</div>
                <div class="study-brand-subtitle">Your personal exam preparation workspace</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for label, page, icon in NAV_ITEMS:
        try:
            st.sidebar.page_link(page, label=f"{icon}  {label}")
        except Exception:
            fallback_url = _page_url_from_path(page)
            st.sidebar.markdown(
                f"<a class='fallback-nav-link' href='{fallback_url}'>{icon}  {html.escape(label)}</a>",
                unsafe_allow_html=True,
            )

    st.sidebar.markdown(
        f"""
        <div class="profile-card">
            <div class="profile-top">
                <div class="profile-avatar">{html.escape(initials)}</div>
                <div>
                    <div class="profile-name">{escaped_name}</div>
                    <div class="profile-role">{escaped_email or "CS Student"}</div>
                </div>
            </div>
            <div class="profile-mode">Offline AI Workspace</div>
        </div>
        <div class="sidebar-helper">
            <div class="sidebar-helper-icon">&#129302;</div>
            <strong>StudyMate AI</strong>
            <p>Personalized study power for Ali Shair.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.get("user_id"):
        if st.sidebar.button("Log Out", use_container_width=True):
            from modules.auth import logout

            logout()


def page_header(title, subtitle, kicker="StudyMate AI"):
    """Render a consistent colorful page hero."""
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-content">
                <div class="hero-kicker">{html.escape(kicker)}</div>
                <h1>{html.escape(title)}</h1>
                <p>{html.escape(subtitle)}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stat_card(label, value, hint, icon, accent, soft):
    """Render a colorful dashboard stat card."""
    st.markdown(
        f"""
        <div class="stat-card" style="--accent:{accent}; --soft:{soft};">
            <div class="stat-top">
                <div class="stat-icon">{icon}</div>
                <div>
                    <div class="stat-label">{html.escape(str(label))}</div>
                    <div class="stat-value">{html.escape(str(value))}</div>
                </div>
            </div>
            <div class="stat-hint">{html.escape(str(hint))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feature_card(title, text, icon, accent="#14b8b4", soft="#d8fff6"):
    """Render a compact colorful page feature card."""
    st.markdown(
        f"""
        <div class="feature-card" style="--accent:{accent}; --soft:{soft};">
            <div class="feature-icon">{icon}</div>
            <h3>{html.escape(title)}</h3>
            <p>{html.escape(text)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title, subtitle, icon="\U0001f4c1"):
    """Render a friendly empty state."""
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-icon">{icon}</div>
            <strong>{html.escape(title)}</strong>
            <p>{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tip(text):
    """Render a colorful tip card. Text may include small trusted HTML."""
    st.markdown(
        f"""
        <div class="tip-card">
            <div class="tip-icon">&#128161;</div>
            <div>{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text, icon="\u2726"):
    """Render a compact section title."""
    st.markdown(
        f'<div class="section-title"><span>{html.escape(text)}</span><span>{icon}</span></div>',
        unsafe_allow_html=True,
    )
