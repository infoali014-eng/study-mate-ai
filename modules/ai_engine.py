import os
import re
import time
import base64
import mimetypes
from pathlib import Path

import requests
from dotenv import dotenv_values, load_dotenv

from modules.database import get_user_api_key
from modules.vector_store import VectorStoreError, query_subject_notes


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
DEFAULT_AI_PROVIDER = os.getenv("AI_PROVIDER", "Gemini")
REQUIRE_USER_API_KEYS = os.getenv("REQUIRE_USER_API_KEYS", "true").lower() != "false"
OPENAI_MODEL_OPTIONS = [
    model.strip()
    for model in os.getenv("OPENAI_MODEL_OPTIONS", "gpt-5.4-mini,gpt-5.4,gpt-5.5").split(",")
    if model.strip()
]
LEGACY_GEMINI_MODELS = {"gemini-1.5-flash", "gemini-1.5-pro"}
GEMINI_FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
]
TEMPORARY_GEMINI_STATUSES = {429, 500, 502, 503, 504}
AI_REQUEST_LIMIT = 30
AI_REQUEST_WINDOW_SECONDS = 300

MISSING_GEMINI_KEY_MESSAGE = (
    "Gemini API key is missing. Add it in AI Settings, save it securely for your account, "
    "or enter a temporary session key."
)
MISSING_OPENAI_KEY_MESSAGE = "OpenAI API key is missing. Add it in AI Settings."

ANSWER_STYLE_INSTRUCTIONS = {
    "Simple English": "Use short, clear sentences and explain the idea like a friendly tutor.",
    "Roman Urdu": "Answer in Roman Urdu. Keep technical terms simple and easy for Pakistani students.",
    "Exam Style": "Write a structured exam answer with definitions, key points, and a concise conclusion.",
    "Viva Style": "Answer like a spoken viva response: direct, confident, and easy to say aloud.",
}

RELEVANCE_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "why",
    "with",
}

SENSITIVE_MEMORY_WORDS = {
    "api key",
    "apikey",
    "password",
    "secret",
    "token",
    "client secret",
    "cookie secret",
    "private key",
}

class AIProviderError(Exception):
    """Raised when the selected AI provider cannot return a response."""


def safe_ai_error_message(exc):
    """Return a user-safe AI error without leaking URLs, keys, or stack details."""
    if isinstance(exc, AIProviderError):
        return str(exc)
    return "The selected AI provider could not complete the request. Please try again or switch provider."


def _check_ai_rate_limit():
    """Limit rapid AI requests per Streamlit browser session."""
    try:
        import streamlit as st
    except Exception:
        return

    now = time.time()
    request_times = st.session_state.get("ai_request_times", [])
    request_times = [
        request_time
        for request_time in request_times
        if now - request_time < AI_REQUEST_WINDOW_SECONDS
    ]
    if len(request_times) >= AI_REQUEST_LIMIT:
        st.session_state.ai_request_times = request_times
        raise AIProviderError("You are sending requests too quickly. Please wait a moment.")

    request_times.append(now)
    st.session_state.ai_request_times = request_times


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


def normalize_provider(provider):
    """Map friendly UI labels to stable provider names used by the app."""
    clean = (provider or DEFAULT_AI_PROVIDER or "Gemini").strip().lower()
    aliases = {
        "gemini": "Gemini",
        "gemini api": "Gemini",
        "google gemini": "Gemini",
        "openai": "OpenAI",
        "openai api": "OpenAI",
        "chatgpt": "OpenAI",
        "chatgpt/openai": "OpenAI",
        "groq": "Groq",
        "groq api": "Groq",
        "ollama": "Ollama",
        "ollama local": "Ollama",
        "demo": "Demo Mode",
        "demo mode": "Demo Mode",
    }
    return aliases.get(clean, provider or DEFAULT_AI_PROVIDER)


