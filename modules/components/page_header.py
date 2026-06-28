"""
StudyMate AI – Page Header Component
"""
import html as _html
import streamlit as st
from modules.icons import icon


def page_header(title: str, subtitle: str = "", kicker: str = "StudyMate AI"):
    """
    Render a clean, minimal page header with kicker, title, and subtitle,
    accompanied by the user's avatar on the top right.
    """
    from modules.ui import render_announcement
    render_announcement()

    user_name = st.session_state.get("user_name", "Student")
    initials = "".join(p[0] for p in user_name.split()[:2]).upper() or "ST"
    avatar_url = st.session_state.get("profile_image_url")
    if avatar_url:
        avatar_html = f'<img src="{_html.escape(avatar_url)}" style="width:36px; height:36px; border-radius:50%; object-fit:cover; border: 1px solid var(--color-border);">'
    else:
        avatar_html = f'<div style="width:36px; height:36px; border-radius:50%; background:var(--color-primary-muted); color:var(--color-primary-dark); font-weight:700; font-size:0.8125rem; display:flex; align-items:center; justify-content:center; border: 1px solid var(--color-primary-light);">{_html.escape(initials)}</div>'

    kicker_icon = icon("graduation-cap", size=14, color="#14B8A6")
    st.markdown(
        f"""
        <div class="sm-page-header" style="display:flex; justify-content:space-between; align-items:center; gap:16px;">
            <div style="min-width:0;">
                <div class="sm-page-header-kicker">
                    {kicker_icon}
                    <span>{_html.escape(kicker)}</span>
                </div>
                <h1>{_html.escape(title)}</h1>
                {'<p>' + _html.escape(subtitle) + '</p>' if subtitle else ''}
            </div>
            <div style="display:flex; align-items:center; gap:10px; flex-shrink:0; background:var(--color-surface); padding:6px 12px; border-radius:var(--radius-lg); border:1px solid var(--color-border);">
                <span style="font-size:0.8125rem; font-weight:600; color:var(--color-text);">{_html.escape(user_name)}</span>
                {avatar_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
