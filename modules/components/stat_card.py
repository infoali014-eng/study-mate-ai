"""
StudyMate AI – Stat Card Component
"""
import html as _html
import streamlit as st
from modules.icons import icon


def render_stat_card(
    label: str,
    value,
    hint: str = "",
    icon_name: str = "bar-chart-2",
    accent: str = "#14B8A6",
    accent_bg: str = "#F0FDFA",
):
    """
    Render a clean, minimal analytics stat card.

    Args:
        label:      Card title (e.g. "Quiz Accuracy")
        value:      The main metric value (number or string)
        hint:       Sub-label below the value
        icon_name:  Lucide icon name string
        accent:     Left border + icon color (hex)
        accent_bg:  Icon background color (hex)
    """
    svg = icon(icon_name, size=20, color=accent)
    st.markdown(
        f"""
        <div class="sm-stat-card" style="--card-accent:{accent}; --card-accent-bg:{accent_bg};">
            <div class="sm-stat-header">
                <div class="sm-stat-icon">{svg}</div>
            </div>
            <div class="sm-stat-label">{_html.escape(str(label))}</div>
            <div class="sm-stat-value">{_html.escape(str(value))}</div>
            <div class="sm-stat-hint">{_html.escape(str(hint))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