def provider_display_name(provider=None):
    """Return a user-facing provider label."""
    canonical = normalize_provider(provider or get_selected_provider())
    labels = {
        "Gemini": "Gemini API",
        "OpenAI": "OpenAI API",
        "Groq": "Groq API",
        "Ollama": "Ollama Local",
        "Demo Mode": "Demo Mode",
    }
    return labels.get(canonical, str(provider or canonical))


def is_gemini_provider(provider=None):
    """Return True when the selected provider is Gemini."""
    return normalize_provider(provider or get_selected_provider()) == "Gemini"


def is_openai_provider(provider=None):
    """Return True when the selected provider is OpenAI."""
    return normalize_provider(provider or get_selected_provider()) == "OpenAI"


def provider_supports_vision(provider=None):
    """Return whether the provider path can receive image attachments directly."""
    return normalize_provider(provider or get_selected_provider()) in {"Gemini", "OpenAI"}


def _get_streamlit_secret(name):
    """Read a Streamlit secret when Streamlit is available and configured."""
    try:
        import streamlit as st

        return st.secrets.get(name, "")
    except Exception:
        return ""


def _get_current_user_id():
    """Return the current Streamlit user id when running inside the app."""
    try:
        import streamlit as st

        return st.session_state.get("user_id")
    except Exception:
        return None


def get_current_user_display_name():
    """Return the current user's display name for AI prompts."""
    try:
        from modules.auth import get_current_user_display_name as auth_display_name

        return auth_display_name()
    except Exception:
        return "Student"


def build_study_assistant_system_prompt(user_name=None):
    """Build the shared study assistant system prompt with current user context."""
    clean_name = (user_name or get_current_user_display_name() or "Student").strip()
    return f"""
You are {clean_name}'s AI Study Assistant.
You help {clean_name} prepare for exams using uploaded notes and general academic knowledge.
Give clear, detailed, concept-based, exam-focused answers like a strong personal tutor.
If uploaded notes do not contain the answer, say that clearly and then answer from general knowledge.
Use simple English unless the selected style asks for Roman Urdu.
Make answers visually useful whenever it genuinely helps understanding:
- Use Markdown tables for comparisons, steps, formulas, pros/cons, or examples.
- Use short ASCII diagrams for simple relationships.
- Use Mermaid flowcharts for processes, lifecycles, algorithms, systems, and cause-effect chains.
- Use bullet summaries, examples, common mistakes, and quick-check questions.
- Do not force diagrams for tiny/simple questions.

When using Mermaid, output valid fenced Mermaid code like:
```mermaid
flowchart TD
    A[Start] --> B[Understand the concept]
    B --> C[Apply with example]
    C --> D[Exam-ready answer]
```

For academic questions, prefer this structure when useful:
- Simple explanation
- Key points
- Example
- Visual / Flowchart
- Exam-style answer
- Common mistakes
- Quick revision tip
"""


def memory_enabled():
    """Return whether user memory is enabled for this browser session."""
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is None:
            return True
        return bool(st.session_state.get("memory_enabled", True))
    except Exception:
        return True


def _safe_memory_text(text):
    """Reject secrets and overly long/private-looking memory candidates."""
    clean = str(text or "").strip()
    lowered = clean.lower()
    if not clean or len(clean) > 300:
        return ""
    if any(word in lowered for word in SENSITIVE_MEMORY_WORDS):
        return ""
    return clean


def _save_memory_candidate(user_id, key, value, category):
    """Save one memory candidate if it is safe and useful."""
    value = _safe_memory_text(value)
    if not user_id or not value:
        return None
    try:
        from modules.database import save_user_memory

        save_user_memory(user_id, key, value, category)
        return {"key": key, "value": value, "category": category}
    except Exception:
        return None


