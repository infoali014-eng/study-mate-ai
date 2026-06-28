"""
StudyMate AI – Alert & State Components
"""
import html as _html
import streamlit as st
from modules.icons import icon


def render_tip(text: str):
    """Render a clean info/tip banner with teal left border."""
    tip_icon = icon("lightbulb", size=16, color="#3B82F6")
    st.markdown(
        f"""
        <div class="sm-tip">
            <div class="sm-tip-icon">{tip_icon}</div>
            <div>{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, subtitle: str, icon_name: str = "inbox"):
    """Render an upgraded empty state with a premium vector SVG illustration."""
    # Premium custom vector illustration representing an empty folder/inbox
    illustration_svg = (
        '<svg width="80" height="80" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-bottom:12px;">'
        '<rect x="12" y="16" width="40" height="36" rx="6" stroke="var(--color-primary)" stroke-width="2" stroke-dasharray="4 4" />'
        '<path d="M22 28H42M22 36H34" stroke="var(--color-text-muted)" stroke-width="2" stroke-linecap="round" />'
        '<circle cx="32" cy="44" r="3" fill="var(--color-primary)" />'
        '</svg>'
    )
    st.markdown(
        f"""
        <div class="sm-empty" style="display:flex; flex-direction:column; align-items:center; text-align:center; padding:30px 20px;">
            {illustration_svg}
            <div class="sm-empty-title" style="font-size:1rem; font-weight:600; color:var(--color-text); margin-bottom:4px;">{_html.escape(title)}</div>
            <div class="sm-empty-subtitle" style="font-size:0.875rem; color:var(--color-text-secondary);">{_html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_success_state(title: str, subtitle: str, icon_name: str = "check-circle"):
    """Render a success confirmation banner."""
    success_icon = icon(icon_name, size=18, color="#22C55E")
    st.markdown(
        f"""
        <div class="sm-tip" style="background:#F0FDF4; border-color:#BBF7D0; border-left-color:#22C55E;">
            <div class="sm-tip-icon">{success_icon}</div>
            <div>
                <strong style="display:block; color:#15803D; margin-bottom:2px;">{_html.escape(title)}</strong>
                <span style="color:#166534; font-size:0.875rem;">{_html.escape(subtitle)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ai_loading(label: str = "StudyMate is thinking"):
    """Render an animated AI loading indicator with a rotating spinner and bouncing dots."""
    st.markdown(
        f"""
        <div class="sm-ai-loading" style="display:flex; align-items:center; gap:10px; padding:12px; background:var(--color-surface); border:1px solid var(--color-border); border-radius:var(--radius-lg); width:fit-content; margin:8px 0;">
            <div class="sm-spinner" style="width:16px; height:16px; border:2px solid var(--color-primary-light); border-top-color:var(--color-primary); border-radius:50%; animation:spin 800ms linear infinite;"></div>
            <div class="sm-dots" style="display:flex; gap:3px;">
                <span style="width:5px; height:5px; background:var(--color-primary); border-radius:50%; animation:bounce 1.2s infinite ease-in-out;"></span>
                <span style="width:5px; height:5px; background:var(--color-primary); border-radius:50%; animation:bounce 1.2s infinite ease-in-out; animation-delay:200ms;"></span>
                <span style="width:5px; height:5px; background:var(--color-primary); border-radius:50%; animation:bounce 1.2s infinite ease-in-out; animation-delay:400ms;"></span>
            </div>
            <div style="font-size:0.8125rem; font-weight:500; color:var(--color-text-secondary);">{_html.escape(label)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
