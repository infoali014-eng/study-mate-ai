import os

import streamlit as st

from modules import ai_engine
from modules.auth import require_login
from modules.database import (
    api_key_saving_configured,
    clear_user_memories,
    delete_user_memory,
    delete_user_api_key,
    get_user_memories,
    get_user_api_key_status,
    init_db,
    save_user_api_key,
)
from modules.ui import (
    apply_theme,
    page_header,
    render_feature_card,
    section_title,
    sidebar_nav,
)


GEMINI_MODEL = getattr(ai_engine, "GEMINI_MODEL", "gemini-2.0-flash")
OPENAI_MODEL = getattr(ai_engine, "OPENAI_MODEL", "gpt-5.4-mini")
OPENAI_MODEL_OPTIONS = getattr(ai_engine, "OPENAI_MODEL_OPTIONS", ["gpt-5.4-mini", "gpt-5.4", "gpt-5.5"])
OLLAMA_MODEL = getattr(ai_engine, "OLLAMA_MODEL", "llama3.2")
GROQ_MODEL = getattr(ai_engine, "GROQ_MODEL", "llama-3.1-8b-instant")
MISSING_KEY_MESSAGE = (
    "Gemini API key is missing. Add it in AI Settings, save it securely for your account, "
    "or enter a temporary session key."
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


def has_openai_key():
    """Check for an OpenAI key without displaying it."""
    if hasattr(ai_engine, "get_openai_api_key"):
        return bool(ai_engine.get_openai_api_key())
    return bool(st.session_state.get("openai_api_key") or os.getenv("OPENAI_API_KEY", ""))


def gemini_key_source():
    """Show where the active key is coming from without revealing the key."""
    if hasattr(ai_engine, "get_gemini_key_source"):
        return ai_engine.get_gemini_key_source()
    if st.session_state.get("gemini_api_key"):
        return "AI Settings session password field"
    if os.getenv("GEMINI_API_KEY", ""):
        return "environment variable or local .env file"
    return "missing"


def openai_key_source():
    """Show where the active OpenAI key is coming from without revealing the key."""
    if hasattr(ai_engine, "get_openai_key_source"):
        return ai_engine.get_openai_key_source()
    if st.session_state.get("openai_api_key"):
        return "AI Settings session password field"
    if os.getenv("OPENAI_API_KEY", ""):
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
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

page_header(
    "AI Settings",
    "Choose Gemini, OpenAI, Ollama, Groq, or Demo Mode without exposing your API keys.",
    "Secure Provider Setup",
)

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card(
        "User-owned keys",
        "Each visitor can save their own Gemini or OpenAI key securely.",
        "\u2728",
        "#14b8b4",
        "#d8fff6",
    )
with feature2:
    render_feature_card(
        "OpenAI / ChatGPT",
        "Use OpenAI models for chat, tutoring, quizzes, and planning.",
        "\U0001f916",
        "#2f7df6",
        "#e3efff",
    )
with feature3:
    render_feature_card(
        "Local or Demo",
        "Keep Ollama local mode and Demo Mode available as fallbacks.",
        "\U0001f9ea",
        "#ffb703",
        "#fff3c4",
    )

section_title("Provider", "\u2699\ufe0f")
with st.container(border=True):
    current_provider = get_provider_label()
    provider_options = ["Gemini API", "OpenAI API", "Groq API", "Ollama Local", "Demo Mode"]
    provider_aliases = {
        "Gemini": "Gemini API",
        "OpenAI": "OpenAI API",
        "Groq": "Groq API",
        "Ollama": "Ollama Local",
    }
    current_provider_label = provider_aliases.get(current_provider, current_provider)
    provider_index = provider_options.index(current_provider_label) if current_provider_label in provider_options else 0
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

    current_openai_model = st.session_state.get("openai_model", os.getenv("OPENAI_MODEL", OPENAI_MODEL))
    if current_openai_model not in OPENAI_MODEL_OPTIONS:
        OPENAI_MODEL_OPTIONS = [current_openai_model] + list(OPENAI_MODEL_OPTIONS)
    st.session_state.openai_model = st.selectbox(
        "OpenAI model",
        OPENAI_MODEL_OPTIONS,
        index=OPENAI_MODEL_OPTIONS.index(current_openai_model),
        help="Used only when provider is OpenAI API. If your account cannot access a model, select another one.",
    )

    st.session_state.ollama_model = st.text_input(
        "Ollama model",
        value=st.session_state.get("ollama_model", os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)),
        help="Used only when provider is Ollama.",
    )

    st.session_state.groq_model = st.text_input(
        "Groq model",
        value=st.session_state.get("groq_model", os.getenv("GROQ_MODEL", GROQ_MODEL)),
        help="Used only when provider is Groq.",
    )

