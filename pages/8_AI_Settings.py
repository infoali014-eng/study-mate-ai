import os

import streamlit as st

from modules import ai_engine
from modules.database import init_db
from modules.ui import (
    apply_theme,
    page_header,
    render_feature_card,
    section_title,
    sidebar_nav,
)


GEMINI_MODEL = getattr(ai_engine, "GEMINI_MODEL", "gemini-2.0-flash")
OLLAMA_MODEL = getattr(ai_engine, "OLLAMA_MODEL", "llama3.2")
MISSING_KEY_MESSAGE = (
    "Gemini API key is missing. Add it in .env, Streamlit secrets, "
    "environment variable, or enter it in AI Settings."
)


def get_provider_label():
    """Return the selected provider, even if Streamlit is holding an older module."""
    if hasattr(ai_engine, "get_selected_provider"):
        return ai_engine.get_selected_provider()
    return st.session_state.get("ai_provider", "Gemini")


def has_gemini_key():
    """Check for a Gemini key without displaying it."""
    if hasattr(ai_engine, "get_gemini_api_key"):
        return bool(ai_engine.get_gemini_api_key())
    return bool(st.session_state.get("gemini_api_key") or os.getenv("GEMINI_API_KEY", ""))


def gemini_key_source():
    """Show where the active key is coming from without revealing the key."""
    if hasattr(ai_engine, "get_gemini_key_source"):
        return ai_engine.get_gemini_key_source()
    if st.session_state.get("gemini_api_key"):
        return "AI Settings session password field"
    if os.getenv("GEMINI_API_KEY", ""):
        return "environment variable or local .env file"
    return "missing"


def missing_key_message():
    """Return the configured missing-key message with a local fallback."""
    if hasattr(ai_engine, "get_missing_key_message"):
        return ai_engine.get_missing_key_message()
    return MISSING_KEY_MESSAGE


def normalize_model(model):
    """Keep the settings UI away from unavailable older Gemini models."""
    if hasattr(ai_engine, "normalize_gemini_model"):
        return ai_engine.normalize_gemini_model(model)
    if model in {"gemini-1.5-flash", "gemini-1.5-pro"}:
        return GEMINI_MODEL
    return model or GEMINI_MODEL


st.set_page_config(page_title="AI Settings - StudyMate AI", layout="wide")
init_db()
apply_theme()
sidebar_nav()

page_header(
    "AI Settings",
    "Choose Gemini, Ollama, or Demo Mode without exposing your API keys.",
    "Secure Provider Setup",
)

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card(
        "Gemini default",
        "Use Gemini with a local secret, environment variable, or password input.",
        "\u2728",
        "#14b8b4",
        "#d8fff6",
    )
with feature2:
    render_feature_card(
        "Ollama local",
        "Keep offline mode available when you want local AI responses.",
        "\U0001f4bb",
        "#2f7df6",
        "#e3efff",
    )
with feature3:
    render_feature_card(
        "Demo fallback",
        "Use a safe placeholder response while configuring providers.",
        "\U0001f9ea",
        "#ffb703",
        "#fff3c4",
    )

section_title("Provider", "\u2699\ufe0f")
with st.container(border=True):
    current_provider = get_provider_label()
    provider_options = ["Gemini", "Ollama", "Demo Mode"]
    provider_index = provider_options.index(current_provider) if current_provider in provider_options else 0
    st.session_state.ai_provider = st.selectbox(
        "Selected AI provider",
        provider_options,
        index=provider_index,
    )

    current_gemini_model = normalize_model(
        st.session_state.get("gemini_model", os.getenv("GEMINI_MODEL", GEMINI_MODEL))
    )
    st.session_state.gemini_model = st.text_input(
        "Gemini model",
        value=current_gemini_model,
        help="Recommended: gemini-2.0-flash. The app will automatically try fallback models if Gemini is busy.",
    )

    st.session_state.ollama_model = st.text_input(
        "Ollama model",
        value=st.session_state.get("ollama_model", os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)),
        help="Used only when provider is Ollama.",
    )

section_title("API Key", "\U0001f512")
with st.container(border=True):
    entered_key = st.text_input(
        "Gemini API key",
        type="password",
        placeholder="Paste key for this browser session only",
        help="This is stored only in Streamlit session state and is never printed.",
    )

    if entered_key:
        st.session_state.gemini_api_key = entered_key
        st.success("Gemini API key saved for this session only.")

    if has_gemini_key():
        st.success(f"Gemini API key is available from: {gemini_key_source()}.")
    else:
        st.warning(missing_key_message())

    if st.button("Test Gemini Connection", type="primary", use_container_width=True):
        try:
            response = ai_engine.ask_gemini("Say OK only.")
            st.success(f"Gemini connection works. Response: {response[:40]}")
        except Exception as exc:
            st.error(str(exc))
            st.info(
                "If this is a quota/rate-limit message, your key is being found, "
                "but Google is blocking more Gemini requests right now. You can wait, "
                "try another Gemini key, or select Ollama/Demo Mode above."
            )

st.info(
    "Safe setup: use a local `.env`, Streamlit secrets, environment variable, "
    "Codex secret, or the temporary password field above. Never commit real keys."
)
