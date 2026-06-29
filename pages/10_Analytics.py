import streamlit as st

from modules.auth import require_login
from modules.database import init_db
from modules.library_repository import get_subjects
from modules.ui import apply_theme, page_header, sidebar_nav
from services.analytics_service import AnalyticsService
from services.recommendation_engine import RecommendationEngine
from modules.analytics_ui import (
    render_filters,
    render_overview_cards,
    render_goals_and_insights,
    render_charts,
    render_performance_metrics,
    render_ai_recommendations,
    render_timeline
)

st.set_page_config(page_title="Analytics Dashboard - StudyMate AI", layout="wide")
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

# Initialize session state for AI recommendations pinning
if "pinned_recs" not in st.session_state:
    st.session_state.pinned_recs = []

page_header(
    "Analytics Dashboard",
    "Track your learning efficiency, progress goals, achievements, and AI recommendations.",
    "Analytics"
)

# ── 1. Load Filter Input Selectors ───────────────────────────────────────────
subjects = get_subjects(user_id=user_id)
selected_sub_id, selected_range = render_filters(subjects)

# ── 2. Load Recommendation Action Callbacks ──────────────────────────────────
def handle_recommendation_action(action_type: str, rec_id: str):
    if action_type == "dismiss" and rec_id:
        if AnalyticsService.dismiss_recommendation(rec_id):
            st.success("Recommendation dismissed.")
            st.rerun()
    elif action_type == "pin" and rec_id:
        if rec_id in st.session_state.pinned_recs:
            st.session_state.pinned_recs.remove(rec_id)
        else:
            st.session_state.pinned_recs.append(rec_id)
        st.rerun()
    elif action_type == "refresh":
        with st.spinner("Analyzing learning profile and generating recommendations..."):
            RecommendationEngine.generate_recommendations(user_id)
        st.success("AI Insights updated successfully.")
        st.rerun()

# ── 3. Fetch Unified Analytics Dataset ────────────────────────────────────────
with st.spinner("Fetching performance metrics..."):
    dashboard_data = AnalyticsService.get_dashboard_data(
        user_id=user_id,
        subject_id=selected_sub_id,
        date_range=selected_range
    )

# ── 4. Compose UI Sections ───────────────────────────────────────────────────
st.write("")
render_overview_cards(dashboard_data)

st.markdown('<hr style="margin:24px 0; border:none; border-top:1px solid var(--color-border);">', unsafe_allow_html=True)
render_goals_and_insights(dashboard_data)

st.markdown('<hr style="margin:24px 0; border:none; border-top:1px solid var(--color-border);">', unsafe_allow_html=True)
render_charts(dashboard_data)

st.markdown('<hr style="margin:24px 0; border:none; border-top:1px solid var(--color-border);">', unsafe_allow_html=True)
render_performance_metrics(dashboard_data)

st.markdown('<hr style="margin:24px 0; border:none; border-top:1px solid var(--color-border);">', unsafe_allow_html=True)
render_ai_recommendations(dashboard_data, handle_recommendation_action)

st.markdown('<hr style="margin:24px 0; border:none; border-top:1px solid var(--color-border);">', unsafe_allow_html=True)
render_timeline(dashboard_data)
