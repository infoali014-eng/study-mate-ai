import streamlit as st

from modules.auth import require_login
from modules.database import get_branding_settings, init_db
from modules.ui import apply_theme, page_header, render_feature_card, section_title, sidebar_nav


st.set_page_config(page_title="About - StudyMate AI", layout="wide")
require_login()
init_db()
apply_theme()
sidebar_nav()

branding = get_branding_settings()

page_header(
    branding["app_name"],
    branding["product_tagline"],
    branding["app_subtitle"],
)

section_title("What is StudyMate AI?", "book")
with st.container(border=True):
    st.write(branding["about_what"])

section_title("Why I Built It", "zap")
with st.container(border=True):
    st.write(branding["about_why"])
    st.markdown(f"**Mission:** {branding['mission_statement']}")

section_title("Creator", "user")
with st.container(border=True):
    st.markdown(f"### {branding['creator_name']}")
    st.caption(branding["creator_role"])
    st.write(branding["creator_description"])
    st.write(f"Email: {branding['creator_email']}")
    link_cols = st.columns(4)
    link_cols[0].write(f"GitHub: {branding['github_link']}")
    link_cols[1].write(f"Portfolio: {branding['portfolio_link']}")
    link_cols[2].write(f"LinkedIn: {branding['linkedin_link']}")
    link_cols[3].write(f"Instagram: {branding['instagram_link']}")

section_title("Feature Highlights", "star")
features = [line.strip() for line in branding["feature_highlights"].splitlines() if line.strip()]
cols = st.columns(3)
for index, feature in enumerate(features):
    with cols[index % 3]:
        render_feature_card(feature, "Built into your personal study workspace.", "\u2714", "#14b8b4", "#d8fff6")

st.caption(f"{branding['footer_text']} | {branding['app_version']}")
