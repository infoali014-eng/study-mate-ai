import os
import time
from pathlib import Path

import requests
from dotenv import dotenv_values, load_dotenv

from modules.vector_store import VectorStoreError, query_subject_notes


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
DEFAULT_AI_PROVIDER = os.getenv("AI_PROVIDER", "Gemini")
LEGACY_GEMINI_MODELS = {"gemini-1.5-flash", "gemini-1.5-pro"}
GEMINI_FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
]
TEMPORARY_GEMINI_STATUSES = {429, 500, 502, 503, 504}

MISSING_GEMINI_KEY_MESSAGE = (
    "Gemini API key is missing. Add it in .env, Streamlit secrets, "
    "environment variable, or enter it in AI Settings."
)

ANSWER_STYLE_INSTRUCTIONS = {
    "Simple English": "Use short, clear sentences and explain the idea like a friendly tutor.",
    "Roman Urdu": "Answer in Roman Urdu. Keep technical terms simple and easy for Pakistani students.",
    "Exam Style": "Write a structured exam answer with definitions, key points, and a concise conclusion.",
    "Viva Style": "Answer like a spoken viva response: direct, confident, and easy to say aloud.",
}

STUDY_ASSISTANT_SYSTEM_PROMPT = """
You are Ali Shair's AI Study Assistant.
You help a CS student prepare for exams using uploaded notes and general academic knowledge.
Give clear, detailed, concept-based, exam-focused answers.
If uploaded notes do not contain the answer, say that clearly and then answer from general knowledge.
Use simple English unless the selected style asks for Roman Urdu.
For academic questions, prefer this structure when useful:
- Simple explanation
- Key points
- Example
- Exam-style answer
- Quick revision tip
"""


class AIProviderError(Exception):
    """Raised when the selected AI provider cannot return a response."""


def normalize_gemini_model(model):
    """Use a currently available default when an older Gemini model is selected."""
    selected_model = (model or GEMINI_MODEL).strip()
    if selected_model in LEGACY_GEMINI_MODELS:
        return GEMINI_MODEL
    return selected_model


def get_gemini_model_candidates(preferred_model=None):
    """Return the preferred Gemini model followed by safe fallback models."""
    first_model = normalize_gemini_model(preferred_model)
    models = [first_model]

    for fallback_model in GEMINI_FALLBACK_MODELS:
        normalized = normalize_gemini_model(fallback_model)
        if normalized not in models:
            models.append(normalized)

    return models


def _get_streamlit_secret(name):
    """Read a Streamlit secret when Streamlit is available and configured."""
    try:
        import streamlit as st

        return st.secrets.get(name, "")
    except Exception:
        return ""


def get_session_ai_settings():
    """Read temporary AI settings saved in Streamlit session state."""
    try:
        import streamlit as st

        return {
            "provider": st.session_state.get("ai_provider", DEFAULT_AI_PROVIDER),
            "gemini_api_key": st.session_state.get("gemini_api_key", ""),
            "gemini_model": normalize_gemini_model(
                st.session_state.get("gemini_model", GEMINI_MODEL)
            ),
            "ollama_model": st.session_state.get("ollama_model", OLLAMA_MODEL),
            "groq_model": st.session_state.get("groq_model", GROQ_MODEL),
        }
    except Exception:
        return {
            "provider": DEFAULT_AI_PROVIDER,
            "gemini_api_key": "",
            "gemini_model": GEMINI_MODEL,
            "ollama_model": OLLAMA_MODEL,
            "groq_model": GROQ_MODEL,
        }


def get_gemini_api_key():
    """
    Return the Gemini key without printing or persisting it.

    Priority:
    1. Temporary Streamlit session input
    2. GEMINI_API_KEY environment variable or local .env
    3. Streamlit secrets
    """
    settings = get_session_ai_settings()
    return (
        settings.get("gemini_api_key")
        or os.getenv("GEMINI_API_KEY", "")
        or _get_streamlit_secret("GEMINI_API_KEY")
    )


def get_groq_api_key():
    """Return the Groq key without printing or persisting it."""
    try:
        import streamlit as st

        session_key = st.session_state.get("groq_api_key", "")
    except Exception:
        session_key = ""

    return (
        session_key
        or os.getenv("GROQ_API_KEY", "")
        or _get_streamlit_secret("GROQ_API_KEY")
    )


def get_gemini_key_source():
    """Return where the active Gemini key is coming from, without exposing it."""
    settings = get_session_ai_settings()
    if settings.get("gemini_api_key"):
        return "AI Settings session password field"

    env_file_values = dotenv_values(PROJECT_ROOT / ".env")
    if env_file_values.get("GEMINI_API_KEY"):
        return "local .env file"

    if os.getenv("GEMINI_API_KEY", ""):
        return "environment variable"

    if _get_streamlit_secret("GEMINI_API_KEY"):
        return "Streamlit secrets"

    return "missing"


