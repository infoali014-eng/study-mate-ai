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
    """Render a clean empty state with centered icon and text."""
    empty_icon = icon(icon_name, size=24, color="#9CA3AF")
    st.markdown(
        f"""
        <div class="sm-empty">
            <div class="sm-empty-icon">{empty_icon}</div>
            <div class="sm-empty-title">{_html.escape(title)}</div>
            <div class="sm-empty-subtitle">{_html.escape(subtitle)}</div>
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
    """Render an animated AI loading indicator with three dots."""
    st.markdown(
        f"""
        <div class="sm-ai-loading">
            <div class="sm-dots">
                <span></span><span></span><span></span>
            </div>
            <div>{_html.escape(label)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
