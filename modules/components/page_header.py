"""
StudyMate AI – Page Header Component
"""
import html as _html
import streamlit as st
from modules.icons import icon


def page_header(title: str, subtitle: str = "", kicker: str = "StudyMate AI"):
    """
    Render a clean, minimal page header with kicker, title, and subtitle.
    """
    from modules.ui import render_announcement
    render_announcement()

    kicker_icon = icon("graduation-cap", size=14, color="#14B8A6")
    st.markdown(
        f"""
        <div class="sm-page-header">
            <div class="sm-page-header-kicker">
                {kicker_icon}
                <span>{_html.escape(kicker)}</span>
            </div>
            <h1>{_html.escape(title)}</h1>
            {'<p>' + _html.escape(subtitle) + '</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
