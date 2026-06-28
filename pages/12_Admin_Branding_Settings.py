import streamlit as st

from modules.auth import require_admin
from modules.database import (
    BRANDING_DEFAULTS,
    get_branding_settings,
    init_db,
    reset_branding_settings_to_defaults,
    save_branding_settings,
)
from modules.ui import apply_theme, page_header, section_title, sidebar_nav


st.set_page_config(page_title="Branding Settings - StudyMate AI", layout="wide")
require_admin()
init_db()
apply_theme()
sidebar_nav()

settings = get_branding_settings()

page_header(
    "Branding Settings",
    "Edit public app branding, creator information, About page content, and announcement text.",
    "Admin Controls",
)

section_title("Branding", "star")
with st.form("branding_settings_form"):
    col1, col2 = st.columns(2)
    with col1:
        app_name = st.text_input("App name", value=settings["app_name"])
        app_subtitle = st.text_input("App subtitle", value=settings["app_subtitle"])
        product_tagline = st.text_input("Product tagline", value=settings["product_tagline"])
        app_version = st.text_input("App version", value=settings["app_version"])
        footer_text = st.text_input("Footer text", value=settings["footer_text"])
    with col2:
        creator_name = st.text_input("Creator name", value=settings["creator_name"])
        creator_role = st.text_input("Creator role", value=settings["creator_role"])
        creator_email = st.text_input("Creator email", value=settings["creator_email"])
        github_link = st.text_input("GitHub link", value=settings["github_link"])
        portfolio_link = st.text_input("Portfolio link", value=settings["portfolio_link"])
        linkedin_link = st.text_input("LinkedIn link", value=settings["linkedin_link"])
        instagram_link = st.text_input("Instagram link", value=settings["instagram_link"])

    creator_description = st.text_area("Creator description", value=settings["creator_description"], height=100)
    about_what = st.text_area("What is StudyMate AI?", value=settings["about_what"], height=120)
    about_why = st.text_area("Why I built it", value=settings["about_why"], height=100)
    mission_statement = st.text_area("Mission statement", value=settings["mission_statement"], height=90)
    feature_highlights = st.text_area("Feature highlights, one per line", value=settings["feature_highlights"], height=160)

    st.markdown("**Announcement Banner**")
    ann_col1, ann_col2 = st.columns(2)
    with ann_col1:
        announcement_active = st.checkbox(
            "Announcement active",
            value=str(settings["announcement_active"]).lower() == "true",
        )
        announcement_type = st.selectbox(
            "Announcement type",
            ["info", "success", "warning"],
            index=["info", "success", "warning"].index(settings.get("announcement_type", "info")),
        )
    with ann_col2:
        announcement_message = st.text_area("Announcement message", value=settings["announcement_message"], height=95)

    st.markdown("**Simple Feature Toggles**")
    toggle1, toggle2, toggle3 = st.columns(3)
    with toggle1:
        enable_public_signup = st.checkbox("Enable public signup", value=str(settings["enable_public_signup"]).lower() == "true")
    with toggle2:
        enable_demo_mode = st.checkbox("Enable Demo Mode", value=str(settings["enable_demo_mode"]).lower() == "true")
    with toggle3:
        enable_google_login = st.checkbox("Enable Google login UI", value=str(settings["enable_google_login"]).lower() == "true")

    save_button = st.form_submit_button("Save Branding Settings", type="primary", use_container_width=True)

if save_button:
    save_branding_settings(
        {
            "app_name": app_name,
            "app_subtitle": app_subtitle,
            "product_tagline": product_tagline,
            "creator_name": creator_name,
            "creator_role": creator_role,
            "creator_description": creator_description,
            "creator_email": creator_email,
            "github_link": github_link,
            "portfolio_link": portfolio_link,
            "linkedin_link": linkedin_link,
            "instagram_link": instagram_link,
            "app_version": app_version,
            "footer_text": footer_text,
            "about_what": about_what,
            "about_why": about_why,
            "mission_statement": mission_statement,
            "feature_highlights": feature_highlights,
            "announcement_active": "true" if announcement_active else "false",
            "announcement_type": announcement_type,
            "announcement_message": announcement_message,
            "enable_public_signup": "true" if enable_public_signup else "false",
            "enable_demo_mode": "true" if enable_demo_mode else "false",
            "enable_google_login": "true" if enable_google_login else "false",
        }
    )
    st.success("Branding settings saved.")
    st.rerun()

reset_col, preview_col = st.columns(2)
with reset_col:
    if st.button("Reset Branding to Defaults", use_container_width=True):
        reset_branding_settings_to_defaults()
        st.success("Branding reset to defaults.")
        st.rerun()
with preview_col:
    if st.button("Preview Current Defaults", use_container_width=True):
        st.json(BRANDING_DEFAULTS)
