import os

import requests

from modules.vector_store import query_subject_notes


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

ANSWER_STYLE_INSTRUCTIONS = {
    "Simple English": "Use short, clear sentences and explain the idea like a friendly tutor.",
    "Roman Urdu": "Answer in Roman Urdu. Keep technical terms simple and easy for Pakistani students.",
    "Exam Style": "Write a structured exam answer with definitions, key points, and a concise conclusion.",
    "Viva Style": "Answer like a spoken viva response: direct, confident, and easy to say aloud.",
}


def ask_ollama(prompt, model=OLLAMA_MODEL):
    """Send a prompt to the local Ollama server and return the response text."""
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def chat_with_notes(subject_id, question, model=OLLAMA_MODEL, answer_style="Simple English"):
    """Answer a student question using only the uploaded notes for a subject."""
    matches = query_subject_notes(subject_id, question)
    context = "\n\n".join(match["text"] for match in matches)
    style_instruction = ANSWER_STYLE_INSTRUCTIONS.get(
        answer_style,
        ANSWER_STYLE_INSTRUCTIONS["Simple English"],
    )

    if not context:
        return {
            "answer": "I could not find notes for this subject yet. Please upload a PDF first.",
            "sources": [],
        }

    prompt = f"""
You are StudyMate AI, a helpful offline study assistant.
Answer the student's question using only the notes below.
If the notes do not contain the answer, say that clearly.
Answer style: {answer_style}
Style instruction: {style_instruction}

NOTES:
{context}

QUESTION:
{question}

ANSWER:
"""

    try:
        answer = ask_ollama(prompt, model=model)
    except requests.exceptions.RequestException as exc:
        answer = (
            "I found relevant notes, but I could not connect to Ollama. "
            "Make sure Ollama is running with `ollama serve` and that your model is installed. "
            f"Technical detail: {exc}"
        )

    return {
        "answer": answer,
        "sources": matches,
    }