section_title("API Key", "\U0001f512")
with st.container(border=True):
    saved_key_status = get_user_api_key_status(user_id, "gemini")
    saving_ready = api_key_saving_configured()

    if saved_key_status and saving_ready:
        suffix = saved_key_status["key_suffix"] or "****"
        st.success(f"Gemini API key saved securely. Key ending in ****{suffix}.")
    elif saved_key_status:
        st.warning(
            "A saved Gemini key record exists, but API key saving is not configured on this server. "
            "Add APP_ENCRYPTION_KEY to unlock saved keys, or use a temporary key."
        )
    elif saving_ready:
        st.info("No saved Gemini API key for this account yet.")
    else:
        st.info(
            "Secure key saving is available. For best Streamlit Cloud stability, add "
            "APP_ENCRYPTION_KEY in secrets; locally the app creates an ignored private key file."
        )

    entered_key = st.text_input(
        "Gemini API key",
        type="password",
        placeholder="Paste Gemini key",
        help="The key is never displayed or printed. Save it securely, or use it temporarily for this session.",
        key="gemini_key_entry",
    )

    save_label = "Replace Saved Gemini Key" if saved_key_status else "Save Gemini Key"
    save_col, temp_col, remove_col = st.columns(3)
    with save_col:
        if st.button(save_label, type="primary", use_container_width=True):
            clean_key = entered_key.strip()
            if not clean_key:
                st.warning("Paste a Gemini API key first.")
            elif not saving_ready:
                st.error("Secure key saving is not available in this environment.")
            else:
                try:
                    save_user_api_key(user_id, "gemini", clean_key)
                    st.session_state.pop("gemini_api_key", None)
                    st.success("Gemini API key saved securely for this account.")
                    st.rerun()
                except Exception:
                    st.error("Could not save the Gemini API key securely. Check APP_ENCRYPTION_KEY.")

    with temp_col:
        if st.button("Use Temporarily", use_container_width=True):
            clean_key = entered_key.strip()
            if not clean_key:
                st.warning("Paste a Gemini API key first.")
            else:
                st.session_state.gemini_api_key = clean_key
                st.success("Gemini API key saved for this browser session only.")
                st.rerun()

    with remove_col:
        if st.button("Remove Saved Key", use_container_width=True):
            delete_user_api_key(user_id, "gemini")
            st.session_state.pop("gemini_api_key", None)
            st.success("Saved Gemini key removed for this account.")
            st.rerun()

    if has_gemini_key():
        st.success(f"Gemini API key is available from: {gemini_key_source()}.")
    else:
        st.warning(missing_key_message())

    if getattr(ai_engine, "user_api_keys_required", lambda: True)():
        st.info(
            "Public app mode is active: Gemini uses the signed-in user's saved key first, "
            "then their temporary session key. Shared deployment keys are not used unless "
            "REQUIRE_USER_API_KEYS=false is configured intentionally."
        )

    if st.button("Clear Temporary Gemini Key From This Session", use_container_width=True):
        st.session_state.pop("gemini_api_key", None)
        st.success("Temporary Gemini key removed from this browser session.")
        st.rerun()

    if st.button("Test Gemini Connection", type="primary", use_container_width=True):
        try:
            response = ai_engine.ask_gemini("Say OK only.")
            st.success(f"Gemini connection works. Response: {response[:40]}")
        except Exception as exc:
            if hasattr(ai_engine, "safe_ai_error_message"):
                st.error(ai_engine.safe_ai_error_message(exc))
            else:
                st.error("Gemini could not complete the test request.")
            st.info(
                "If this is a quota/rate-limit message, your key is being found, "
                "but Google is blocking more Gemini requests right now. You can wait, "
                "try another Gemini key, or select Ollama/Demo Mode above."
            )

