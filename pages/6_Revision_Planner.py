from datetime import date, timedelta

import streamlit as st

from modules import ai_engine
from modules.auth import require_login
from modules.database import (
    get_revision_plans,
    get_weak_topics,
    init_db,
    save_revision_plan,
)
from modules.library_repository import (
    get_subjects,
)
from modules.planner import generate_revision_plan
from modules.security import clean_text
from modules.ui import (
    apply_theme,
    page_header,
    render_ai_loading,
    render_empty_state,
    render_feature_card,
    section_title,
    sidebar_nav,
)


def get_provider_label():
    """Return the selected provider, even if Streamlit is holding an older module."""
    if hasattr(ai_engine, "get_selected_provider"):
        return ai_engine.get_selected_provider()
    return "Ollama"


st.set_page_config(page_title="Revision Planner - StudyMate AI", layout="wide")
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

page_header(
    "Revision Planner",
    "Generate and save a day-wise study plan for your exam.",
    "Exam Roadmap",
)

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card("Exam countdown", "Plan from today through your exam date.", "\U0001f5d3\ufe0f", "#2f7df6", "#e3efff")
with feature2:
    render_feature_card("Confidence aware", "Use preparation and confidence levels to shape the plan.", "\U0001f4ca", "#ffb703", "#fff3c4")
with feature3:
    render_feature_card("Weak-topic focus", "Prioritize topics marked weak in quizzes and flashcards.", "\U0001f4cc", "#ff637d", "#ffe3e9")

subjects = get_subjects(user_id=user_id)
if not subjects:
    render_empty_state(
        "No subject to plan yet.",
        "Create a subject first, then build a revision plan.",
        "\U0001f5d3\ufe0f",
    )
    st.stop()

subject_options = {subject["name"]: subject for subject in subjects}
selected_name = st.selectbox("Choose subject", list(subject_options.keys()))
selected_subject = subject_options[selected_name]

weak_topic_rows = get_weak_topics(subject_id=selected_subject["id"], user_id=user_id)
available_weak_topics = [row["topic"] for row in weak_topic_rows]

section_title("Plan Builder", "\U0001f4ca")
with st.container(border=True):
    col1, col2 = st.columns(2)

    with col1:
        exam_date = st.date_input(
            "Exam date",
            value=date.today() + timedelta(days=7),
            min_value=date.today(),
        )
        preparation_level = st.slider(
            "Preparation level out of 10",
            min_value=1,
            max_value=10,
            value=5,
        )
        confidence_level = st.slider(
            "Confidence level out of 10",
            min_value=1,
            max_value=10,
            value=5,
        )

    with col2:
        selected_weak_topics = st.multiselect(
            "Select weak topics",
            available_weak_topics,
            default=available_weak_topics[:3],
            help="Weak topics come from Quiz Mode and Flashcards.",
        )
        extra_weak_topics = st.text_area(
            "Add more weak topics",
            placeholder="Write one topic per line, if needed.",
            height=110,
        )
        st.info(f"AI provider: {get_provider_label()}. Change it from AI Settings.")

    generate_button = st.button(
        "Generate and Save Plan",
        type="primary",
        use_container_width=True,
    )

manual_topics = [
    clean_text(topic, max_length=120)
    for topic in extra_weak_topics.splitlines()
    if clean_text(topic, max_length=120)
]
all_weak_topics = selected_weak_topics + [
    topic for topic in manual_topics if topic not in selected_weak_topics
]

if "latest_revision_plan" not in st.session_state:
    st.session_state.latest_revision_plan = None

if generate_button:
    loading_slot = st.empty()
    with loading_slot:
        render_ai_loading("Building your revision roadmap")
    try:
        plan_text = generate_revision_plan(
            subject_name=selected_subject["name"],
            exam_date=exam_date,
            preparation_level=preparation_level,
            confidence_level=confidence_level,
            weak_topics=all_weak_topics,
        )
    finally:
        loading_slot.empty()

    plan_id = save_revision_plan(
        subject_id=selected_subject["id"],
        exam_date=exam_date,
        preparation_level=preparation_level,
        confidence_level=confidence_level,
        weak_topics=all_weak_topics,
        plan_text=plan_text,
        user_id=user_id,
    )

    st.session_state.latest_revision_plan = {
        "id": plan_id,
        "plan_text": plan_text,
    }
    st.success("Revision plan generated and saved locally.")

if st.session_state.latest_revision_plan:
    section_title("Latest Generated Plan", "\u2728")
    with st.container(border=True):
        st.markdown(st.session_state.latest_revision_plan["plan_text"])

saved_plans = get_revision_plans(subject_id=selected_subject["id"], user_id=user_id)

section_title("Saved Plans", "\U0001f4da")
if not saved_plans:
    render_empty_state(
        "No saved plans yet.",
        "Generate your first AI revision plan and it will appear here.",
        "\U0001f5d3\ufe0f",
    )
else:
    for plan in saved_plans:
        with st.expander(
            f"Exam: {plan['exam_date']} | Created: {plan['created_at']}"
        ):
            st.write(f"Preparation level: {plan['preparation_level']} / 10")
            st.write(f"Confidence level: {plan['confidence_level']} / 10")
            st.write(f"Weak topics: {plan['weak_topics'] or 'None selected'}")
            st.markdown(plan["plan_text"])