def get_selected_provider():
    """Return the currently selected AI provider."""
    return get_session_ai_settings().get("provider", DEFAULT_AI_PROVIDER)


def ask_gemini(prompt, model=None, api_key=None):
    """Send a prompt to Gemini using an API key from safe local configuration."""
    key = api_key or get_gemini_api_key()
    if not key:
        raise AIProviderError(MISSING_GEMINI_KEY_MESSAGE)

    preferred_model = normalize_gemini_model(
        model or get_session_ai_settings().get("gemini_model") or GEMINI_MODEL
    )
    model_errors = []
    quota_error_seen = False
    candidates = get_gemini_model_candidates(preferred_model)

    for attempt_number, selected_model in enumerate(candidates, start=1):
        try:
            return _ask_single_gemini_model(
                prompt=prompt,
                api_key=key,
                selected_model=selected_model,
            )
        except AIProviderError as exc:
            status_code = getattr(exc, "status_code", None)
            quota_error_seen = quota_error_seen or getattr(exc, "quota_error", False)
            model_errors.append(str(exc))

            if status_code not in TEMPORARY_GEMINI_STATUSES:
                raise

            if attempt_number < len(candidates):
                time.sleep(0.8)
                continue

    if quota_error_seen:
        raise AIProviderError(
            "Gemini quota or rate limit is blocking this API key right now. "
            "The key is loaded correctly, but Google is not allowing more requests "
            "for the available free-tier models. Wait and retry, use another Gemini key, "
            "check your Google AI Studio quota/billing, or switch to Ollama/Demo Mode."
        )

    raise AIProviderError(
        "Gemini is temporarily busy across the available fallback models. "
        "Please try again in a few minutes. Last error: "
        f"{model_errors[-1] if model_errors else 'No details returned.'}"
    )


def _ask_single_gemini_model(prompt, api_key, selected_model):
    """Call one Gemini model and raise a safe provider error if it fails."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{selected_model}:generateContent"
    )
    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=120,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        detail = _safe_gemini_error_message(response if "response" in locals() else None)
        if status_code in {401, 403}:
            message = (
                "Gemini rejected the API key. Please check that your Gemini API key is valid "
                "and has access to the Generative Language API."
            )
        elif status_code == 404:
            message = (
                f"Gemini model '{selected_model}' is not available for this API key. "
                f"Use '{GEMINI_MODEL}' in AI Settings or GEMINI_MODEL in your .env file."
            )
        elif status_code == 429:
            message = (
                f"Gemini quota or rate limit was reached for model '{selected_model}'. "
                "Your key is loaded correctly, but Google is not allowing this request right now."
            )
        elif status_code in TEMPORARY_GEMINI_STATUSES:
            message = (
                f"Gemini model '{selected_model}' is temporarily busy "
                f"(status {status_code})."
            )
        elif status_code:
            message = f"Gemini request failed with status {status_code}."
        else:
            message = "Could not connect to Gemini. Please check your internet connection."

        if detail:
            message = f"{message} Gemini said: {_brief_gemini_detail(detail)}"
        provider_error = AIProviderError(message)
        provider_error.status_code = status_code
        provider_error.quota_error = status_code == 429 or _looks_like_quota_error(detail)
        raise provider_error from exc

    data = response.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError("Gemini returned an unexpected response format.") from exc


def _safe_gemini_error_message(response):
    """Return Gemini's error text without exposing request URLs or API keys."""
    if response is None:
        return ""
    try:
        data = response.json()
    except ValueError:
        return ""

    error = data.get("error", {}) if isinstance(data, dict) else {}
    return str(error.get("message", "")).strip()


def _brief_gemini_detail(detail):
    """Shorten long Gemini quota/error text for the UI."""
    if not detail:
        return ""

    first_line = detail.strip().splitlines()[0].strip()
    if _looks_like_quota_error(detail):
        return (
            f"{first_line} Check your quota at https://ai.dev/rate-limit "
            "or switch to Ollama/Demo Mode."
        )
    return first_line


def _looks_like_quota_error(detail):
    """Detect quota/rate-limit messages without depending on exact wording."""
    lowered = (detail or "").lower()
    return "quota" in lowered or "rate limit" in lowered or "rate-limit" in lowered


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


def ask_groq(prompt, model=None):
    """Send a prompt to Groq's OpenAI-compatible chat completions API."""
    key = get_groq_api_key()
    if not key:
        raise AIProviderError(
            "Groq API key is missing. Add it in .env, Streamlit secrets, "
            "environment variable, or enter it in AI Settings."
        )

    selected_model = model or get_session_ai_settings().get("groq_model") or GROQ_MODEL
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": selected_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=120,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        raise AIProviderError(
            f"Groq request failed with status {status_code or 'unknown'}. "
            "Check your Groq API key, model name, or network connection."
        ) from exc

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError("Groq returned an unexpected response format.") from exc