def extract_user_memories_from_message(user_id, message):
    """
    Extract a small set of useful study memories from a student message.

    This is intentionally rule-based and conservative. It avoids secrets,
    passwords, API keys, and raw note content.
    """
    if not memory_enabled() or not user_id:
        return []

    text = str(message or "").strip()
    lowered = text.lower()
    if not text or any(word in lowered for word in SENSITIVE_MEMORY_WORDS):
        return []

    saved = []

    name_match = re.search(
        r"\b(?:my name is|call me|i am|i'm)\s+([A-Za-z][A-Za-z .'-]{1,40}?)(?:[,.]| and | but |$)",
        text,
        flags=re.IGNORECASE,
    )
    if name_match and "weak" not in name_match.group(1).lower():
        candidate = name_match.group(1).strip()
        if len(candidate.split()) <= 4:
            saved_item = _save_memory_candidate(user_id, "preferred_name", candidate, "profile")
            if saved_item:
                saved.append(saved_item)

    language_patterns = [
        (r"\b(?:prefer|use|explain (?:me )?in|answer in)\s+(roman urdu)\b", "Roman Urdu"),
        (r"\b(?:prefer|use|explain (?:me )?in|answer in)\s+(mixed english\s*\+?\s*roman urdu)\b", "Mixed English + Roman Urdu"),
        (r"\b(?:prefer|use|explain (?:me )?in|answer in)\s+(simple english)\b", "Simple English"),
    ]
    for pattern, value in language_patterns:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            saved_item = _save_memory_candidate(user_id, "language_preference", value, "language_preference")
            if saved_item:
                saved.append(saved_item)
            break

    if re.search(r"\b(?:prefer|give|explain).{0,30}\bshort\b", lowered):
        saved_item = _save_memory_candidate(user_id, "answer_style", "short exam-style answers", "study_preference")
        if saved_item:
            saved.append(saved_item)
    elif re.search(r"\b(?:prefer|give|answer).{0,30}\b(?:exam style|exam-style)\b", lowered):
        saved_item = _save_memory_candidate(user_id, "answer_style", "exam-style answers", "study_preference")
        if saved_item:
            saved.append(saved_item)

    weak_match = re.search(
        r"\b(?:i am weak in|i'm weak in|weak in|i do not understand|i don't understand)\s+([A-Za-z0-9 +#_.-]{2,60})",
        text,
        flags=re.IGNORECASE,
    )
    if weak_match:
        topic = weak_match.group(1).strip(" .,!?:;")
        key_topic = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")[:50]
        if key_topic:
            saved_item = _save_memory_candidate(user_id, f"weak_topic_{key_topic}", topic, "weak_topic")
            if saved_item:
                saved.append(saved_item)

    exam_match = re.search(
        r"\b(?:my exam is|exam is|i have exam|i have an exam)\s+([A-Za-z0-9 ,./-]{2,80})",
        text,
        flags=re.IGNORECASE,
    )
    if exam_match:
        saved_item = _save_memory_candidate(user_id, "exam_info", exam_match.group(1).strip(" .,!?:;"), "exam_info")
        if saved_item:
            saved.append(saved_item)

    subject_match = re.search(
        r"\b(?:i am preparing|i'm preparing|preparing for|studying)\s+([A-Za-z0-9 +#_.-]{2,60})",
        text,
        flags=re.IGNORECASE,
    )
    if subject_match:
        subject = subject_match.group(1).strip(" .,!?:;")
        saved_item = _save_memory_candidate(user_id, "current_subject_focus", subject, "subject_preference")
        if saved_item:
            saved.append(saved_item)

    return saved


def get_user_memory_profile(user_id):
    """Return active memories as safe prompt lines."""
    if not memory_enabled() or not user_id:
        return []
    try:
        from modules.database import get_user_memories

        memories = get_user_memories(user_id, active_only=True)
    except Exception:
        return []

    labels = {
        "preferred_name": "Preferred name",
        "language_preference": "Preferred language",
        "answer_style": "Preferred answer style",
        "exam_info": "Exam info",
        "current_subject_focus": "Current subject focus",
    }
    lines = []
    for memory in memories[:12]:
        key = memory["memory_key"]
        value = _safe_memory_text(memory["memory_value"])
        if not value:
            continue
        label = labels.get(key)
        if not label and str(memory["category"]) == "weak_topic":
            label = "Weak topic"
        elif not label:
            label = str(memory["category"]).replace("_", " ").title()
        lines.append(f"- {label}: {value}")
    return lines