section_title("OpenAI API Key", "\U0001f916")
with st.container(border=True):
    st.info(
        "OpenAI API is usually usage-based and may cost money. Use your own API key and monitor usage."
    )
    saved_openai_status = get_user_api_key_status(user_id, "openai")
    saving_ready = api_key_saving_configured()

    if saved_openai_status and saving_ready:
        suffix = saved_openai_status["key_suffix"] or "****"
        st.success(f"OpenAI API key saved securely. Key ending in ****{suffix}.")
    elif saved_openai_status:
        st.warning(
            "A saved OpenAI key record exists, but API key saving is not configured on this server. "
            "Add APP_ENCRYPTION_KEY to unlock saved keys, or use a temporary key."
        )
    elif saving_ready:
        st.info("No saved OpenAI API key for this account yet.")
    else:
        st.info(
            "Secure key saving needs APP_ENCRYPTION_KEY. You can still use a temporary OpenAI key "
            "for this browser session."
        )

    entered_openai_key = st.text_input(
        "OpenAI API key",
        type="password",
        placeholder="Paste OpenAI key",
        help="The key is never displayed or printed. Save it securely, or use it temporarily for this session.",
        key="openai_key_entry",
    )

    openai_save_label = "Replace Saved OpenAI Key" if saved_openai_status else "Save OpenAI Key"
    openai_save_col, openai_temp_col, openai_remove_col = st.columns(3)
    with openai_save_col:
        if st.button(openai_save_label, type="primary", use_container_width=True):
            clean_key = entered_openai_key.strip()
            if not clean_key:
                st.warning("Paste an OpenAI API key first.")
            elif not saving_ready:
                st.error("Secure key saving is not available in this environment.")
            else:
                try:
                    save_user_api_key(user_id, "openai", clean_key)
                    st.session_state.pop("openai_api_key", None)
                    st.success("OpenAI API key saved securely for this account.")
                    st.rerun()
                except Exception:
                    st.error("Could not save the OpenAI API key securely. Check APP_ENCRYPTION_KEY.")

    with openai_temp_col:
        if st.button("Use OpenAI Temporarily", use_container_width=True):
            clean_key = entered_openai_key.strip()
            if not clean_key:
                st.warning("Paste an OpenAI API key first.")
            else:
                st.session_state.openai_api_key = clean_key
                st.success("OpenAI API key saved for this browser session only.")
                st.rerun()

    with openai_remove_col:
        if st.button("Remove OpenAI Key", use_container_width=True):
            delete_user_api_key(user_id, "openai")
            st.session_state.pop("openai_api_key", None)
            st.success("Saved OpenAI key removed for this account.")
            st.rerun()

    if has_openai_key():
        st.success(f"OpenAI API key is available from: {openai_key_source()}.")
    else:
        st.warning("OpenAI API key is missing. Add it in AI Settings.")

    if st.button("Clear Temporary OpenAI Key From This Session", use_container_width=True):
        st.session_state.pop("openai_api_key", None)
        st.success("Temporary OpenAI key removed from this browser session.")
        st.rerun()

    if st.button("Test OpenAI Connection", type="primary", use_container_width=True):
        try:
            response = ai_engine.generate_with_openai(
                "Say OK only.",
                model=st.session_state.get("openai_model", OPENAI_MODEL),
            )
            st.success(f"OpenAI connection works. Response: {response[:40]}")
        except Exception as exc:
            if hasattr(ai_engine, "safe_ai_error_message"):
                st.error(ai_engine.safe_ai_error_message(exc))
            else:
                st.error("OpenAI could not complete the test request.")
            st.info(
                "If this is a model, quota, or billing message, your key may be loaded correctly "
                "but OpenAI is not allowing this request. Try another model or check your account."
            )

section_title("Groq Key", "\U0001f511")
with st.container(border=True):
    entered_groq_key = st.text_input(
        "Groq API key",
        type="password",
        placeholder="Paste Groq key for this browser session only",
        help="This is stored only in Streamlit session state and is never printed.",
    )

    if entered_groq_key:
        st.session_state.groq_api_key = entered_groq_key
        st.success("Groq API key saved for this session only.")

    if getattr(ai_engine, "get_groq_api_key", lambda: "")():
        st.success("Groq API key is available.")
    else:
        st.info("Groq API key is optional. Add it only if you want Groq provider mode.")

    if st.button("Clear Groq Key From This Session", use_container_width=True):
        st.session_state.pop("groq_api_key", None)
        st.success("Groq key removed from this browser session.")
        st.rerun()

section_title("Memory Settings", "\U0001f9e0")
with st.container(border=True):
    st.session_state.memory_enabled = st.toggle(
        "Memory enabled",
        value=bool(st.session_state.get("memory_enabled", True)),
        help="When enabled, StudyMate can use saved study preferences and recent chat context.",
    )
    st.caption(
        "Memory is private to your account. It is not shown to other users and does not store passwords or API keys."
    )

    memories = get_user_memories(user_id, active_only=True)
    if not memories:
        st.info("No saved memories yet. Try telling the chatbot: My name is Ahmed and I prefer Roman Urdu.")
    else:
        st.markdown("**Saved memories**")
        for memory in memories:
            with st.container(border=True):
                info_col, action_col = st.columns([4, 1])
                with info_col:
                    st.markdown(f"**{memory['memory_key']}**")
                    st.caption(str(memory["category"]).replace("_", " ").title())
                    st.write(memory["memory_value"])
                with action_col:
                    if st.button("Delete", key=f"delete_memory_{memory['id']}", use_container_width=True):
                        delete_user_memory(user_id, memory["id"])
                        st.success("Memory deleted.")
                        st.rerun()

    if memories:
        if st.button("Clear All Memories", use_container_width=True):
            clear_user_memories(user_id)
            st.success("All memories cleared for this account.")
            st.rerun()

st.info(
    "Privacy note: Online AI providers may receive selected note chunks needed to answer "
    "your question. Use Offline/Demo mode for maximum privacy."
)
st.info(
    "Safe setup: public users should paste their own key above. Never commit real keys."
)
