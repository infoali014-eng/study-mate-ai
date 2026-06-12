import json
import re

import requests

from modules.ai_engine import OLLAMA_MODEL, ask_ollama
from modules.vector_store import query_subject_notes


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


def _fallback_flashcards(raw_text, card_count):
    """Parse simple Q/A text when the model does not return valid JSON."""
    cards = []
    current_question = ""

    for line in raw_text.splitlines():
        clean_line = line.strip()

        if clean_line.lower().startswith("q:"):
            current_question = clean_line[2:].strip()
        elif clean_line.lower().startswith("a:") and current_question:
            cards.append(
                {
                    "question": current_question,
                    "answer": clean_line[2:].strip(),
                }
            )
            current_question = ""

    return cards[:card_count]


def generate_flashcards(subject_id, topic, card_count=8, model=OLLAMA_MODEL):
    """Generate structured flashcards from uploaded notes."""
    matches = query_subject_notes(subject_id, topic, limit=8)
    context = "\n\n".join(match["text"] for match in matches)

    if not context:
        return {
            "flashcards": [],
            "sources": [],
            "error": "Upload notes for this subject before generating flashcards.",
        }

    prompt = f"""
You are StudyMate AI. Create flashcards using only the notes below.

Return only valid JSON. Do not add markdown.
The JSON must be an array of objects.
Each object must use these keys:
- "question": string
- "answer": string

Number of flashcards: {card_count}
Topic: {topic}

NOTES:
{context}
"""

    try:
        raw_response = ask_ollama(prompt, model=model)
    except requests.exceptions.RequestException as exc:
        return {
            "flashcards": [],
            "sources": matches,
            "error": (
                "Could not connect to Ollama. Make sure Ollama is running with "
                f"`ollama serve` and your model is installed. Technical detail: {exc}"
            ),
        }

    flashcards = _extract_json(raw_response)
    if not isinstance(flashcards, list):
        flashcards = _fallback_flashcards(raw_response, card_count)

    clean_cards = []
    for card in flashcards[:card_count]:
        if not isinstance(card, dict):
            continue

        question = str(card.get("question", "")).strip()
        answer = str(card.get("answer", "")).strip()

        if question and answer:
            clean_cards.append(
                {
                    "question": question,
                    "answer": answer,
                }
            )

    return {
        "flashcards": clean_cards,
        "sources": matches,
        "error": "",
    }
