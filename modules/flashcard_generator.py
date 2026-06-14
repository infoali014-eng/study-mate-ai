import json
import re

from modules import ai_engine
from modules.vector_store import VectorStoreError, query_subject_notes


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


def generate_flashcards(subject_id, topic, card_count=8, model=None, user_id=None):
    """Generate structured flashcards from uploaded notes."""
    try:
        matches = query_subject_notes(subject_id, topic, limit=8, user_id=user_id)
    except VectorStoreError as exc:
        return {
            "flashcards": [],
            "sources": [],
            "error": str(exc),
        }

    context = "\n\n".join(match["text"] for match in matches)

    if not context:
        return {
            "flashcards": [],
            "sources": [],
            "error": "Upload notes for this subject before generating flashcards.",
        }

    prompt = f"""
{ai_engine.build_study_assistant_system_prompt()}

Create flashcards using only the notes below.

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
        raw_response = _ask_selected_ai(prompt, model=model)
    except Exception as exc:
        return {
            "flashcards": [],
            "sources": matches,
            "error": (
                "Could not generate flashcards with the selected AI provider. "
                f"Reason: {ai_engine.safe_ai_error_message(exc)}"
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
