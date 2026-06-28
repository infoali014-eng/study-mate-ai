import streamlit as st

from modules import ai_engine
from modules.auth import require_login
from modules.database import (
    get_quiz_results,
    init_db,
    save_quiz_result,
    update_weak_topic,
)
from modules.library_repository import (
    get_subjects,
)
from modules.quiz_generator import check_quiz_answers, generate_quiz
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


QUESTION_TYPES = ["MCQ", "Short", "Long", "Viva"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]


def get_provider_label():
    """Return the selected provider, even if Streamlit is holding an older module."""
    if hasattr(ai_engine, "get_selected_provider"):
        return ai_engine.get_selected_provider()
    return "Ollama"


st.set_page_config(page_title="Quiz Mode - StudyMate AI", layout="wide")
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

page_header(
    "Quiz Mode",
    "Generate questions from uploaded notes, answer them, and get AI feedback.",
    "Practice Lab",
)

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card("Question types", "Practice MCQs, short answers, long answers, or viva prompts.", "\u2754", "#2f7df6", "#e3efff")
with feature2:
    render_feature_card("Difficulty control", "Choose Easy, Medium, or Hard before generating.", "\U0001f3af", "#ff637d", "#ffe3e9")
with feature3:
    render_feature_card("AI marking", "Get marks, feedback, and weak-topic tracking.", "\U0001f4dd", "#14b8b4", "#d8fff6")

subjects = get_subjects(user_id=user_id)
if not subjects:
    render_empty_state(
        "No quiz source yet.",
        "Create a subject and upload notes before generating a quiz.",
        "\U0001f4dd",
    )
    st.stop()

subject_options = {subject["name"]: subject for subject in subjects}
subject_names = list(subject_options.keys())
prefill_subject_id = st.session_state.pop("quiz_prefill_subject_id", None)
default_subject_index = 0
if prefill_subject_id:
    for index, subject_name in enumerate(subject_names):
        if subject_options[subject_name]["id"] == prefill_subject_id:
            default_subject_index = index
            break
prefill_topic = st.session_state.pop("quiz_prefill_topic", "")

section_title("Quiz Builder", "\U0001f3af")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        selected_name = st.selectbox("Choose subject", subject_names, index=default_subject_index)
        question_type = st.selectbox("Question type", QUESTION_TYPES)
        difficulty = st.selectbox("Difficulty", DIFFICULTIES)
    with col2:
        topic = st.text_input("Topic", value=prefill_topic, placeholder="Example: cell structure")
        question_count = st.number_input(
            "Number of questions",
            min_value=1,
            max_value=10,
            value=5,
            step=1,
        )
        st.info(f"AI provider: {get_provider_label()}. Change it from AI Settings.")

    generate_button = st.button("Generate Quiz", type="primary", use_container_width=True)

selected_subject = subject_options[selected_name]

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "quiz_feedback" not in st.session_state:
    st.session_state.quiz_feedback = None

if generate_button:
    clean_topic = clean_text(topic, max_length=120)
    if not clean_topic:
        st.warning("Please enter a topic.")
    else:
        loading_slot = st.empty()
        with loading_slot:
            render_ai_loading("Searching notes and building your quiz")
        try:
            quiz_data = generate_quiz(
                subject_id=selected_subject["id"],
                topic=clean_topic,
                question_type=question_type,
                difficulty=difficulty,
                question_count=int(question_count),
                user_id=user_id,
            )
        finally:
            loading_slot.empty()

        if quiz_data["error"]:
            st.error(quiz_data["error"])
        elif not quiz_data["questions"]:
            st.error("The selected AI provider did not return usable questions. Try again with a clearer topic.")
        else:
            st.session_state.quiz_data = {
                "subject_id": selected_subject["id"],
                "subject_name": selected_subject["name"],
                "topic": clean_topic,
                "question_type": question_type,
                "difficulty": difficulty,
                "questions": quiz_data["questions"],
                "sources": quiz_data["sources"],
            }
            st.session_state.quiz_feedback = None
            st.success("Quiz generated. Answer the questions below.")

quiz_data = st.session_state.quiz_data

