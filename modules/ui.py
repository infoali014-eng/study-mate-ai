"""
StudyMate AI – Core UI Module
Loads CSS assets and re-exports all UI helpers from the components package.

Architecture:
    assets/styles.css      → Base design system (tokens, typography, globals)
    assets/components.css  → Component-level styles
    assets/chat.css        → Chat interface styles
    modules/icons.py       → Lucide SVG icon library
    modules/theme.py       → Design tokens (Python)
    modules/components/    → Individual component modules
"""

import html as _html
import os
import re
import uuid

import streamlit as st
import streamlit.components.v1 as components

# ─────────────────────────────────────────────────────────────────────────────
# Re-exports so every existing caller of `from modules.ui import X` still works
# ─────────────────────────────────────────────────────────────────────────────
from modules.icons import icon                                           # noqa: F401
from modules.theme import (                                              # noqa: F401
    COLORS, SUBJECT_ACCENTS, FILE_TYPE_COLORS,
    SPACING, RADIUS, SHADOW, ANIMATION, TYPOGRAPHY, ICON_SIZE,
)
from modules.components.stat_card import render_stat_card                # noqa: F401
from modules.components.page_header import page_header                  # noqa: F401
from modules.components.sidebar import sidebar_nav, NAV_ITEMS, ADMIN_NAV_ITEMS  # noqa: F401
from modules.components.alerts import (                                  # noqa: F401
    render_tip, render_empty_state, render_success_state, render_ai_loading,
)
from modules.components.cards import (                                   # noqa: F401
    render_feature_card, render_subject_card, render_progress_panel,
    subject_visual, file_type_visual,
)

# ─────────────────────────────────────────────────────────────────────────────
# Backward-compatibility aliases (old callers used emoji-based helpers)
# ─────────────────────────────────────────────────────────────────────────────
THEME_PRESETS = {}          # kept so any stray import doesn't crash
SUBJECT_THEMES = []         # same
FILE_TYPE_STYLES = {}       # same