def format_user_memory_profile(user_id):
    """Return a prompt-ready memory profile."""
    lines = get_user_memory_profile(user_id)
    if not lines:
        return "No saved user memories."
    return "\n".join(lines)


def get_memory_display_name(user_id, fallback_name=None):
    """Prefer a saved preferred_name memory, otherwise use the session name."""
    if not memory_enabled() or not user_id:
        return fallback_name or get_current_user_display_name()
    try:
        from modules.database import get_user_memories

        for memory in get_user_memories(user_id, active_only=True):
            if memory["memory_key"] == "preferred_name":
                return _safe_memory_text(memory["memory_value"]) or fallback_name or "Student"
    except Exception:
        pass
    return fallback_name or get_current_user_display_name()


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
            "openai_api_key": st.session_state.get("openai_api_key", ""),
            "openai_model": st.session_state.get("openai_model", OPENAI_MODEL),
            "ollama_model": st.session_state.get("ollama_model", OLLAMA_MODEL),
            "groq_model": st.session_state.get("groq_model", GROQ_MODEL),
        }
    except Exception:
        return {
            "provider": DEFAULT_AI_PROVIDER,
            "gemini_api_key": "",
            "gemini_model": GEMINI_MODEL,
            "openai_api_key": "",
            "openai_model": OPENAI_MODEL,
            "ollama_model": OLLAMA_MODEL,
            "groq_model": GROQ_MODEL,
        }