def ask_demo(prompt):
    """Return a simple demo response when no AI provider is available."""
    return (
        "Demo Mode response: AI provider is not connected yet. "
        "Add a Gemini API key in AI Settings or switch to Ollama local mode."
    )


def ask_ai(prompt, provider=None, model=None):
    """Ask the selected AI provider. Gemini is the default provider."""
    selected_provider = provider or get_selected_provider()

    if selected_provider == "Gemini":
        return ask_gemini(prompt, model=model)

    if selected_provider == "Ollama":
        selected_model = model or get_session_ai_settings().get("ollama_model") or OLLAMA_MODEL
        return ask_ollama(prompt, model=selected_model)

    if selected_provider == "Groq":
        selected_model = model or get_session_ai_settings().get("groq_model") or GROQ_MODEL
        return ask_groq(prompt, model=selected_model)

    return ask_demo(prompt)


def get_missing_key_message():
    """Expose the missing-key copy for pages that want to show it directly."""
    return MISSING_GEMINI_KEY_MESSAGE


def chat_with_notes(
    subject_id,
    question,
    model=None,
    answer_style="Simple English",
    provider=None,
):
    """Answer a student question using only the uploaded notes for a subject."""
    try:
        matches = query_subject_notes(subject_id, question)
    except VectorStoreError as exc:
        return {
            "answer": str(exc),
            "sources": [],
        }

    context = "\n\n".join(match["text"] for match in matches)
    style_instruction = ANSWER_STYLE_INSTRUCTIONS.get(
        answer_style,
        ANSWER_STYLE_INSTRUCTIONS["Simple English"],
    )

    if not context:
        return {
            "answer": "I could not find notes for this subject yet. Please upload a document first.",
            "sources": [],
        }

    prompt = f"""
You are StudyMate AI, a helpful study assistant.
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
        answer = ask_ai(prompt, provider=provider, model=model)
    except Exception as exc:
        answer = str(exc)

    return {
        "answer": answer,
        "sources": matches,
    }


def build_study_chat_prompt(
    question,
    answer_style,
    notes_context="",
    context_label="General Chat",
    general_chat=False,
):
    """Build a detailed study-chat prompt for notes or general AI chat."""
    style_instruction = ANSWER_STYLE_INSTRUCTIONS.get(
        answer_style,
        ANSWER_STYLE_INSTRUCTIONS["Simple English"],
    )

    if general_chat:
        context_block = """
GENERAL CHAT MODE:
No uploaded notes were selected. Answer normally using general academic knowledge.
"""
    elif notes_context:
        context_block = f"""
UPLOADED NOTES CONTEXT ({context_label}):
{notes_context}

Use the uploaded notes first. If the notes are incomplete, add helpful general academic knowledge.
"""
    else:
        context_block = f"""
NO DIRECT NOTE CONTEXT FOUND ({context_label}).
Clearly say: "I could not find this directly in your uploaded notes, so I'm answering from general knowledge."
Then answer helpfully using general academic knowledge.
"""

    return f"""
{STUDY_ASSISTANT_SYSTEM_PROMPT}

Answer style: {answer_style}
Style instruction: {style_instruction}

{context_block}

Student question:
{question}

Answer with readable Markdown. Be detailed, organized, and useful for exam preparation.
"""


def generate_study_chat_response(
    question,
    answer_style="Simple English",
    chat_mode="General Chat",
    subject_id=None,
    document_ids=None,
    context_label="General Chat",
    limit=5,
):
    """Generate a chatbot answer with optional RAG context and sources."""
    sources = []
    warning = ""

    should_retrieve = chat_mode != "General Chat" and subject_id is not None
    if should_retrieve:
        try:
            sources = query_subject_notes(
                subject_id=subject_id,
                question=question,
                limit=limit,
                document_ids=document_ids,
            )
        except VectorStoreError as exc:
            warning = str(exc)

    notes_context = "\n\n".join(
        f"Source {index}: {source['text']}"
        for index, source in enumerate(sources, start=1)
    )

    if should_retrieve and not sources and not warning:
        warning = (
            "I could not find this directly in your uploaded notes, "
            "so I'm answering from general knowledge."
        )

    prompt = build_study_chat_prompt(
        question=question,
        answer_style=answer_style,
        notes_context=notes_context,
        context_label=context_label,
        general_chat=chat_mode == "General Chat",
    )

    try:
        answer = ask_ai(prompt)
    except Exception as exc:
        answer = str(exc)

    return {
        "answer": answer,
        "sources": sources,
        "warning": warning,
        "source_count": len(sources),
    }