# ─────────────────────────────────────────────────────────────────────────────
# CSS Loader
# ─────────────────────────────────────────────────────────────────────────────
_CSS_CACHE: dict[str, str] = {}
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_css(filename: str) -> str:
    """Load a CSS file from the assets/ directory (cached)."""
    if filename not in _CSS_CACHE:
        path = os.path.join(_BASE_DIR, "assets", filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                _CSS_CACHE[filename] = f.read()
        except FileNotFoundError:
            _CSS_CACHE[filename] = ""
    return _CSS_CACHE[filename]


# ─────────────────────────────────────────────────────────────────────────────
# apply_theme  (called on every page, once per rerun)
# ─────────────────────────────────────────────────────────────────────────────
def apply_theme():
    """
    Inject the full design system CSS into the Streamlit app.
    Loads styles.css + components.css from the assets/ directory.
    Called at the top of every page after st.set_page_config().
    """
    base_css     = _load_css("styles.css")
    comp_css     = _load_css("components.css")
    chat_css     = _load_css("chat.css")

    # Sidebar icon-link override: make st.page_link look like sm-nav-link
    sidebar_icon_fix = """
        [data-testid="stSidebar"] [data-testid="stPageLink"] a {
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
            padding: 9px 12px !important;
            border-radius: 12px !important;
            color: #6B7280 !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            text-decoration: none !important;
            transition: all 200ms ease !important;
            border: 1px solid transparent !important;
            margin: 2px 0 !important;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
            background: #F9FAFB !important;
            color: #111827 !important;
            border-color: #E5E7EB !important;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
            background: #F0FDFA !important;
            color: #0F9D8C !important;
            border-color: #CCFBF1 !important;
            font-weight: 600 !important;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a p,
        [data-testid="stSidebar"] [data-testid="stPageLink"] a span {
            color: inherit !important;
            font-weight: inherit !important;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] {
            display: none !important;
        }
    """

    full_css = f"<style>{base_css}\n{comp_css}\n{chat_css}\n{sidebar_icon_fix}</style>"
    st.markdown(full_css, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# section_title  (standalone helper used directly in pages)
# ─────────────────────────────────────────────────────────────────────────────
def section_title(text: str, icon_name: str = "chevron-right"):
    """Render a clean section heading with an SVG accent icon."""
    svg = icon(icon_name, size=16, color="#14B8A6")
    st.markdown(
        f'<div class="sm-section-title">{svg}<span>{_html.escape(text)}</span></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# render_file_badge  (used in library and upload pages)
# ─────────────────────────────────────────────────────────────────────────────
def render_file_badge(file_type: str, label: str | None = None):
    """Render a compact file type badge pill."""
    visual = file_type_visual(file_type)
    badge_label = label or (file_type or "FILE").upper()
    file_icon = icon(visual["icon_key"], size=12, color=visual["accent"])
    st.markdown(
        f'<span class="sm-file-badge" style="'
        f'background:{visual["bg"]}; color:{visual["accent"]};">'
        f'{file_icon} {_html.escape(str(badge_label))}</span>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# render_announcement  (called from page_header)
# ─────────────────────────────────────────────────────────────────────────────
def render_announcement():
    """Render an optional app-wide announcement banner from branding settings."""
    try:
        from modules.database import get_branding_settings
        settings = get_branding_settings()
    except Exception:
        return
    active  = str(settings.get("announcement_active", "false")).lower() == "true"
    message = (settings.get("announcement_message") or "").strip()
    if not active or not message:
        return
    kind = settings.get("announcement_type", "info")
    if kind == "success":
        st.success(message)
    elif kind == "warning":
        st.warning(message)
    else:
        st.info(message)


# ─────────────────────────────────────────────────────────────────────────────
# render_ai_markdown  (rich Mermaid + Markdown renderer for Chat page)
# ─────────────────────────────────────────────────────────────────────────────
def _clean_mermaid_diagram(diagram: str) -> str:
    """Strip AI wrapper text before Mermaid parses the diagram."""
    allowed_starts = (
        "graph ", "flowchart ", "sequenceDiagram", "classDiagram",
        "stateDiagram", "stateDiagram-v2", "erDiagram", "journey",
        "gantt", "pie", "mindmap", "timeline", "quadrantChart", "gitGraph",
    )
    cleaned_lines = []
    for raw_line in str(diagram or "").splitlines():
        line  = raw_line.strip()
        lower = line.lower()
        if not line:
            cleaned_lines.append(raw_line)
            continue
        if "mermaid" in lower and ("version" in lower or "code block" in lower):
            continue
        if lower.startswith(("here's", "here is", "syntax error", "error in text")):
            continue
        cleaned_lines.append(raw_line)

    cleaned = "\n".join(cleaned_lines).strip()
    lines   = cleaned.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if any(stripped.startswith(s) for s in allowed_starts):
            return "\n".join(lines[index:]).strip()
    return cleaned


def render_ai_markdown(content: str):
    """Render AI Markdown and inline Mermaid flowcharts."""
    text    = content or ""
    pattern = re.compile(r"```mermaid\s*(.*?)```", re.DOTALL | re.IGNORECASE)
    last_end     = 0
    found_mermaid = False

    for match in pattern.finditer(text):
        before = text[last_end : match.start()].strip()
        if before:
            st.markdown(before)

        diagram = match.group(1).strip()
        if diagram:
            found_mermaid = True
            diagram = _clean_mermaid_diagram(diagram)
            import json
            safe_json  = json.dumps(diagram)
            mermaid_id = f"mermaid-{uuid.uuid4().hex}"
            components.html(
                f"""
                <div class="mermaid" id="{mermaid_id}"></div>
                <pre id="{mermaid_id}-fallback"
                     style="display:none; white-space:pre-wrap; background:#F9FAFB;
                            border:1px solid #E5E7EB; border-radius:8px; padding:12px;
                            font-size:0.8125rem;"></pre>
                <script type="module">
                    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                    mermaid.initialize({{ startOnLoad: false, theme: 'base', securityLevel: 'loose' }});
                    const el = document.getElementById('{mermaid_id}');
                    const fb = document.getElementById('{mermaid_id}-fallback');
                    el.textContent = {safe_json};
                    mermaid.run({{ nodes: [el] }}).catch(() => {{
                        el.style.display = 'none';
                        fb.style.display = 'block';
                        fb.textContent   = {safe_json};
                    }});
                </script>
                """,
                height=360,
                scrolling=True,
            )
        last_end = match.end()

    remaining = text[last_end:].strip()
    if remaining:
        st.markdown(remaining)
    elif not found_mermaid:
        st.markdown(text)