if not quiz_data:
    section_title("Answer Quiz", "\U0001f4dd")
    render_empty_state(
        "No quiz generated yet.",
        "Choose a topic and generate questions to start practicing.",
        "\u2754",
    )

if quiz_data:
    section_title("Answer Quiz", "\U0001f4dd")
    st.caption(
        f"{quiz_data['subject_name']} | {quiz_data['question_type']} | "
        f"{quiz_data['difficulty']} | Topic: {quiz_data['topic']}"
    )

    with st.form("quiz_answer_form"):
        user_answers = {}

        for index, question in enumerate(quiz_data["questions"]):
            st.markdown(f"**Q{index + 1}. {question['question']}**")

            options = question.get("options", [])
            if quiz_data["question_type"] == "MCQ" and options:
                user_answers[index] = st.radio(
                    "Choose one answer",
                    options,
                    key=f"quiz_answer_{index}",
                    label_visibility="collapsed",
                )
            else:
                height = 90 if quiz_data["question_type"] in ["Short", "Viva"] else 160
                user_answers[index] = st.text_area(
                    "Your answer",
                    key=f"quiz_answer_{index}",
                    height=height,
                )

            st.divider()

        submitted = st.form_submit_button("Submit Answers", use_container_width=True)

    if submitted:
        loading_slot = st.empty()
        with loading_slot:
            render_ai_loading("Checking answers and preparing feedback")
        try:
            checked = check_quiz_answers(
                questions=quiz_data["questions"],
                user_answers=user_answers,
            )
        finally:
            loading_slot.empty()

        if checked["error"]:
            st.error(checked["error"])
        else:
            results = checked["results"]
            score = sum(result["marks"] for result in results)
            total = len(results)
            result_id = save_quiz_result(
                subject_id=quiz_data["subject_id"],
                score=score,
                total_questions=total,
                topic=quiz_data["topic"],
                user_id=user_id,
            )

            if score < total:
                update_weak_topic(
                    subject_id=quiz_data["subject_id"],
                    topic=quiz_data["topic"],
                    weakness_score=total - score,
                    notes=f"Quiz result: {score}/{total}",
                    user_id=user_id,
                )

            st.session_state.quiz_feedback = {
                "results": results,
                "score": score,
                "total": total,
                "result_id": result_id,
            }

feedback = st.session_state.quiz_feedback

if feedback:
    section_title("Marks and Feedback", "\U0001f31f")
    st.success(
        f"Score: {feedback['score']} / {feedback['total']} | Quiz result saved."
    )

    for result in feedback["results"]:
        with st.container(border=True):
            st.markdown(f"**Question {result['question_number']}**")
            st.write(f"Marks: {result['marks']} / 1")
            st.write(f"Feedback: {result['feedback']}")
            st.write(f"Correct answer: {result['correct_answer']}")

if quiz_data and quiz_data["sources"]:
    with st.expander("Source chunks used to generate this quiz"):
        for index, source in enumerate(quiz_data["sources"], start=1):
            metadata = source["metadata"]
            st.markdown(f"**Source {index}: {metadata.get('file_name', 'Uploaded PDF')}**")
            st.write(source["text"])

section_title("Quiz History", "\U0001f4c8")
history_subject = st.selectbox(
    "Filter history by subject",
    ["All subjects"] + subject_names,
    key="quiz_history_subject_filter",
)
history_subject_id = None
if history_subject != "All subjects":
    history_subject_id = subject_options[history_subject]["id"]

quiz_history = get_quiz_results(subject_id=history_subject_id, user_id=user_id, limit=25)
if not quiz_history:
    render_empty_state(
        "No quiz attempts yet.",
        "Submit a quiz and your score history will appear here.",
        "\U0001f4c8",
    )
else:
    for attempt in quiz_history:
        total = int(attempt["total_questions"] or 0)
        score = int(attempt["score"] or 0)
        percent = int((score / total) * 100) if total else 0
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a:
                st.markdown(f"**{attempt['subject_name']}**")
                st.caption(f"Topic: {attempt['topic'] or 'General'} | {attempt['created_at']}")
            with col_b:
                st.metric("Score", f"{score}/{total}")
            with col_c:
                st.metric("Percent", f"{percent}%")