def get_gemini_api_key():
    """
    Return the Gemini key without printing or persisting it.

    By default, users must provide their own key in AI Settings so visitors do
    not spend the app owner's Gemini quota. Set REQUIRE_USER_API_KEYS=false only
    for private deployments where using a shared app key is intentional.
    """
    settings = get_session_ai_settings()
    user_id = _get_current_user_id()
    saved_user_key = get_user_api_key(user_id, "gemini") if user_id else ""
    session_key = settings.get("gemini_api_key")

    if REQUIRE_USER_API_KEYS:
        return saved_user_key or session_key

    return (
        saved_user_key
        or session_key
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

    if REQUIRE_USER_API_KEYS:
        return session_key

    return session_key or os.getenv("GROQ_API_KEY", "") or _get_streamlit_secret("GROQ_API_KEY")


def get_openai_api_key():
    """Return the OpenAI key for the current user/session without exposing it."""
    settings = get_session_ai_settings()
    user_id = _get_current_user_id()
    saved_user_key = get_user_api_key(user_id, "openai") if user_id else ""
    session_key = settings.get("openai_api_key")

    if REQUIRE_USER_API_KEYS:
        return saved_user_key or session_key

    return (
        saved_user_key
        or session_key
        or os.getenv("OPENAI_API_KEY", "")
        or _get_streamlit_secret("OPENAI_API_KEY")
    )


def get_gemini_key_source():
    """Return where the active Gemini key is coming from, without exposing it."""
    settings = get_session_ai_settings()
    user_id = _get_current_user_id()
    if user_id and get_user_api_key(user_id, "gemini"):
        return "saved securely for this user"

    if settings.get("gemini_api_key"):
        return "temporary AI Settings session password field"

    if REQUIRE_USER_API_KEYS:
        return "missing - each user must add their own key in AI Settings"

    env_file_values = dotenv_values(PROJECT_ROOT / ".env")
    if env_file_values.get("GEMINI_API_KEY"):
        return "local .env file"

    if os.getenv("GEMINI_API_KEY", ""):
        return "environment variable"

    if _get_streamlit_secret("GEMINI_API_KEY"):
        return "Streamlit secrets"

    return "missing"


def get_openai_key_source():
    """Return where the active OpenAI key is coming from, without exposing it."""
    settings = get_session_ai_settings()
    user_id = _get_current_user_id()
    if user_id and get_user_api_key(user_id, "openai"):
        return "saved securely for this user"

    if settings.get("openai_api_key"):
        return "temporary AI Settings session password field"

    if REQUIRE_USER_API_KEYS:
        return "missing - each user must add their own key in AI Settings"

    env_file_values = dotenv_values(PROJECT_ROOT / ".env")
    if env_file_values.get("OPENAI_API_KEY"):
        return "local .env file"

    if os.getenv("OPENAI_API_KEY", ""):
        return "environment variable"

    if _get_streamlit_secret("OPENAI_API_KEY"):
        return "Streamlit secrets"

    return "missing"


def user_api_keys_required():
    """Return whether visitors must provide their own AI provider keys."""
    return REQUIRE_USER_API_KEYS


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


def ask_gemini_multimodal(prompt, image_paths=None, model=None, api_key=None):
    """Send text plus image attachments to a Gemini multimodal model."""
    key = api_key or get_gemini_api_key()
    if not key:
        raise AIProviderError(MISSING_GEMINI_KEY_MESSAGE)

    clean_paths = [Path(path) for path in (image_paths or []) if path]
    if not clean_paths:
        return ask_gemini(prompt, model=model, api_key=key)

    preferred_model = normalize_gemini_model(
        model or get_session_ai_settings().get("gemini_model") or GEMINI_MODEL
    )
    model_errors = []
    quota_error_seen = False
    for attempt_number, selected_model in enumerate(get_gemini_model_candidates(preferred_model), start=1):
        try:
            return _ask_single_gemini_multimodal_model(
                prompt=prompt,
                image_paths=clean_paths,
                api_key=key,
                selected_model=selected_model,
            )
        except AIProviderError as exc:
            status_code = getattr(exc, "status_code", None)
            quota_error_seen = quota_error_seen or getattr(exc, "quota_error", False)
            model_errors.append(str(exc))
            if status_code not in TEMPORARY_GEMINI_STATUSES:
                raise
            if attempt_number < len(get_gemini_model_candidates(preferred_model)):
                time.sleep(0.8)
                continue

    if quota_error_seen:
        raise AIProviderError(
            "Gemini quota or rate limit is blocking this API key right now. "
            "Try again later, use another Gemini key, or switch to Ollama/Demo Mode."
        )
    raise AIProviderError(
        "Gemini vision is temporarily unavailable. "
        f"Last error: {model_errors[-1] if model_errors else 'No details returned.'}"
    )


def _ask_single_gemini_multimodal_model(prompt, image_paths, api_key, selected_model):
    """Call one Gemini model with inline image data."""
    parts = [{"text": prompt}]
    for image_path in image_paths[:5]:
        mime_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
        try:
            image_bytes = image_path.read_bytes()
        except OSError as exc:
            raise AIProviderError("Could not read one attached image safely.") from exc
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                }
            }
        )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{selected_model}:generateContent"
    )
    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json={"contents": [{"parts": parts}]},
            timeout=160,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        detail = _safe_gemini_error_message(response if "response" in locals() else None)
        if status_code in {401, 403}:
            message = "Gemini rejected the API key. Please check your Gemini API key."
        elif status_code == 404:
            message = f"Gemini model '{selected_model}' is not available for vision input."
        elif status_code == 429:
            message = f"Gemini quota or rate limit was reached for model '{selected_model}'."
        elif status_code in TEMPORARY_GEMINI_STATUSES:
            message = f"Gemini vision model '{selected_model}' is temporarily busy."
        elif status_code:
            message = f"Gemini vision request failed with status {status_code}."
        else:
            message = "Could not connect to Gemini vision. Please check your internet connection."
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
        raise AIProviderError("Gemini vision returned an unexpected response format.") from exc


def _openai_client(api_key):
    """Create an OpenAI SDK client lazily so the app still imports if the SDK is missing."""
    try:
        from openai import OpenAI
    except Exception as exc:
        raise AIProviderError("OpenAI SDK is not installed. Run pip install -r requirements.txt.") from exc
    return OpenAI(api_key=api_key)


