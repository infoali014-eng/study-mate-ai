import os

import streamlit as st

from modules.ai_engine import OLLAMA_MODEL
from modules.database import (
    get_subjects,
    init_db,
    save_quiz_result,
    update_weak_topic,
)
from modules.quiz_generator import check_quiz_answers, generate_quiz


QUESTION_TYPES = ["MCQ", "Short", "Long", "Viva"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]


st.set_page_config(page_title="Quiz Mode - StudyMate AI", layout="wide")
init_db()

st.sidebar.title("StudyMate AI")
st.sidebar.page_link("pages/1_Dashboard.py", label="Dashboard")
st.sidebar.page_link("pages/2_Upload_Notes.py", label="Upload Notes")
st.sidebar.page_link("pages/3_Chat_With_Notes.py", label="Chat With Notes")
st.sidebar.page_link("pages/4_Quiz_Mode.py", label="Quiz Mode")
st.sidebar.page_link("pages/5_Flashcards.py", label="Flashcards")
st.sidebar.page_link("pages/6_Revision_Planner.py", label="Revision Planner")

st.title("Quiz Mode")
st.caption("Generate questions from uploaded notes, answer them, and get AI feedback.")

subjects = get_subjects()
if not subjects:
    st.warning("Create a subject and upload notes first.")
    st.stop()

subject_options = {subject["name"]: subject for subject in subjects}

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        selected_name = st.selectbox("Choose subject", list(subject_options.keys()))
        question_type = st.selectbox("Question type", QUESTION_TYPES)
        difficulty = st.selectbox("Difficulty", DIFFICULTIES)
    with col2:
        topic = st.text_input("Topic", placeholder="Example: cell structure")
        question_count = st.number_input(
            "Number of questions",
            min_value=1,
            max_value=10,
            value=5,
            step=1,
        )
        model = st.text_input("Ollama model", value=os.getenv("OLLAMA_MODEL", OLLAMA_MODEL))

    generate_button = st.button("Generate Quiz", type="primary", use_container_width=True)

selected_subject = subject_options[selected_name]

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "quiz_feedback" not in st.session_state:
    st.session_state.quiz_feedback = None

if generate_button:
    if not topic.strip():
        st.warning("Please enter a topic.")
    else:
        with st.spinner("Searching uploaded notes and generating quiz with Ollama..."):
            quiz_data = generate_quiz(
                subject_id=selected_subject["id"],
                topic=topic,
                question_type=question_type,
                difficulty=difficulty,
                question_count=int(question_count),
                model=model,
            )

        if quiz_data["error"]:
            st.error(quiz_data["error"])
        elif not quiz_data["questions"]:
            st.error("Ollama did not return usable questions. Try again with a clearer topic.")
        else:
            st.session_state.quiz_data = {
                "subject_id": selected_subject["id"],
                "subject_name": selected_subject["name"],
                "topic": topic,
                "question_type": question_type,
                "difficulty": difficulty,
                "model": model,
                "questions": quiz_data["questions"],
                "sources": quiz_data["sources"],
            }
            st.session_state.quiz_feedback = None
            st.success("Quiz generated. Answer the questions below.")

quiz_data = st.session_state.quiz_data

if quiz_data:
    st.subheader("Answer Quiz")
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
        with st.spinner("Checking answers with Ollama..."):
            checked = check_quiz_answers(
                questions=quiz_data["questions"],
                user_answers=user_answers,
                model=quiz_data["model"],
            )

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
            )

            if score < total:
                update_weak_topic(
                    subject_id=quiz_data["subject_id"],
                    topic=quiz_data["topic"],
                    weakness_score=total - score,
                    notes=f"Quiz result: {score}/{total}",
                )

            st.session_state.quiz_feedback = {
                "results": results,
                "score": score,
                "total": total,
                "result_id": result_id,
            }

feedback = st.session_state.quiz_feedback

if feedback:
    st.subheader("Marks and Feedback")
    st.success(
        f"Score: {feedback['score']} / {feedback['total']} "
        f"| Saved quiz result id: {feedback['result_id']}"
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
