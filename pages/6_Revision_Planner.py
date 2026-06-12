import os
from datetime import date, timedelta

import streamlit as st

from modules.ai_engine import OLLAMA_MODEL
from modules.database import (
    get_revision_plans,
    get_subjects,
    get_weak_topics,
    init_db,
    save_revision_plan,
)
from modules.planner import generate_revision_plan


st.set_page_config(page_title="Revision Planner - StudyMate AI", layout="wide")
init_db()

st.sidebar.title("StudyMate AI")
st.sidebar.page_link("pages/1_Dashboard.py", label="Dashboard")
st.sidebar.page_link("pages/2_Upload_Notes.py", label="Upload Notes")
st.sidebar.page_link("pages/3_Chat_With_Notes.py", label="Chat With Notes")
st.sidebar.page_link("pages/4_Quiz_Mode.py", label="Quiz Mode")
st.sidebar.page_link("pages/5_Flashcards.py", label="Flashcards")
st.sidebar.page_link("pages/6_Revision_Planner.py", label="Revision Planner")

st.title("Revision Planner")
st.caption("Generate and save a day-wise study plan for your exam.")

subjects = get_subjects()
if not subjects:
    st.warning("Create a subject first.")
    st.stop()

subject_options = {subject["name"]: subject for subject in subjects}
selected_name = st.selectbox("Choose subject", list(subject_options.keys()))
selected_subject = subject_options[selected_name]

weak_topic_rows = get_weak_topics(subject_id=selected_subject["id"])
available_weak_topics = [row["topic"] for row in weak_topic_rows]

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
        model = st.text_input("Ollama model", value=os.getenv("OLLAMA_MODEL", OLLAMA_MODEL))

    generate_button = st.button(
        "Generate and Save Plan",
        type="primary",
        use_container_width=True,
    )

manual_topics = [
    topic.strip()
    for topic in extra_weak_topics.splitlines()
    if topic.strip()
]
all_weak_topics = selected_weak_topics + [
    topic for topic in manual_topics if topic not in selected_weak_topics
]

if "latest_revision_plan" not in st.session_state:
    st.session_state.latest_revision_plan = None

if generate_button:
    with st.spinner("Generating day-wise study plan with Ollama..."):
        plan_text = generate_revision_plan(
            subject_name=selected_subject["name"],
            exam_date=exam_date,
            preparation_level=preparation_level,
            confidence_level=confidence_level,
            weak_topics=all_weak_topics,
            model=model,
        )

    plan_id = save_revision_plan(
        subject_id=selected_subject["id"],
        exam_date=exam_date,
        preparation_level=preparation_level,
        confidence_level=confidence_level,
        weak_topics=all_weak_topics,
        plan_text=plan_text,
    )

    st.session_state.latest_revision_plan = {
        "id": plan_id,
        "plan_text": plan_text,
    }
    st.success(f"Revision plan generated and saved locally. Plan id: {plan_id}")

if st.session_state.latest_revision_plan:
    st.subheader("Latest Generated Plan")
    st.markdown(st.session_state.latest_revision_plan["plan_text"])

saved_plans = get_revision_plans(subject_id=selected_subject["id"])

st.subheader("Saved Plans")
if not saved_plans:
    st.info("No revision plans saved for this subject yet.")
else:
    for plan in saved_plans:
        with st.expander(
            f"Plan {plan['id']} | Exam: {plan['exam_date']} | Created: {plan['created_at']}"
        ):
            st.write(f"Preparation level: {plan['preparation_level']} / 10")
            st.write(f"Confidence level: {plan['confidence_level']} / 10")
            st.write(f"Weak topics: {plan['weak_topics'] or 'None selected'}")
            st.markdown(plan["plan_text"])