def _extract_openai_response_text(response):
    """Return text from OpenAI Responses API objects without depending on one SDK shape."""
    output_text = getattr(response, "output_text", "")
    if output_text:
        return str(output_text).strip()

    try:
        output = getattr(response, "output", []) or []
        chunks = []
        for item in output:
            content = getattr(item, "content", []) or []
            for part in content:
                text = getattr(part, "text", "")
                if text:
                    chunks.append(text)
        return "\n".join(chunks).strip()
    except Exception:
        return ""


def _safe_openai_error_message(exc, selected_model=None):
    """Convert OpenAI SDK exceptions into safe user-facing messages."""
    status_code = getattr(exc, "status_code", None)
    message = str(exc).lower()
    model_hint = f" Model: {selected_model}." if selected_model else ""

    if status_code in {401, 403} or "api key" in message or "authentication" in message:
        return "OpenAI rejected the API key. Please check your OpenAI API key in AI Settings."
    if status_code == 404 or "model" in message and "not found" in message:
        return f"OpenAI model is not available for this key.{model_hint} Select another model in AI Settings."
    if status_code == 429 or "rate limit" in message or "quota" in message or "billing" in message:
        return "OpenAI request was blocked by rate limit, quota, or billing. Check your OpenAI account usage."
    if status_code and status_code >= 500:
        return "OpenAI is temporarily unavailable. Please try again in a few minutes."
    if status_code:
        return f"OpenAI request failed with status {status_code}. Please check your key, model, or billing/quota."
    return "OpenAI request failed. Please check your API key, model selection, or billing/quota."


def generate_with_openai(prompt, api_key=None, model=None, attachments=None):
    """Generate a text response with OpenAI."""
    key = api_key or get_openai_api_key()
    if not key:
        raise AIProviderError(MISSING_OPENAI_KEY_MESSAGE)

    selected_model = model or get_session_ai_settings().get("openai_model") or OPENAI_MODEL
    try:
        client = _openai_client(key)
        response = client.responses.create(
            model=selected_model,
            input=prompt,
        )
        text = _extract_openai_response_text(response)
        if not text:
            raise AIProviderError("OpenAI returned an empty response. Please try again.")
        return text
    except AIProviderError:
        raise
    except Exception as exc:
        raise AIProviderError(_safe_openai_error_message(exc, selected_model)) from exc


def _image_to_openai_part(image_path):
    """Build an OpenAI Responses API image part from a local image path."""
    path = Path(image_path)
    try:
        image_bytes = path.read_bytes()
    except OSError as exc:
        raise AIProviderError("Could not read one attached image safely.") from exc
    mime_type = mimetypes.guess_type(str(path))[0] or "image/png"
    image_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    return {"type": "input_image", "image_url": image_url}


def generate_with_openai_multimodal(prompt, api_key=None, model=None, image_paths=None, file_context=None):
    """Generate a response with OpenAI using text plus optional image attachments."""
    clean_paths = [Path(path) for path in (image_paths or []) if path]
    if not clean_paths:
        combined_prompt = prompt
        if file_context:
            combined_prompt = f"{prompt}\n\nAttached file context:\n{file_context}"
        return generate_with_openai(combined_prompt, api_key=api_key, model=model)

    key = api_key or get_openai_api_key()
    if not key:
        raise AIProviderError(MISSING_OPENAI_KEY_MESSAGE)

    selected_model = model or get_session_ai_settings().get("openai_model") or OPENAI_MODEL
    content = [{"type": "input_text", "text": prompt}]
    if file_context:
        content.append({"type": "input_text", "text": f"Attached file context:\n{file_context}"})
    for image_path in clean_paths[:5]:
        content.append(_image_to_openai_part(image_path))

    try:
        client = _openai_client(key)
        response = client.responses.create(
            model=selected_model,
            input=[{"role": "user", "content": content}],
        )
        text = _extract_openai_response_text(response)
        if not text:
            raise AIProviderError("OpenAI returned an empty multimodal response. Please try again.")
        return text
    except AIProviderError:
        raise
    except Exception as exc:
        raise AIProviderError(_safe_openai_error_message(exc, selected_model)) from exc


