import json
import re

from modules import ai_engine
from modules.vector_store import VectorStoreError, query_subject_notes


QUESTION_TYPE_GUIDE = {
    "MCQ": "Create multiple choice questions with four options: A, B, C, and D.",
    "Short": "Create short answer questions that can be answered in 2 to 4 lines.",
    "Long": "Create long answer questions that need explanation, examples, or steps.",
    "Viva": "Create oral viva-style questions with direct spoken answers.",
}


def _ask_selected_ai(prompt, model=None):
    """Use the selected AI provider, with a fallback for older loaded modules."""
    if hasattr(ai_engine, "ask_ai"):
        return ai_engine.ask_ai(prompt, model=model)
    return ai_engine.ask_ollama(prompt, model=model)


def _extract_json(text):
    """Extract JSON from an Ollama response, even if it includes extra text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _fallback_questions(raw_text, question_count):
    """Build simple question objects if the model does not return valid JSON."""
    lines = [line.strip(" -0123456789.").strip() for line in raw_text.splitlines()]
    questions = [line for line in lines if line.endswith("?")]
    if not questions:
        questions = [raw_text.strip()]

    return [
        {
            "question": question,
            "options": [],
            "expected_answer": "",
        }
        for question in questions[:question_count]
    ]


def generate_quiz(
    subject_id,
    topic,
    question_type="MCQ",
    difficulty="Easy",
    question_count=5,
    model=None,
    user_id=None,
):
    """Generate structured quiz questions from uploaded notes."""
    search_text = f"{topic} {question_type} {difficulty}"
    try:
        matches = query_subject_notes(subject_id, search_text, limit=8, user_id=user_id)
    except VectorStoreError as exc:
        return {
            "questions": [],
            "sources": [],
            "error": str(exc),
        }

    context = "\n\n".join(match["text"] for match in matches)

    if not context:
        return {
            "questions": [],
            "sources": [],
            "error": "Upload notes for this subject before generating a quiz.",
        }

    prompt = f"""
{ai_engine.build_study_assistant_system_prompt()}

Generate a quiz using only the notes below.

Return only valid JSON. Do not add markdown.
The JSON must be an array of objects.
Each object must use these keys:
- "question": string
- "options": array of strings, empty array for non-MCQ questions
- "expected_answer": string

Question type: {question_type}
Question type instruction: {QUESTION_TYPE_GUIDE.get(question_type, QUESTION_TYPE_GUIDE["MCQ"])}
Difficulty: {difficulty}
Number of questions: {question_count}
Topic: {topic}

NOTES:
{context}
"""

    try:
        raw_response = _ask_selected_ai(prompt, model=model)
    except Exception as exc:
        return {
            "questions": [],
            "sources": matches,
            "error": (
                "Could not generate quiz with the selected AI provider. "
                f"Reason: {ai_engine.safe_ai_error_message(exc)}"
            ),
        }

    questions = _extract_json(raw_response)
    if not isinstance(questions, list):
        questions = _fallback_questions(raw_response, question_count)

    clean_questions = []
    for question in questions[:question_count]:
        if not isinstance(question, dict):
            continue

        clean_questions.append(
            {
                "question": str(question.get("question", "")).strip(),
                "options": question.get("options", []) or [],
                "expected_answer": str(question.get("expected_answer", "")).strip(),
            }
        )

    return {
        "questions": [item for item in clean_questions if item["question"]],
        "sources": matches,
        "error": "",
    }


def check_quiz_answers(questions, user_answers, model=None):
    """Ask Ollama to mark answers and return feedback for each question."""
    quiz_payload = []
    for index, question in enumerate(questions):
        quiz_payload.append(
            {
                "question_number": index + 1,
                "question": question["question"],
                "options": question.get("options", []),
                "expected_answer": question.get("expected_answer", ""),
                "student_answer": user_answers.get(index, ""),
            }
        )

    prompt = f"""
{ai_engine.build_study_assistant_system_prompt()}

You are also an honest but supportive teacher.
Check the student's answers.

Return only valid JSON. Do not add markdown.
The JSON must be an array of objects with these keys:
- "question_number": integer
- "marks": 0 or 1
- "feedback": short string
- "correct_answer": string

Give 1 mark if the answer is correct or mostly correct.
Give 0 marks if it is wrong, empty, or too vague.

QUIZ:
{json.dumps(quiz_payload, indent=2)}
"""

    try:
        raw_response = _ask_selected_ai(prompt, model=model)
    except Exception as exc:
        return {
            "results": [],
            "error": (
                "Could not check answers with the selected AI provider. "
                f"Reason: {ai_engine.safe_ai_error_message(exc)}"
            ),
        }

    results = _extract_json(raw_response)
    if not isinstance(results, list):
        results = []

    clean_results = []
    for index, question in enumerate(questions):
        model_result = {}
        if index < len(results) and isinstance(results[index], dict):
            model_result = results[index]

        marks = model_result.get("marks", 0)
        try:
            marks = int(marks)
        except (TypeError, ValueError):
            marks = 0

        clean_results.append(
            {
                "question_number": index + 1,
                "marks": max(0, min(1, marks)),
                "feedback": str(model_result.get("feedback", "No feedback returned.")).strip(),
                "correct_answer": str(
                    model_result.get(
                        "correct_answer",
                        question.get("expected_answer", "Not provided."),
                    )
                ).strip(),
            }
        )

    return {
        "results": clean_results,
        "error": "",
    }