def transcribe_with_openai_audio(file_path, api_key=None, model=None):
    """Optionally transcribe audio with OpenAI if the selected account/model supports it."""
    key = api_key or get_openai_api_key()
    if not key:
        return {
            "success": False,
            "transcript": "",
            "method": "openai_audio",
            "error": "OpenAI audio transcription is not configured yet. Using available transcription fallback.",
        }

    selected_model = model or os.getenv("OPENAI_AUDIO_MODEL", "gpt-4o-mini-transcribe")
    try:
        client = _openai_client(key)
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=selected_model,
                file=audio_file,
            )
        text = (getattr(transcript, "text", "") or "").strip()
        return {
            "success": bool(text),
            "transcript": text,
            "method": "openai_audio",
            "error": "" if text else "No speech was detected. Please try again with clearer audio.",
        }
    except Exception as exc:
        return {
            "success": False,
            "transcript": "",
            "method": "openai_audio",
            "error": "OpenAI audio transcription is not configured yet. Using available transcription fallback.",
            "technical_error": str(exc)[:160],
        }


ask_openai = generate_with_openai


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
    try:
        from modules.database import get_app_setting

        if str(get_app_setting("enable_demo_mode", "true")).lower() != "true":
            raise AIProviderError("Demo Mode is disabled by the admin.")
    except AIProviderError:
        raise
    except Exception:
        pass
    return (
        "Demo Mode response: AI provider is not connected yet. "
        "Add a Gemini API key in AI Settings or switch to Ollama local mode."
    )


def ask_ai(prompt, provider=None, model=None):
    """Ask the selected AI provider. Gemini is the default provider."""
    _check_ai_rate_limit()
    selected_provider = normalize_provider(provider or get_selected_provider())

    if selected_provider == "Gemini":
        return ask_gemini(prompt, model=model)

    if selected_provider == "OpenAI":
        selected_model = model or get_session_ai_settings().get("openai_model") or OPENAI_MODEL
        return generate_with_openai(prompt, model=selected_model)

    if selected_provider == "Ollama":
        selected_model = model or get_session_ai_settings().get("ollama_model") or OLLAMA_MODEL
        return ask_ollama(prompt, model=selected_model)

    if selected_provider == "Groq":
        selected_model = model or get_session_ai_settings().get("groq_model") or GROQ_MODEL
        return ask_groq(prompt, model=selected_model)

    return ask_demo(prompt)


def get_missing_key_message():
    """Expose the missing-key copy for pages that want to show it directly."""
    provider = normalize_provider(get_selected_provider())
    if provider == "OpenAI":
        return MISSING_OPENAI_KEY_MESSAGE
    return MISSING_GEMINI_KEY_MESSAGE


def generate_response(prompt, provider=None, model=None, attachments=None):
    """Compatibility wrapper for pages that need a generic AI response call."""
    return ask_ai(prompt, provider=provider, model=model)


def chat_with_notes(
    subject_id,
    question,
    model=None,
    answer_style="Simple English",
    provider=None,
    user_id=None,
):
    """Answer a student question using only the uploaded notes for a subject."""
    try:
        matches = query_subject_notes(subject_id, question, user_id=user_id)
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
{build_study_assistant_system_prompt()}

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
        answer = safe_ai_error_message(exc)

    return {
        "answer": answer,
        "sources": matches,
    }


def build_study_chat_prompt(
    question,
    answer_style,
    notes_context="",
    attachment_context="",
    context_label="General Chat",
    general_chat=False,
    chat_history="",
    user_memory="",
    user_id=None,
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

    display_name = get_memory_display_name(user_id, get_current_user_display_name())

    return f"""
{build_study_assistant_system_prompt(display_name)}

Answer style: {answer_style}
Style instruction: {style_instruction}

User profile and saved study preferences:
{user_memory or "No saved user memories."}

Recent conversation:
{chat_history or "No previous messages in this chat."}

{context_block}

Attached file context:
{attachment_context or "No files attached to this message."}

Student question:
{question}

Answer with clean, study-friendly Markdown. For non-trivial questions, use a natural subset of:
# Topic Title
## What I found in the attachment
## Simple Explanation
## Key Points
## Example
## Visual / Table / Flowchart
## Exam-Style Answer
## Common Mistakes
## Quick Revision Tip
## Follow-up Suggestions

Do not force every section for simple questions. Use tables, formulas, ASCII diagrams,
Mermaid flowcharts, or step-by-step layouts when they make the answer easier to study.
"""


def _content_words(text):
    """Return meaningful lowercase words for a simple relevance check."""
    words = []
    for raw_word in text.lower().replace("_", " ").split():
        word = "".join(char for char in raw_word if char.isalnum())
        if len(word) >= 3 and word not in RELEVANCE_STOPWORDS:
            words.append(word)
    return set(words)


def _filter_relevant_sources(question, sources):
    """Remove weak matches so unrelated notes fall back to general knowledge."""
    question_words = _content_words(question)
    if not question_words:
        return sources

    relevant_sources = []
    for source in sources:
        source_words = _content_words(source.get("text", ""))
        overlap = question_words.intersection(source_words)

        if overlap:
            relevant_sources.append(source)

    return relevant_sources


def _attachment_context_has_text(attachment_context):
    """Return True when an attachment prompt block contains readable extracted text."""
    return bool(attachment_context and "Extracted text/context:" in attachment_context)


def _demo_attachment_response(attachment_context):
    """Return a safe offline placeholder for attachment-based prompts."""
    preview = (attachment_context or "").strip()[:1600] or "No readable attachment text was extracted."
    return f"""
Demo Mode response: I received your attachment(s).

## What I found in the attachment
{preview}

## Placeholder answer
Connect Gemini for image understanding, or use Ollama/Groq when readable text was extracted from the file.
"""


def _provider_cannot_read_attachment_response():
    """Explain why a non-vision provider cannot answer from an unreadable attachment."""
    return (
        "This provider cannot directly read this attachment, and no readable text was extracted. "
        "Try Gemini vision, OpenAI vision, upload clearer text, or use a transcription provider for audio."
    )


def generate_study_chat_response(
    question,
    answer_style="Simple English",
    chat_mode="General Chat",
    subject_id=None,
    document_ids=None,
    context_label="General Chat",
    limit=5,
    user_id=None,
    chat_history="",
    user_memory="",
    attachment_context="",
    image_paths=None,
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
                user_id=user_id,
            )
            sources = _filter_relevant_sources(question, sources)
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
        attachment_context=attachment_context,
        context_label=context_label,
        general_chat=chat_mode == "General Chat",
        chat_history=chat_history,
        user_memory=user_memory or format_user_memory_profile(user_id),
        user_id=user_id,
    )

    selected_provider = normalize_provider(get_selected_provider())
    attachment_has_text = _attachment_context_has_text(attachment_context)

    try:
        if attachment_context and selected_provider == "Demo Mode":
            answer = _demo_attachment_response(attachment_context)
        elif attachment_context and not attachment_has_text and not image_paths:
            answer = _provider_cannot_read_attachment_response()
        elif image_paths and selected_provider == "Gemini":
            try:
                answer = ask_gemini_multimodal(prompt, image_paths=image_paths)
            except Exception:
                if attachment_has_text:
                    answer = ask_ai(prompt)
                else:
                    raise
        elif image_paths and selected_provider == "OpenAI":
            try:
                answer = generate_with_openai_multimodal(prompt, image_paths=image_paths)
            except Exception:
                if attachment_has_text:
                    answer = ask_ai(prompt)
                else:
                    raise
        elif image_paths and not attachment_has_text:
            answer = _provider_cannot_read_attachment_response()
        else:
            answer = ask_ai(prompt)
    except Exception as exc:
        answer = safe_ai_error_message(exc)

    return {
        "answer": answer,
        "sources": sources,
        "warning": warning,
        "source_count": len(sources),
    }
