import html
import json
import mimetypes
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from modules import ai_engine
from modules.auth import get_current_user_display_name, require_login
from modules.audio_processor import (
    AUDIO_TYPES,
    save_audio_file,
    transcribe_audio,
    validate_audio_file,
)
from modules.database import (
    attach_chat_attachments_to_message,
    create_chat_session,
    delete_chat_session,
    get_chat_attachments,
    get_chat_session,
    get_chat_messages,
    get_chat_sessions,
    get_documents_by_subject,
    get_subjects,
    init_db,
    save_chat_attachment,
    save_chat_message,
    update_chat_session_context,
    update_chat_session_title,
)
from modules.document_processor import IMAGE_TYPES, process_uploaded_file
from modules.security import validate_chat_question
from modules.security import sanitize_filename, is_path_inside
from modules.ui import (
    apply_theme,
    render_ai_loading,
    render_ai_markdown,
    render_empty_state,
    section_title,
    sidebar_nav,
)
from modules.vector_store import VectorStoreError, query_subject_notes


ANSWER_STYLES = ["Simple English", "Roman Urdu", "Exam Style", "Viva Style"]
CHAT_MODES = [
    "General Chat",
    "Chat with Subject",
    "Chat with Specific Notes",
    "Chat with Multiple Notes",
    "Teach Me Mode",
]
TEACH_MATERIAL_OPTIONS = [
    "General Knowledge",
    "Whole Subject Notes",
    "Specific Note",
    "Multiple Notes",
]
LEARNING_LEVELS = [
    "Beginner",
    "Normal",
    "Exam Preparation",
    "Viva Preparation",
    "Last Night Revision",
]
LANGUAGE_STYLES = [
    "Simple English",
    "Roman Urdu",
    "Mixed English + Roman Urdu",
]
TEACHING_DEPTHS = ["Quick", "Balanced", "Deep Explanation"]
DEFAULT_TEACH_SUGGESTIONS = [
    "Explain again more simply",
    "Give me a real-life example",
    "Ask me a question",
    "Give exam-style answer",
    "Show a diagram",
]
MODE_BADGES = {
    "General Chat": "General AI",
    "Chat with Subject": "Subject-based",
    "Chat with Specific Notes": "Single note",
    "Chat with Multiple Notes": "Multiple notes",
    "Teach Me Mode": "Teach Me Mode",
}
BASE_DIR = Path(__file__).resolve().parent.parent
CHAT_UPLOAD_DIR = BASE_DIR / "data" / "chat_uploads"
CHAT_ATTACHMENT_TYPES = {"PDF", "PNG", "JPG", "JPEG", "WEBP", "DOCX", "PPTX", "TXT", "MD"}
CHAT_MAX_ATTACHMENTS = 5
CHAT_IMAGE_MAX_BYTES = 5 * 1024 * 1024
CHAT_DOC_MAX_BYTES = 20 * 1024 * 1024
ATTACHMENT_PROMPT_CHAR_LIMIT = 9000


def get_provider_label():
    """Return the selected provider, even if Streamlit is holding an older module."""
    if hasattr(ai_engine, "get_selected_provider"):
        return ai_engine.get_selected_provider()
    return "Ollama"


def _provider_supports_vision(provider=None):
    """Return True when the selected provider can receive image attachments directly."""
    if hasattr(ai_engine, "provider_supports_vision"):
        return ai_engine.provider_supports_vision(provider or get_provider_label())
    return (provider or get_provider_label()) == "Gemini"


def _is_gemini_provider(provider=None):
    """Return True when the selected provider is Gemini."""
    if hasattr(ai_engine, "is_gemini_provider"):
        return ai_engine.is_gemini_provider(provider or get_provider_label())
    return (provider or get_provider_label()) == "Gemini"


def _is_openai_provider(provider=None):
    """Return True when the selected provider is OpenAI."""
    if hasattr(ai_engine, "is_openai_provider"):
        return ai_engine.is_openai_provider(provider or get_provider_label())
    return (provider or get_provider_label()) == "OpenAI"


def get_subject_index(subjects, subject_id):
    """Find a subject's selectbox index from its id."""
    if not subject_id:
        return 0

    for index, subject in enumerate(subjects):
        if subject["id"] == subject_id:
            return index

    return 0


def source_title(source, index):
    """Build a readable source title from vector metadata."""
    metadata = source.get("metadata", {})
    file_name = metadata.get("file_name", "Uploaded note")
    subject_name = metadata.get("subject_name", "Subject")
    chunk_index = metadata.get("chunk_index", index - 1)
    return f"Source {index}: {file_name} | {subject_name} | Chunk {chunk_index}"


def render_sources(sources):
    """Render sources below an assistant message."""
    if not sources:
        return

    with st.expander(f"Sources used ({len(sources)} relevant note chunks)", expanded=False):
        for index, source in enumerate(sources, start=1):
            st.markdown(f"**{source_title(source, index)}**")
            st.write(source.get("text", "")[:1200])
            st.divider()


def _attachment_icon(file_type):
    """Return a small readable icon for an attachment type."""
    icons = {
        "PDF": "\U0001f4c4",
        "DOCX": "\U0001f4dd",
        "PPTX": "\U0001f4ca",
        "TXT": "\U0001f4c3",
        "MD": "\U0001f4c3",
        "PNG": "\U0001f5bc\ufe0f",
        "JPG": "\U0001f5bc\ufe0f",
        "JPEG": "\U0001f5bc\ufe0f",
        "WEBP": "\U0001f5bc\ufe0f",
        "MP3": "\U0001f399\ufe0f",
        "WAV": "\U0001f399\ufe0f",
        "M4A": "\U0001f399\ufe0f",
        "OGG": "\U0001f399\ufe0f",
        "WEBM": "\U0001f399\ufe0f",
    }
    return icons.get(str(file_type).upper(), "\U0001f4ce")


def _format_size(size_bytes):
    """Return a friendly file size."""
    size = int(size_bytes or 0)
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / 1024:.1f} KB"


def _attachment_rows_to_cards(rows):
    """Convert SQLite attachment rows to message-safe dictionaries."""
    cards = []
    for row in rows or []:
        cards.append(
            {
                "id": row["id"],
                "file_name": row["file_name"],
                "file_type": row["file_type"],
                "file_size": row["file_size"],
                "extraction_method": row["extraction_method"],
                "warning": row["warning_message"],
                "transcript_preview": (row["extracted_text"] or "")[:500],
            }
        )
    return cards


def render_message_attachments(attachments):
    """Render saved attachment chips inside a chat message."""
    if not attachments:
        return
    st.markdown("**Attachments**")
    for attachment in attachments:
        file_type = str(attachment.get("file_type", "")).upper()
        st.markdown(
            f"{_attachment_icon(file_type)} **{html.escape(attachment.get('file_name', 'Attachment'))}** "
            f"`{html.escape(file_type or 'FILE')}` - {_format_size(attachment.get('file_size', 0))}"
        )
        if attachment.get("warning"):
            st.caption(attachment["warning"])
        if str(file_type).upper() in AUDIO_TYPES and attachment.get("transcript_preview"):
            st.caption(f"Transcript: {attachment['transcript_preview']}")


def _chat_attachment_context(attachments):
    """Build a safe prompt block from processed attachments."""
    if not attachments:
        return "", []

    image_paths = []
    blocks = [
        "The user attached the following files. Use them as context for the answer."
    ]
    remaining_chars = ATTACHMENT_PROMPT_CHAR_LIMIT

    for index, attachment in enumerate(attachments, start=1):
        file_type = attachment["file_type"]
        extracted_text = (attachment.get("extracted_text") or "").strip()
        warning = attachment.get("warning", "")
        file_block = [
            f"Attachment {index}: {attachment['file_name']}",
            f"Type: {file_type}",
            f"Extraction method: {attachment.get('extraction_method') or 'not available'}",
        ]
        if warning:
            file_block.append(f"Warning: {warning}")
        if extracted_text and remaining_chars > 0:
            preview = extracted_text[:remaining_chars]
            remaining_chars -= len(preview)
            file_block.append("Extracted text/context:")
            file_block.append(preview)
            if len(extracted_text) > len(preview):
                file_block.append("... attachment text truncated for prompt safety ...")
        else:
            file_block.append("No readable text was extracted from this attachment.")

        blocks.append("\n".join(file_block))
        if file_type in IMAGE_TYPES and attachment.get("file_path"):
            image_paths.append(attachment["file_path"])

    return "\n\n".join(blocks), image_paths


def _audio_upload_to_attachment(uploaded_file, session_id):
    """Save and transcribe one audio upload for the active chat session."""
    if not uploaded_file:
        return None, "Audio file is missing."

    safe_name, validation_error = validate_audio_file(
        getattr(uploaded_file, "name", "voice_recording.wav"),
        getattr(uploaded_file, "size", 0) or 0,
    )
    if validation_error:
        return None, f"{getattr(uploaded_file, 'name', 'audio')}: {validation_error}"

    saved_audio, save_error = save_audio_file(user_id, session_id, uploaded_file)
    if save_error:
        return None, f"{safe_name}: {save_error}"

    provider = get_provider_label()
    if provider == "Demo Mode":
        transcript_result = {
            "success": False,
            "transcript": "",
            "method": "unavailable",
            "error": "Voice transcription needs Gemini API key or local transcription support.",
            "warnings": ["Voice transcription is not available in Demo Mode."],
            "status": {},
        }
    else:
        with st.spinner("Transcribing audio..."):
            gemini_api_key = ai_engine.get_gemini_api_key()
            gemini_model = ai_engine.get_session_ai_settings().get("gemini_model")
            transcript_result = transcribe_audio(
                saved_audio["file_path"],
                provider="auto",
                api_key=gemini_api_key,
                model=gemini_model,
            )
            if (
                not transcript_result.get("transcript")
                and _is_openai_provider(provider)
                and hasattr(ai_engine, "transcribe_with_openai_audio")
            ):
                openai_result = ai_engine.transcribe_with_openai_audio(
                    saved_audio["file_path"],
                    api_key=ai_engine.get_openai_api_key() if hasattr(ai_engine, "get_openai_api_key") else None,
                )
                if openai_result.get("success"):
                    transcript_result = {
                        "success": True,
                        "transcript": openai_result.get("transcript", ""),
                        "method": openai_result.get("method", "openai_audio"),
                        "error": "",
                        "warnings": transcript_result.get("warnings", []),
                        "status": transcript_result.get("status", {}),
                    }
                else:
                    transcript_result.setdefault("warnings", []).append(
                        openai_result.get(
                            "error",
                            "OpenAI audio transcription is not configured yet. Using available transcription fallback.",
                        )
                    )

    transcript = (transcript_result.get("transcript") or "").strip()
    warnings = transcript_result.get("warnings", [])
    error_message = transcript_result.get("error", "")
    warning_parts = [error_message] if error_message else []
    warning_parts.extend(warnings)
    warning_message = " ".join(part for part in warning_parts if part)
    attachment_id = save_chat_attachment(
        user_id=user_id,
        session_id=session_id,
        file_name=saved_audio["file_name"],
        file_path=saved_audio["file_path"],
        file_type=saved_audio["file_type"],
        mime_type=saved_audio["mime_type"],
        file_size=saved_audio["file_size"],
        extracted_text=transcript,
        extraction_method=transcript_result.get("method", "unavailable"),
        warning_message=warning_message,
    )
    if not attachment_id:
        return None, f"{safe_name}: Could not save audio metadata."

    attachment = {
        "id": attachment_id,
        "file_name": saved_audio["file_name"],
        "file_path": saved_audio["file_path"],
        "file_type": saved_audio["file_type"],
        "file_size": saved_audio["file_size"],
        "extracted_text": transcript,
        "extraction_method": transcript_result.get("method", "unavailable"),
        "warning": warning_message,
        "status": transcript_result.get("status", {}),
    }
    if not transcript:
        return attachment, warning_message or "No speech was detected. Please try again with clearer audio."
    return attachment, ""


def _attachment_context_has_text(attachment_context):
    """Return True when an attachment contains extracted text that a text model can use."""
    return bool(attachment_context and "Extracted text/context:" in attachment_context)


def _provider_cannot_read_attachment_response():
    """Friendly message for providers that cannot inspect unreadable images directly."""
    return (
        "This provider cannot directly read this attachment, and no readable text was extracted. "
        "Try Gemini vision, OpenAI vision, upload clearer text, or use a transcription provider for audio."
    )


def _save_and_process_chat_attachments(uploaded_files, session_id):
    """Validate, save, extract, and record chat attachments for the active user."""
    if not uploaded_files:
        return [], []

    files = list(uploaded_files)[:CHAT_MAX_ATTACHMENTS]
    warnings = []
    processed = []
    upload_root = CHAT_UPLOAD_DIR / str(user_id) / str(session_id)
    upload_root.mkdir(parents=True, exist_ok=True)

    for uploaded_file in files:
        safe_name, error = sanitize_filename(uploaded_file.name)
        if error:
            warnings.append(f"{uploaded_file.name}: {error}")
            continue

        file_type = Path(safe_name).suffix.replace(".", "").upper()
        if file_type not in CHAT_ATTACHMENT_TYPES:
            warnings.append(f"{safe_name}: This file type is not supported in chat attachments.")
            continue

        file_size = int(getattr(uploaded_file, "size", 0) or 0)
        max_size = CHAT_IMAGE_MAX_BYTES if file_type in IMAGE_TYPES else CHAT_DOC_MAX_BYTES
        if file_size > max_size:
            warnings.append(f"{safe_name}: This file is too large. Please upload a smaller file.")
            continue

        unique_name = f"{Path(safe_name).stem}_{uuid.uuid4().hex[:8]}{Path(safe_name).suffix.lower()}"
        file_path = upload_root / unique_name
        if not is_path_inside(upload_root, file_path):
            warnings.append(f"{safe_name}: File path was rejected for safety.")
            continue

        file_path.write_bytes(uploaded_file.getvalue())
        result = process_uploaded_file(file_path, file_type)
        warning_message = " ".join(result.get("warnings", []))
        attachment_id = save_chat_attachment(
            user_id=user_id,
            session_id=session_id,
            file_name=safe_name,
            file_path=str(file_path),
            file_type=file_type,
            mime_type=getattr(uploaded_file, "type", "") or mimetypes.guess_type(safe_name)[0] or "",
            file_size=file_size,
            extracted_text=result.get("text", ""),
            extraction_method=result.get("method", ""),
            warning_message=warning_message,
        )
        if not attachment_id:
            warnings.append(f"{safe_name}: Could not save attachment metadata.")
            continue

        processed.append(
            {
                "id": attachment_id,
                "file_name": safe_name,
                "file_path": str(file_path),
                "file_type": file_type,
                "file_size": file_size,
                "extracted_text": result.get("text", ""),
                "extraction_method": result.get("method", ""),
                "warning": warning_message,
            }
        )

    if len(uploaded_files) > CHAT_MAX_ATTACHMENTS:
        warnings.append(f"Only the first {CHAT_MAX_ATTACHMENTS} attachments were processed.")
    return processed, warnings


def render_follow_up_suggestions(message_index, suggestions):
    """Render suggested tutor follow-ups as small buttons."""
    if not suggestions:
        return

    st.markdown("**Try next:**")
    cols = st.columns(min(3, len(suggestions)))
    for index, suggestion in enumerate(suggestions):
        with cols[index % len(cols)]:
            if st.button(
                suggestion,
                key=f"teach_suggestion_{message_index}_{index}",
                use_container_width=True,
            ):
                st.session_state.study_chat_pending_prompt = suggestion
                st.rerun()


def _chat_messages_key():
    """Return the active chat history key for the logged-in user."""
    return f"chat_history_{st.session_state.get('user_id', 'guest')}"


def _chat_messages():
    """Return this user's active session chat history."""
    key = _chat_messages_key()
    if key not in st.session_state:
        st.session_state[key] = []
    st.session_state.study_chat_messages = st.session_state[key]
    return st.session_state[key]


def _set_chat_messages(messages):
    """Replace only this user's active session chat history."""
    key = _chat_messages_key()
    st.session_state[key] = messages
    st.session_state.study_chat_messages = st.session_state[key]


def _decode_json(value, fallback):
    """Decode JSON stored in SQLite chat history."""
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


def _active_chat_session_key():
    """Return the session-state key for this user's selected chat."""
    return f"active_chat_session_user_{st.session_state.get('user_id')}"


def _active_chat_session_id():
    """Return the selected chat id for the current user."""
    return st.session_state.get(_active_chat_session_key())


def _set_active_chat_session(session_id):
    """Set the selected chat id for the current user."""
    st.session_state[_active_chat_session_key()] = session_id


def _generate_chat_title(message):
    """Create a short ChatGPT-style title from the first user message."""
    words = str(message or "").replace("\n", " ").split()
    title = " ".join(words[:7]).strip()
    if len(title) > 50:
        title = title[:47].rstrip() + "..."
    return title or "New Chat"


def _load_saved_chat_messages(session_id):
    """Load one saved chat session into Streamlit session state."""
    rows = get_chat_messages(st.session_state.get("user_id"), session_id)
    attachment_rows = get_chat_attachments(st.session_state.get("user_id"), session_id)
    attachments_by_message = {}
    for attachment in attachment_rows:
        attachments_by_message.setdefault(attachment["message_id"], []).append(attachment)
    messages = []
    for row in rows:
        context = _decode_json(row["context_json"], {})
        metadata = _decode_json(row["metadata_json"], {})
        messages.append(
            {
                "role": row["role"],
                "content": row["content"],
                "context": context,
                "mode": metadata.get("mode", context.get("badge", context.get("label", "General Chat"))),
                "subject_id": metadata.get("subject_id", context.get("subject_id")),
                "document_id": metadata.get("document_id"),
                "sources": _decode_json(row["sources_json"], []),
                "warning": row["warning"],
                "source_count": row["source_count"],
                "suggestions": _decode_json(row["suggestions_json"], []),
                "attachments": _attachment_rows_to_cards(attachments_by_message.get(row["id"], [])),
                "created_at": row["created_at"],
                "timestamp": row["created_at"],
            }
        )
    _set_chat_messages(messages)


def _load_chat_session(session_id):
    """Select and load one owned chat session."""
    session = get_chat_session(st.session_state.get("user_id"), session_id)
    if not session:
        st.error("Chat not found or you do not have access to it.")
        return False
    _set_active_chat_session(session_id)
    saved_mode = session["chat_mode"] or "General Chat"
    if saved_mode not in CHAT_MODES:
        saved_mode = "General Chat"
    st.session_state.study_chat_mode_selector = saved_mode
    if session["subject_id"]:
        st.session_state.chat_prefill_subject_id = session["subject_id"]
    document_ids = _decode_json(session["document_ids_json"], [])
    if document_ids:
        st.session_state.chat_prefill_document_id = document_ids[0]
        st.session_state.chat_prefill_document_ids = document_ids
    _load_saved_chat_messages(session_id)
    loaded_messages = _chat_messages()
    if (session["chat_mode"] or "") == "Teach Me Mode" and loaded_messages:
        for message in reversed(loaded_messages):
            message_context = message.get("context", {})
            if message_context.get("badge") == "Teach Me Mode":
                st.session_state.study_chat_teach_context = message_context
                break
    st.session_state.study_chat_last_question = ""
    st.session_state.study_chat_last_request = None
    return True


def _request_chat_session_load(session_id):
    """Queue a chat session load for the next rerun before widgets are created."""
    st.session_state.study_chat_pending_session_load = session_id


def _ensure_chat_session(chat_mode="General Chat", context_label=""):
    """Ensure the logged-in user has a saved chat session selected."""
    if _active_chat_session_id():
        existing = get_chat_session(st.session_state.get("user_id"), _active_chat_session_id())
        if existing:
            return _active_chat_session_id()
        st.session_state.pop(_active_chat_session_key(), None)

    sessions = get_chat_sessions(st.session_state.get("user_id"), limit=1)
    if sessions:
        _set_active_chat_session(sessions[0]["id"])
        _load_saved_chat_messages(sessions[0]["id"])
        return sessions[0]["id"]

    session_id = create_chat_session(
        st.session_state.get("user_id"),
        title="New Chat",
        mode=chat_mode,
        context_label=context_label,
    )
    _set_active_chat_session(session_id)
    return session_id


def _start_new_chat_session(chat_mode="General Chat", context_label="", context=None):
    """Create and select a fresh saved chat session."""
    context = context or {}
    session_id = create_chat_session(
        st.session_state.get("user_id"),
        title="New Chat",
        mode=chat_mode,
        subject_id=context.get("subject_id"),
        document_ids=context.get("document_ids", []),
        context_label=context_label,
    )
    _set_active_chat_session(session_id)
    _set_chat_messages([])
    return session_id


def _sync_active_chat_context(chat_mode, context):
    """Persist selected mode/context on the active chat."""
    session_id = _ensure_chat_session(chat_mode, context.get("label", ""))
    update_chat_session_context(
        st.session_state.get("user_id"),
        session_id,
        mode=chat_mode,
        subject_id=context.get("subject_id"),
        document_ids=context.get("document_ids", []),
        context_label=context.get("label", ""),
    )
    return session_id


def _persist_chat_message(message):
    """Save a chat message to SQLite for this user."""
    context = message.get("context", {})
    session_id = _sync_active_chat_context(
        context.get("chat_mode") or message.get("mode") or context.get("badge", "General Chat"),
        context,
    )
    return save_chat_message(
        user_id=st.session_state.get("user_id"),
        session_id=session_id,
        role=message.get("role"),
        content=message.get("content", ""),
        metadata={
            "mode": message.get("mode"),
            "subject_id": message.get("subject_id"),
            "document_id": message.get("document_id"),
        },
        context_json=json.dumps(message.get("context", {}), default=str),
        sources_json=json.dumps(message.get("sources", []), default=str),
        warning=message.get("warning", ""),
        source_count=message.get("source_count", 0),
        suggestions_json=json.dumps(message.get("suggestions", []), default=str),
    )


def _message_timestamp():
    """Return a simple timestamp for chat history records."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_chat_pair(question, answer_data, context, attachments=None):
    """Append one user message and one assistant response to session history."""
    attachments = attachments or []
    messages = _chat_messages()
    session_id = _ensure_chat_session(context.get("chat_mode", "General Chat"), context.get("label", ""))
    session = get_chat_session(st.session_state.get("user_id"), session_id)
    if session and (session["title"] or "New Chat") == "New Chat" and not messages:
        update_chat_session_title(
            st.session_state.get("user_id"),
            session_id,
            _generate_chat_title(question),
        )
    timestamp = _message_timestamp()
    user_message = {
            "role": "user",
            "content": question,
            "timestamp": timestamp,
            "mode": context.get("badge", context.get("label", "General Chat")),
            "subject_id": context.get("subject_id"),
            "document_id": context.get("document_ids", [None])[0] if context.get("document_ids") else None,
            "attachments": [
                {
                    "id": attachment["id"],
                    "file_name": attachment["file_name"],
                    "file_type": attachment["file_type"],
                    "file_size": attachment["file_size"],
                    "warning": attachment.get("warning", ""),
                }
                for attachment in attachments
            ],
            "context": context,
            "created_at": timestamp,
        }
    assistant_message = {
            "role": "assistant",
            "content": answer_data["answer"],
            "timestamp": _message_timestamp(),
            "mode": context.get("badge", context.get("label", "General Chat")),
            "subject_id": context.get("subject_id"),
            "document_id": context.get("document_ids", [None])[0] if context.get("document_ids") else None,
            "sources": answer_data["sources"],
            "warning": answer_data["warning"],
            "source_count": answer_data["source_count"],
            "context": context,
            "suggestions": answer_data.get("suggestions", []),
            "created_at": _message_timestamp(),
        }
    messages.append(user_message)
    messages.append(assistant_message)
    user_message_id = _persist_chat_message(user_message)
    if user_message_id and attachments:
        attach_chat_attachments_to_message(
            st.session_state.get("user_id"),
            session_id,
            [attachment["id"] for attachment in attachments],
            user_message_id,
        )
    _persist_chat_message(assistant_message)


def add_assistant_message(answer_data, context):
    """Append only an assistant response, used when regenerating."""
    assistant_message = {
            "role": "assistant",
            "content": answer_data["answer"],
            "timestamp": _message_timestamp(),
            "mode": context.get("badge", context.get("label", "General Chat")),
            "subject_id": context.get("subject_id"),
            "document_id": context.get("document_ids", [None])[0] if context.get("document_ids") else None,
            "sources": answer_data["sources"],
            "warning": answer_data["warning"],
            "source_count": answer_data["source_count"],
            "context": context,
            "suggestions": answer_data.get("suggestions", []),
            "created_at": _message_timestamp(),
        }
    _chat_messages().append(assistant_message)
    _persist_chat_message(assistant_message)


def _compact_chat_history(limit=8):
    """Return a compact recent chat history for tutor continuity."""
    recent_messages = st.session_state.get(_chat_messages_key(), [])[-limit:]
    lines = []
    for message in recent_messages:
        role = "Student" if message.get("role") == "user" else "Tutor"
        content = str(message.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content[:900]}")
    return "\n".join(lines)


def _memory_enabled():
    """Return whether memory is active for this browser session."""
    return bool(st.session_state.get("memory_enabled", True))


def _memory_profile_text():
    """Return prompt-ready memory lines for this user."""
    if hasattr(ai_engine, "format_user_memory_profile"):
        return ai_engine.format_user_memory_profile(st.session_state.get("user_id"))
    return "No saved user memories."


def _memory_display_name():
    """Return preferred memory name or the account display name."""
    if hasattr(ai_engine, "get_memory_display_name"):
        return ai_engine.get_memory_display_name(
            st.session_state.get("user_id"),
            get_current_user_display_name(),
        )
    return get_current_user_display_name()


def _extract_memories_from_prompt(prompt):
    """Save useful user preferences from a prompt, never secrets or raw notes."""
    if not _memory_enabled() or not hasattr(ai_engine, "extract_user_memories_from_message"):
        return []
    return ai_engine.extract_user_memories_from_message(
        st.session_state.get("user_id"),
        prompt,
    )


def _chat_group_label(updated_at):
    """Group chat sessions into friendly date buckets."""
    try:
        updated = datetime.fromisoformat(str(updated_at).replace("Z", "").split(".")[0])
    except Exception:
        return "Older"
    today = datetime.now().date()
    if updated.date() == today:
        return "Today"
    if updated.date() == today - timedelta(days=1):
        return "Yesterday"
    if updated.date() >= today - timedelta(days=7):
        return "Previous 7 Days"
    return "Older"


def _format_chat_updated_at(updated_at):
    """Format a chat timestamp for a compact one-line history card."""
    try:
        updated = datetime.fromisoformat(str(updated_at).replace("Z", "").split(".")[0])
    except Exception:
        return "Updated recently"

    today = datetime.now().date()
    time_label = updated.strftime("%I:%M %p").lstrip("0")
    if updated.date() == today:
        return f"Today, {time_label}"
    if updated.date() == today - timedelta(days=1):
        return f"Yesterday, {time_label}"
    return updated.strftime("%b %d, %I:%M %p").replace(" 0", " ")


def render_chat_history_panel():
    """Render a compact left-side ChatGPT-style history manager."""
    st.markdown(
        """
        <div class="chat-history-heading">
            <span>Chat History</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(height=620, border=True):
        if st.button("Hide History", use_container_width=True, key="hide_chat_history"):
            st.session_state.show_chat_history_panel = False
            st.rerun()

        if st.button("New Chat", type="primary", use_container_width=True, key="history_new_chat"):
            _start_new_chat_session(
                st.session_state.get("study_chat_mode_selector", "General Chat"),
                "New Chat",
            )
            st.session_state.study_chat_last_question = ""
            st.session_state.study_chat_last_request = None
            st.session_state.study_chat_teach_context = {}
            st.session_state.study_chat_pending_prompt = ""
            st.rerun()

        search = st.text_input(
            "Search chats",
            placeholder="Search by title",
            key="chat_history_search",
        )
        sessions = get_chat_sessions(user_id, limit=40, search=search)
        active_id = _active_chat_session_id()

        if not sessions:
            st.info("No saved chats yet.")
            return

        current_group = None
        for session in sessions:
            group = _chat_group_label(session["updated_at"])
            if group != current_group:
                current_group = group
                st.markdown(
                    f"<div class='history-group-label'>{html.escape(group)}</div>",
                    unsafe_allow_html=True,
                )

            is_active = session["id"] == active_id
            title = session["title"] or "New Chat"
            mode = session["chat_mode"] or "General Chat"
            mode_short = {
                "General Chat": "General",
                "Chat with Subject": "Subject",
                "Chat with Specific Notes": "Note",
                "Chat with Multiple Notes": "Notes",
                "Teach Me Mode": "Teach Me",
            }.get(mode, "Chat")
            active_class = " active" if is_active else ""
            updated_label = _format_chat_updated_at(session["updated_at"])

            st.markdown(
                f"""
                <div class="history-card{active_class}">
                    <div class="history-card-main">
                        <span class="history-mode-badge">{html.escape(mode_short)}</span>
                        <span class="history-title" title="{html.escape(title)}">{html.escape(title)}</span>
                    </div>
                    <div class="history-meta">Updated: {html.escape(updated_label)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            item_col, more_col = st.columns([0.84, 0.16], gap="small")
            with item_col:
                open_label = "Open active chat" if is_active else "Open chat"
                if st.button(
                    open_label,
                    key=f"open_chat_{session['id']}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    _request_chat_session_load(session["id"])
                    st.rerun()

            with more_col:
                action_container = st.popover("⋮") if hasattr(st, "popover") else st.expander("⋮", expanded=False)
                with action_container:
                    new_title = st.text_input(
                        "Rename chat",
                        value=title,
                        key=f"rename_chat_{session['id']}",
                    )
                    if st.button("Save Name", key=f"save_chat_name_{session['id']}", use_container_width=True):
                        if update_chat_session_title(user_id, session["id"], new_title):
                            st.success("Chat renamed.")
                            st.rerun()
                        else:
                            st.error("Could not rename this chat.")

                    pending_key = f"confirm_delete_chat_{session['id']}"
                    if st.session_state.get(pending_key):
                        st.warning("Delete this chat? This action cannot be undone.")
                        confirm_col, cancel_col = st.columns(2)
                        with confirm_col:
                            if st.button("Delete", key=f"delete_chat_yes_{session['id']}", use_container_width=True):
                                deleted_active = session["id"] == active_id
                                if delete_chat_session(user_id, session["id"]):
                                    st.session_state.pop(pending_key, None)
                                    if deleted_active:
                                        st.session_state.pop(_active_chat_session_key(), None)
                                        _set_chat_messages([])
                                    st.success("Chat deleted.")
                                    st.rerun()
                                else:
                                    st.error("Could not delete this chat.")
                        with cancel_col:
                            if st.button("Cancel", key=f"delete_chat_no_{session['id']}", use_container_width=True):
                                st.session_state.pop(pending_key, None)
                                st.rerun()
                    else:
                        if st.button("Delete Chat", key=f"delete_chat_{session['id']}", use_container_width=True):
                            st.session_state[pending_key] = True
                            st.rerun()
            st.markdown("<div class='history-card-spacer'></div>", unsafe_allow_html=True)


def _demo_teach_response(
    topic,
    learning_level,
    language_style,
    teaching_depth,
    notes_context="",
    user_message="",
    first_lesson=False,
):
    """Return a useful teaching template when Demo Mode is selected."""
    source_note = (
        "I found relevant uploaded note chunks and I am using them as the lesson base."
        if notes_context
        else "I could not find this directly in your uploaded notes, so I'm teaching it using general academic knowledge."
    )

    if not first_lesson:
        return f"""
{source_note}

## Tutor Feedback
I read your message: **{user_message or 'your follow-up'}**.

### What you are doing well
- You are continuing the lesson instead of just memorizing.
- You are focusing on **{topic}**, which helps build concept clarity.

### Improved Explanation
Let's simplify **{topic}** again:

```text
Main idea -> Why it matters -> Example -> Practice
```

For **{learning_level}**, explain the topic in this order:

| Step | What to say |
|---|---|
| 1 | Define the topic in one simple line |
| 2 | Explain the purpose |
| 3 | Give one example |
| 4 | Mention one common mistake |

### Mini Example
If the topic feels hard, connect it to a small real-life example first, then
write the academic version.

### Quick Check
Now answer in one or two lines: what is the main purpose of **{topic}**?

### Next Suggestions
- Explain again more simply
- Give me a real-life example
- Ask me a question
- Give exam-style answer
- Test me like viva

Demo Mode is active, so this is a basic offline tutor response.
"""

    return f"""
{source_note}

## 1. Topic Roadmap
- Understand what **{topic}** means.
- Break it into simple parts.
- See one easy example.
- Practice with a quick check question.

## 2. Simple Meaning
{topic} is an important study concept. In **{language_style}**, start by asking:
what problem does this topic solve, and where do we use it?

## 3. Concept Breakdown
| Part | What to learn |
|---|---|
| Definition | Basic meaning |
| Steps | How it works |
| Example | How to apply it |
| Mistakes | What to avoid |

## 4. Visual Explanation
```text
Topic -> Meaning -> Steps -> Example -> Practice
```

## 5. Real-Life Example
Think of this topic like organizing a messy study desk: first identify the problem,
then arrange things step by step.

## 6. Academic / Exam Explanation
For **{learning_level}**, write a clear definition, explain the main points, and add
one relevant example.

## 7. Important Points
- Learn the definition.
- Understand the purpose.
- Practice examples.
- Avoid memorizing without meaning.

## 8. Common Mistakes
- Skipping the basic definition.
- Mixing similar concepts.
- Not practicing examples.

## 9. Quick Check Question
In your own words, what is the main purpose of **{topic}**?

## 10. Follow-up Suggestions
- Explain again more simply
- Give me a real-life example
- Ask me a question
- Give exam-style answer
- Show a diagram

Demo Mode is active, so this is a basic offline teaching template.
"""


def build_teach_me_prompt(
    user_name,
    topic,
    learning_level,
    language_style,
    teaching_depth,
    notes_context,
    attachment_context,
    chat_history,
    user_memory,
    user_message,
    context_label,
    first_lesson=False,
):
    """Build the tutor prompt for Teach Me Mode."""
    notes_instruction = (
        f"Uploaded notes context is available ({context_label}). Use it first."
        if notes_context
        else (
            "No uploaded notes context is available. Clearly say: "
            "\"I could not find this directly in your uploaded notes, so I'm teaching it using general academic knowledge.\""
        )
    )
    depth_instruction = {
        "Quick": "Keep it concise but still useful.",
        "Balanced": "Use a medium-length explanation with examples and a quick check.",
        "Deep Explanation": "Give a detailed, step-by-step explanation with visuals, examples, mistakes, and practice.",
    }.get(teaching_depth, "Use a balanced explanation.")

    if first_lesson:
        response_structure = """
For the first lesson response, use exactly these sections:
1. Topic Roadmap
2. Simple Meaning
3. Concept Breakdown
4. Visual Explanation
5. Real-Life Example
6. Academic / Exam Explanation
7. Important Points
8. Common Mistakes
9. Quick Check Question
10. Follow-up Suggestions
Use clean Markdown headings, bullets, and tables. For math or logic topics,
use formulas, truth tables, ASCII diagrams, or step-by-step solving when useful.
"""
    else:
        response_structure = """
Continue the same lesson context. Detect whether the student is answering,
asking for an easier explanation, requesting an example, quiz, exam answer,
viva answer, next topic, or saying they do not understand. If they answered a
question, give feedback, mention what is correct/missing, improve the answer,
and ask the next question.
"""

    return f"""
You are {user_name}'s AI Study Tutor inside StudyMate AI. You teach like a
patient expert teacher. Your job is not only to answer, but to make the student
understand deeply. Use uploaded notes when available, but if notes do not cover
the topic, clearly say so and continue using general academic knowledge.
Explain step-by-step, use visuals, examples, tables, formulas, logical
breakdowns, and ask follow-up questions. Keep the explanation student-friendly,
exam-focused, and concept-based.

Student name: {user_name}
Topic: {topic}
Learning level: {learning_level}
Language style: {language_style}
Teaching depth: {teaching_depth}
Depth instruction: {depth_instruction}
Notes instruction: {notes_instruction}

Saved student memory and preferences:
{user_memory or "No saved user memories."}

Recent lesson history:
{chat_history or "No previous lesson messages yet."}

Uploaded notes context:
{notes_context or "No relevant note chunks selected."}

Attached file context:
{attachment_context or "No files attached to this message."}

Student message:
{user_message}

{response_structure}

Always include a Quick Check question unless the student specifically asks for
only a concise exam/viva answer. End with 3-5 follow-up suggestions as bullets.
"""


def _teach_suggestions():
    """Return default Teach Me Mode follow-up suggestions."""
    return DEFAULT_TEACH_SUGGESTIONS


def generate_teach_me_answer(question, context, first_lesson=False, attachment_context="", image_paths=None):
    """Generate a Teach Me Mode tutor response with optional notes context."""
    sources = []
    warning = ""
    material_source = context.get("material_source", "General Knowledge")
    should_retrieve = (
        material_source != "General Knowledge"
        and context.get("subject_id") is not None
    )

    if should_retrieve:
        try:
            sources = query_subject_notes(
                subject_id=context["subject_id"],
                question=f"{context.get('topic', '')} {question}",
                limit=7 if context.get("teaching_depth") == "Deep Explanation" else 5,
                document_ids=context.get("document_ids", []),
                user_id=st.session_state.get("user_id"),
            )
        except VectorStoreError as exc:
            warning = str(exc)

    notes_context = "\n\n".join(
        f"Source {index} ({source.get('metadata', {}).get('file_name', 'Uploaded note')}): {source['text']}"
        for index, source in enumerate(sources, start=1)
    )

    if should_retrieve and not sources and not warning:
        warning = (
            "I could not find this directly in your uploaded notes, "
            "so I'm teaching it using general academic knowledge."
        )

    provider = get_provider_label()
    if provider == "Demo Mode":
        if attachment_context:
            answer = f"""
Demo Mode response: I received your attachment(s).

## What I found in the attachment
{attachment_context[:1400]}

## Placeholder answer
Connect Gemini or Ollama to get a full multimodal tutor response.
"""
        else:
            answer = _demo_teach_response(
                context.get("topic", "this topic"),
                context.get("learning_level", "Normal"),
                context.get("language_style", "Simple English"),
                context.get("teaching_depth", "Balanced"),
                notes_context=notes_context,
                user_message=question,
                first_lesson=first_lesson,
            )
    else:
        prompt = build_teach_me_prompt(
            user_name=_memory_display_name(),
            topic=context.get("topic", "this topic"),
            learning_level=context.get("learning_level", "Normal"),
            language_style=context.get("language_style", "Simple English"),
            teaching_depth=context.get("teaching_depth", "Balanced"),
            notes_context=notes_context,
            attachment_context=attachment_context,
            chat_history=_compact_chat_history(10),
            user_memory=_memory_profile_text(),
            user_message=question,
            context_label=context.get("source_label", context.get("label", "Teach Me Mode")),
            first_lesson=first_lesson,
        )
        try:
            attachment_has_text = _attachment_context_has_text(attachment_context)
            provider_label = get_provider_label()
            if attachment_context and not attachment_has_text and not image_paths:
                answer = _provider_cannot_read_attachment_response()
            elif image_paths and _is_gemini_provider(provider_label):
                try:
                    answer = ai_engine.ask_gemini_multimodal(prompt, image_paths=image_paths)
                except Exception:
                    if attachment_has_text:
                        answer = ai_engine.ask_ai(prompt)
                    else:
                        raise
            elif image_paths and _is_openai_provider(provider_label):
                try:
                    answer = ai_engine.generate_with_openai_multimodal(prompt, image_paths=image_paths)
                except Exception:
                    if attachment_has_text:
                        answer = ai_engine.ask_ai(prompt)
                    else:
                        raise
            elif image_paths and not _provider_supports_vision(provider_label) and not attachment_has_text:
                answer = _provider_cannot_read_attachment_response()
            else:
                answer = ai_engine.ask_ai(prompt)
        except Exception as exc:
            if hasattr(ai_engine, "safe_ai_error_message"):
                answer = ai_engine.safe_ai_error_message(exc)
            else:
                answer = "The selected AI provider could not complete the lesson."

    return {
        "answer": answer,
        "sources": sources,
        "warning": warning,
        "source_count": len(sources),
        "suggestions": _teach_suggestions(),
    }


def generate_chat_answer(question, answer_style, chat_mode, context, attachment_context="", image_paths=None):
    """
    Generate a chatbot response with a compatibility fallback.

    Streamlit Cloud can occasionally keep an older imported module in memory
    after a deploy. This wrapper prevents a hard crash if ai_engine is stale.
    """
    if chat_mode == "Teach Me Mode":
        return generate_teach_me_answer(
            question=question,
            context=context,
            first_lesson=context.get("first_lesson", False),
            attachment_context=attachment_context,
            image_paths=image_paths,
        )

    if hasattr(ai_engine, "generate_study_chat_response"):
        return ai_engine.generate_study_chat_response(
            question=question,
            answer_style=answer_style,
            chat_mode=chat_mode,
            subject_id=context["subject_id"],
            document_ids=context["document_ids"],
            context_label=context["label"],
            user_id=st.session_state.get("user_id"),
            chat_history=_compact_chat_history(10),
            user_memory=_memory_profile_text(),
            attachment_context=attachment_context,
            image_paths=image_paths,
        )

    if chat_mode != "General Chat" and context["subject_id"] is not None:
        return ai_engine.chat_with_notes(
            subject_id=context["subject_id"],
            question=question,
            answer_style=answer_style,
            user_id=st.session_state.get("user_id"),
        )

    prompt = f"""
You are {_memory_display_name()}'s AI Study Assistant.
Answer this student question clearly and in a study-friendly way.
Answer style: {answer_style}

Saved student memory and preferences:
{_memory_profile_text()}

Recent conversation:
{_compact_chat_history(10) or "No previous messages in this chat."}

Attached file context:
{attachment_context or "No files attached to this message."}

Question:
{question}
"""
    try:
        attachment_has_text = _attachment_context_has_text(attachment_context)
        provider_label = get_provider_label()
        if attachment_context and not attachment_has_text and not image_paths:
            answer = _provider_cannot_read_attachment_response()
        elif image_paths and _is_gemini_provider(provider_label):
            try:
                answer = ai_engine.ask_gemini_multimodal(prompt, image_paths=image_paths)
            except Exception:
                if attachment_has_text:
                    answer = ai_engine.ask_ai(prompt)
                else:
                    raise
        elif image_paths and _is_openai_provider(provider_label):
            try:
                answer = ai_engine.generate_with_openai_multimodal(prompt, image_paths=image_paths)
            except Exception:
                if attachment_has_text:
                    answer = ai_engine.ask_ai(prompt)
                else:
                    raise
        elif image_paths and not _provider_supports_vision(provider_label) and not attachment_has_text:
            answer = _provider_cannot_read_attachment_response()
        else:
            answer = ai_engine.ask_ai(prompt)
    except Exception as exc:
        if hasattr(ai_engine, "safe_ai_error_message"):
            answer = ai_engine.safe_ai_error_message(exc)
        else:
            answer = "The selected AI provider could not complete the request."

    return {
        "answer": answer,
        "sources": [],
        "warning": "",
        "source_count": 0,
    }


def build_context(chat_mode, selected_subject, selected_documents):
    """Create the retrieval settings used by the AI engine."""
    subject_id = selected_subject["id"] if selected_subject else None
    document_ids = [document["id"] for document in selected_documents]

    if chat_mode == "Teach Me Mode":
        return dict(st.session_state.get("study_chat_teach_context", {}))

    if chat_mode == "General Chat":
        return {
            "subject_id": None,
            "document_ids": [],
            "label": "General Chat",
            "badge": MODE_BADGES[chat_mode],
        }

    if chat_mode == "Chat with Subject":
        if not selected_subject:
            return {
                "subject_id": None,
                "document_ids": [],
                "label": "No subject selected",
                "badge": MODE_BADGES[chat_mode],
            }

        return {
            "subject_id": subject_id,
            "document_ids": [],
            "label": f"Subject: {selected_subject['name']}",
            "badge": MODE_BADGES[chat_mode],
        }

    if chat_mode == "Chat with Specific Notes":
        if not selected_subject:
            return {
                "subject_id": None,
                "document_ids": [],
                "label": "No subject selected",
                "badge": MODE_BADGES[chat_mode],
            }

        document_name = selected_documents[0]["file_name"] if selected_documents else "Selected note"
        return {
            "subject_id": subject_id,
            "document_ids": document_ids,
            "label": f"Note: {document_name}",
            "badge": MODE_BADGES[chat_mode],
        }

    if not selected_subject:
        return {
            "subject_id": None,
            "document_ids": [],
            "label": "No subject selected",
            "badge": MODE_BADGES[chat_mode],
        }

    return {
        "subject_id": subject_id,
        "document_ids": document_ids,
        "label": f"{len(document_ids)} selected notes",
        "badge": MODE_BADGES[chat_mode],
    }


st.set_page_config(page_title="Chat With Notes - StudyMate AI", layout="wide")
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

st.markdown(
    """
    <style>
        .chat-shell-title {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 4px 0 16px 0;
        }
        .chat-shell-icon {
            width: 42px;
            height: 42px;
            display: grid;
            place-items: center;
            border-radius: 16px;
            background: linear-gradient(135deg, #e9f7ff, #f0e8ff);
            box-shadow: 0 10px 28px rgba(47, 125, 246, 0.12);
            font-size: 1.2rem;
        }
        .chat-shell-title h1 {
            margin: 0;
            font-size: clamp(1.65rem, 2.6vw, 2.35rem);
            line-height: 1.1;
            color: var(--sm-ink);
            letter-spacing: 0;
        }
        .chat-shell-title p {
            margin: 4px 0 0 0;
            color: var(--sm-muted);
            font-weight: 600;
        }
        .chat-history-heading {
            display: flex;
            justify-content: space-between;
            align-items: end;
            margin: 4px 0 8px 0;
            color: var(--sm-ink);
            font-weight: 900;
            font-size: 1.05rem;
        }
        .history-group-label {
            margin: 14px 0 7px 2px;
            color: var(--sm-muted);
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.02em;
            text-transform: uppercase;
        }
        .history-card {
            min-height: 58px;
            padding: 10px 11px;
            border: 1px solid rgba(148, 163, 184, 0.26);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.92);
            box-shadow: 0 8px 24px rgba(17, 25, 54, 0.045);
        }
        .history-card.active {
            border-color: rgba(20, 184, 180, 0.42);
            background: linear-gradient(135deg, rgba(224, 255, 251, 0.95), rgba(242, 235, 255, 0.95));
            box-shadow: 0 10px 28px rgba(20, 184, 180, 0.11);
        }
        .history-card-main {
            display: flex;
            align-items: center;
            gap: 7px;
            min-width: 0;
            width: 100%;
        }
        .history-title {
            color: var(--sm-ink);
            font-weight: 850;
            line-height: 1.2;
            font-size: 0.92rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            min-width: 0;
        }
        .history-mode-badge {
            display: inline-flex;
            align-items: center;
            flex-shrink: 0;
            max-width: 74px;
            padding: 3px 7px;
            border-radius: 999px;
            background: rgba(20, 184, 180, 0.11);
            color: #0f766e;
            font-size: 0.66rem;
            font-weight: 900;
            line-height: 1;
            white-space: nowrap;
        }
        .history-meta {
            color: var(--sm-muted);
            font-size: 0.72rem;
            font-weight: 700;
            margin-top: 7px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .history-card.active .history-title {
            color: #155e75;
        }
        .history-card-spacer {
            height: 8px;
        }
        div[data-testid="stChatMessage"] {
            border-radius: 18px;
        }
        @media (max-width: 900px) {
            .chat-shell-title { align-items: flex-start; }
            .chat-shell-title h1 { font-size: 1.55rem; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

_chat_messages()
_ensure_chat_session()
if "study_chat_last_question" not in st.session_state:
    st.session_state.study_chat_last_question = ""
if "study_chat_last_request" not in st.session_state:
    st.session_state.study_chat_last_request = None
if "study_chat_teach_context" not in st.session_state:
    st.session_state.study_chat_teach_context = {}
if "study_chat_pending_prompt" not in st.session_state:
    st.session_state.study_chat_pending_prompt = ""
if "chat_attachment_uploader_key" not in st.session_state:
    st.session_state.chat_attachment_uploader_key = 0
if "voice_audio_uploader_key" not in st.session_state:
    st.session_state.voice_audio_uploader_key = 0
if "voice_transcript_text" not in st.session_state:
    st.session_state.voice_transcript_text = ""
if "voice_pending_audio" not in st.session_state:
    st.session_state.voice_pending_audio = None
if "voice_transcription_status" not in st.session_state:
    st.session_state.voice_transcription_status = None
if "show_chat_history_panel" not in st.session_state:
    st.session_state.show_chat_history_panel = True

pending_session_load = st.session_state.pop("study_chat_pending_session_load", None)
loaded_session_from_history = False
if pending_session_load:
    loaded_session_from_history = _load_chat_session(pending_session_load)

subjects = get_subjects(user_id=user_id)
prefill_subject_id = st.session_state.pop("chat_prefill_subject_id", None)
prefill_document_id = st.session_state.pop("chat_prefill_document_id", None)
prefill_document_ids = st.session_state.pop("chat_prefill_document_ids", [])
prefill_question = st.session_state.pop("chat_prefill_question", "")

if st.session_state.show_chat_history_panel:
    history_col, chat_col = st.columns([0.24, 0.76], gap="medium")
    with history_col:
        render_chat_history_panel()
else:
    chat_col = st.container()

with chat_col:
    if not st.session_state.show_chat_history_panel:
        if st.button("Show Chat History", use_container_width=False):
            st.session_state.show_chat_history_panel = True
            st.rerun()

    st.markdown(
        """
        <div class="chat-shell-title">
            <div class="chat-shell-icon">AI</div>
            <div>
                <h1>Chat With Notes</h1>
                <p>Ask from your notes, attachments, voice, or general study knowledge.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    section_title("Chat Settings", "\u2699\ufe0f")
    with st.container(border=True):
        top_col1, top_col2, top_col3 = st.columns([1.2, 1.2, 1])

        with top_col1:
            default_mode_index = 0
            if not loaded_session_from_history and prefill_document_id:
                st.session_state.study_chat_mode_selector = "Chat with Specific Notes"
            elif not loaded_session_from_history and prefill_subject_id:
                st.session_state.study_chat_mode_selector = "Chat with Subject"
            elif st.session_state.get("study_chat_mode_selector") not in CHAT_MODES:
                st.session_state.study_chat_mode_selector = CHAT_MODES[default_mode_index]
            chat_mode = st.selectbox(
                "Chat mode",
                CHAT_MODES,
                index=default_mode_index,
                key="study_chat_mode_selector",
            )

        with top_col2:
            answer_style = st.selectbox("Answer style", ANSWER_STYLES)

        with top_col3:
            st.markdown(
                f"<span class='status-pill'>{MODE_BADGES[chat_mode]}</span>",
                unsafe_allow_html=True,
            )
            st.caption(f"AI provider: {get_provider_label()}")
            memory_label = "On" if _memory_enabled() else "Off"
            st.caption(f"Memory: {memory_label}")

        selected_subject = None
        selected_documents = []
        subject_documents = []

        if chat_mode not in {"General Chat", "Teach Me Mode"}:
            if not subjects:
                st.warning("Create a subject or switch to General Chat.")
            else:
                subject_names = [subject["name"] for subject in subjects]
                subject_index = get_subject_index(subjects, prefill_subject_id)
                selected_subject_name = st.selectbox(
                    "Subject",
                    subject_names,
                    index=subject_index,
                )
                selected_subject = next(
                    subject for subject in subjects if subject["name"] == selected_subject_name
                )
                subject_documents = list(
                    get_documents_by_subject(selected_subject["id"], user_id=user_id)
                )

                if chat_mode in {"Chat with Specific Notes", "Chat with Multiple Notes"}:
                    if not subject_documents:
                        st.warning("No uploaded documents found for this subject yet.")
                    else:
                        document_options = {
                            f"{document['file_name']} ({document['chunk_count']} chunks)": document
                            for document in subject_documents
                        }

                        if chat_mode == "Chat with Specific Notes":
                            labels = list(document_options.keys())
                            default_doc_index = 0
                            if prefill_document_id:
                                for index, label in enumerate(labels):
                                    if document_options[label]["id"] == prefill_document_id:
                                        default_doc_index = index
                                        break

                            selected_label = st.selectbox(
                                "Selected note",
                                labels,
                                index=default_doc_index,
                            )
                            selected_documents = [document_options[selected_label]]
                        else:
                            default_labels = [
                                label
                                for label, document in document_options.items()
                                if document["id"] in prefill_document_ids
                            ] or list(document_options.keys())[:2]
                            selected_labels = st.multiselect(
                                "Selected notes",
                                list(document_options.keys()),
                                default=default_labels,
                            )
                            selected_documents = [
                                document_options[label] for label in selected_labels
                            ]

        action_col1, action_col2 = st.columns([1, 1])
        with action_col1:
            if st.button("New Chat", use_container_width=True):
                _start_new_chat_session(chat_mode, "New Chat")
                st.session_state.study_chat_last_question = ""
                st.session_state.study_chat_last_request = None
                st.session_state.study_chat_teach_context = {}
                st.session_state.study_chat_pending_prompt = ""
                st.rerun()
        with action_col2:
            if st.button("Regenerate Last Answer", use_container_width=True):
                if st.session_state.study_chat_last_question:
                    st.session_state.study_chat_regenerate = True
                    st.rerun()
                else:
                    st.info("Ask a question first, then regenerate.")

    if chat_mode == "Teach Me Mode":
        section_title("Tutor Setup", "\U0001f9d1\u200d\U0001f3eb")
        with st.container(border=True):
            tutor_col1, tutor_col2 = st.columns(2)
            with tutor_col1:
                teach_material = st.selectbox("Material selector", TEACH_MATERIAL_OPTIONS)
            with tutor_col2:
                teach_subject = None
                teach_subject_documents = []
                if teach_material == "General Knowledge":
                    st.selectbox("Subject (optional)", ["No subject selected"], disabled=True)
                elif not subjects:
                    st.selectbox("Subject", ["Create a subject first"], disabled=True)
                    st.warning("Create a subject or choose General Knowledge.")
                else:
                    teach_subject_name = st.selectbox(
                        "Subject",
                        [subject["name"] for subject in subjects],
                        key="teach_subject_selector",
                    )
                    teach_subject = next(
                        subject for subject in subjects if subject["name"] == teach_subject_name
                    )
                    teach_subject_documents = list(
                        get_documents_by_subject(teach_subject["id"], user_id=user_id)
                    )

            teach_selected_documents = []
            if teach_material in {"Specific Note", "Multiple Notes"} and teach_subject:
                if not teach_subject_documents:
                    st.warning("No uploaded documents found for this subject yet.")
                else:
                    teach_document_options = {
                        f"{document['file_name']} ({document['chunk_count']} chunks)": document
                        for document in teach_subject_documents
                    }
                    if teach_material == "Specific Note":
                        teach_label = st.selectbox(
                            "Specific note",
                            list(teach_document_options.keys()),
                            key="teach_specific_note",
                        )
                        teach_selected_documents = [teach_document_options[teach_label]]
                    else:
                        teach_labels = st.multiselect(
                            "Multiple notes",
                            list(teach_document_options.keys()),
                            default=list(teach_document_options.keys())[:2],
                            key="teach_multiple_notes",
                        )
                        teach_selected_documents = [
                            teach_document_options[label] for label in teach_labels
                        ]

            topic = st.text_input(
                "Topic",
                placeholder="Example: Database Normalization, K-map, Polymorphism, Probability",
                key="teach_topic",
            )
            level_col, language_col, depth_col = st.columns(3)
            with level_col:
                learning_level = st.selectbox("Learning level", LEARNING_LEVELS)
            with language_col:
                language_style = st.selectbox("Language style", LANGUAGE_STYLES)
            with depth_col:
                teaching_depth = st.selectbox("Teaching depth", TEACHING_DEPTHS, index=1)

            source_label = teach_material
            if teach_material == "Whole Subject Notes" and teach_subject:
                source_label = f"Whole Subject Notes: {teach_subject['name']}"
            elif teach_material == "Specific Note" and teach_selected_documents:
                source_label = f"Specific Note: {teach_selected_documents[0]['file_name']}"
            elif teach_material == "Multiple Notes" and teach_selected_documents:
                source_label = f"Multiple Notes: {len(teach_selected_documents)} selected"

            st.markdown(
                f"""
                <span class='status-pill'>Teach Me Mode</span>
                <span class='status-pill'>Topic: {html.escape(topic.strip() or 'Not started')}</span>
                <span class='status-pill'>Level: {html.escape(learning_level)}</span>
                <span class='status-pill'>Language: {html.escape(language_style)}</span>
                <span class='status-pill'>Source: {html.escape(source_label)}</span>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "Start Lesson",
                type="primary",
                key="start_teach_lesson",
                use_container_width=True,
            ):
                clean_topic = topic.strip()
                if not clean_topic:
                    st.warning("Enter a topic first.")
                    st.stop()
                if teach_material != "General Knowledge" and not teach_subject:
                    st.warning("Select a subject or choose General Knowledge.")
                    st.stop()
                if teach_material == "Specific Note" and not teach_selected_documents:
                    st.warning("Select one uploaded note first.")
                    st.stop()
                if teach_material == "Multiple Notes" and not teach_selected_documents:
                    st.warning("Select at least one uploaded note first.")
                    st.stop()

                teach_context = {
                    "subject_id": teach_subject["id"] if teach_subject else None,
                    "document_ids": [document["id"] for document in teach_selected_documents],
                    "label": f"Teach Me: {clean_topic}",
                    "badge": "Teach Me Mode",
                    "chat_mode": "Teach Me Mode",
                    "topic": clean_topic,
                    "material_source": teach_material,
                    "learning_level": learning_level,
                    "language_style": language_style,
                    "teaching_depth": teaching_depth,
                    "source_label": source_label,
                    "first_lesson": True,
                }
                request_context = dict(teach_context)
                active_context = dict(teach_context)
                active_context["first_lesson"] = False
                st.session_state.study_chat_teach_context = active_context
                start_prompt = f"Start teaching me {clean_topic}."
                st.session_state.study_chat_last_question = start_prompt
                st.session_state.study_chat_last_request = {
                    "question": start_prompt,
                    "answer_style": language_style,
                    "chat_mode": chat_mode,
                    "context": request_context,
                }
                loading_slot = st.empty()
                with loading_slot:
                    render_ai_loading("StudyMate Tutor is preparing your lesson")
                try:
                    answer_data = generate_chat_answer(
                        question=start_prompt,
                        answer_style=language_style,
                        chat_mode=chat_mode,
                        context=request_context,
                    )
                finally:
                    loading_slot.empty()
                add_chat_pair(start_prompt, answer_data, active_context)
                st.rerun()

    context = build_context(chat_mode, selected_subject, selected_documents)
    context["chat_mode"] = chat_mode

    with st.container(border=True):
        recent_count = min(len(_chat_messages()), 10)
        st.markdown(
            f"""
            <span class='status-pill'>Memory: {'On' if _memory_enabled() else 'Off'}</span>
            <span class='status-pill'>Mode: {html.escape(chat_mode)}</span>
            <span class='status-pill'>Context: {html.escape(context.get('label', 'General Chat'))}</span>
            <span class='status-pill'>Recent messages used: {recent_count}</span>
            """,
            unsafe_allow_html=True,
        )

    if prefill_question:
        st.info(f"Suggested question from Study Library: {prefill_question}")
        if st.button("Ask Suggested Question", type="primary", use_container_width=True):
            _extract_memories_from_prompt(prefill_question)
            st.session_state.study_chat_last_question = prefill_question
            st.session_state.study_chat_last_request = {
                "question": prefill_question,
                "answer_style": answer_style,
                "chat_mode": chat_mode,
                "context": context,
            }
            loading_slot = st.empty()
            with loading_slot:
                render_ai_loading("StudyMate is reading your selected material")
            try:
                answer_data = generate_chat_answer(
                    question=prefill_question,
                    answer_style=answer_style,
                    chat_mode=chat_mode,
                    context=context,
                )
            finally:
                loading_slot.empty()
            add_chat_pair(prefill_question, answer_data, context)
            st.rerun()

    section_title("Conversation", "\U0001f4ac")
    with st.container(height=540, border=True):
        messages = _chat_messages()
        if not messages:
            render_empty_state(
                "Ask anything about your notes, subjects, or studies.",
                "Use General Chat or choose a subject/note above, then type at the bottom.",
                "\U0001f4ad",
            )

        for message_index, message in enumerate(messages):
            avatar = "\U0001f468\u200d\U0001f393" if message["role"] == "user" else "\U0001f916"
            with st.chat_message(message["role"], avatar=avatar):
                message_context = message.get("context", {})
                if message_context:
                    st.caption(f"{message_context.get('badge', 'Chat')} | {message_context.get('label', '')}")
                if message.get("created_at"):
                    st.caption(message["created_at"])

                if message.get("warning"):
                    st.warning(message["warning"])

                render_ai_markdown(message["content"])
                render_message_attachments(message.get("attachments", []))

                if message["role"] == "assistant":
                    source_count = message.get("source_count", 0)
                    if source_count:
                        st.caption(f"Using {source_count} relevant note chunks")
                    render_sources(message.get("sources", []))
                    if message_context.get("badge") == "Teach Me Mode":
                        render_follow_up_suggestions(
                            message_index,
                            message.get("suggestions", []),
                        )

    if st.session_state.get("study_chat_regenerate"):
        st.session_state.study_chat_regenerate = False
        messages = _chat_messages()
        if messages and messages[-1]["role"] == "assistant":
            messages.pop()

        last_request = st.session_state.study_chat_last_request
        if last_request:
            loading_slot = st.empty()
            with loading_slot:
                render_ai_loading("Regenerating a sharper answer")
            try:
                answer_data = generate_chat_answer(
                    question=last_request["question"],
                    answer_style=last_request["answer_style"],
                    chat_mode=last_request["chat_mode"],
                    context=last_request["context"],
                    attachment_context=last_request.get("attachment_context", ""),
                    image_paths=last_request.get("image_paths", []),
                )
            finally:
                loading_slot.empty()
            add_assistant_message(answer_data, last_request["context"])
        st.rerun()

    with st.expander("Voice Input", expanded=False):
        st.caption(
            "Speak clearly for 2-5 seconds, then click transcribe. Voice/audio may be sent to Gemini or OpenAI "
            "for transcription when your key is available."
        )
        recorded_audio = None
        if hasattr(st, "audio_input"):
            recorded_audio = st.audio_input(
                "Record voice",
                key=f"voice_recording_{st.session_state.voice_audio_uploader_key}",
                help="Short, clear recordings work best. Start with one sentence.",
            )
        else:
            st.info("Browser voice recording is not available in this Streamlit version. Upload an audio file instead.")

        uploaded_audio = st.file_uploader(
            "Upload audio file",
            type=["mp3", "wav", "m4a", "ogg", "webm"],
            key=f"voice_audio_upload_{st.session_state.voice_audio_uploader_key}",
            help="Supported: MP3, WAV, M4A, OGG, WEBM. Max 10 MB.",
        )

        selected_audio = recorded_audio or uploaded_audio
        if selected_audio:
            selected_audio_name = getattr(selected_audio, "name", "voice_recording.wav")
            selected_audio_type = getattr(selected_audio, "type", "") or mimetypes.guess_type(selected_audio_name)[0] or "audio/wav"
            selected_audio_size = getattr(selected_audio, "size", 0) or 0
            st.caption(
                f"Ready: {_attachment_icon(Path(selected_audio_name).suffix.replace('.', '').upper())} "
                f"{html.escape(selected_audio_name)} - {_format_size(selected_audio_size)}"
            )
            try:
                st.audio(selected_audio.getvalue(), format=selected_audio_type)
            except Exception:
                st.info("Audio received, but browser playback is not available for this file.")
            st.info(
                f"Audio received: yes | File type: {Path(selected_audio_name).suffix.replace('.', '').upper() or 'AUDIO'} "
                f"| File size: {_format_size(selected_audio_size)}"
            )
        else:
            st.caption("Audio received: no")

        voice_col1, voice_col2, voice_col3 = st.columns(3)
        with voice_col1:
            if st.button("Transcribe Audio", use_container_width=True):
                if not selected_audio:
                    st.warning("Record voice or upload an audio file first.")
                else:
                    active_session_id = _sync_active_chat_context(chat_mode, context)
                    attachment, warning = _audio_upload_to_attachment(selected_audio, active_session_id)
                    if attachment:
                        st.session_state.voice_pending_audio = {
                            "id": attachment["id"],
                            "file_name": attachment["file_name"],
                            "file_type": attachment["file_type"],
                            "file_size": attachment["file_size"],
                            "extracted_text": attachment.get("extracted_text", ""),
                            "extraction_method": attachment.get("extraction_method", ""),
                            "warning": attachment.get("warning", ""),
                        }
                        transcript_len = len(attachment.get("extracted_text", "") or "")
                        st.session_state.voice_transcription_status = {
                            "audio_received": "yes",
                            "file_type": attachment["file_type"],
                            "file_size": attachment["file_size"],
                            "method": attachment.get("extraction_method", "unavailable"),
                            "transcript_length": transcript_len,
                        }
                        st.session_state.voice_transcript_text = attachment.get("extracted_text", "")
                        if st.session_state.voice_transcript_text:
                            st.success("Transcription ready.")
                        else:
                            st.warning("No speech was detected. Please try again with clearer audio.")
                    if warning:
                        st.warning(warning)

        with voice_col2:
            if st.button("Clear", use_container_width=True):
                st.session_state.voice_pending_audio = None
                st.session_state.voice_transcript_text = ""
                st.session_state.voice_transcription_status = None
                st.session_state.voice_audio_uploader_key += 1
                st.rerun()

        with voice_col3:
            if st.button("Try Again", use_container_width=True):
                st.session_state.voice_pending_audio = None
                st.session_state.voice_transcript_text = ""
                st.session_state.voice_transcription_status = None
                st.session_state.voice_audio_uploader_key += 1
                st.rerun()

        if st.session_state.voice_transcription_status:
            status = st.session_state.voice_transcription_status
            st.info(
                " | ".join(
                    [
                        f"Audio received: {status.get('audio_received', 'yes')}",
                        f"File type: {status.get('file_type', 'AUDIO')}",
                        f"File size: {_format_size(status.get('file_size', 0))}",
                        f"Transcription method: {status.get('method', 'unavailable')}",
                        f"Transcript length: {status.get('transcript_length', 0)} characters",
                    ]
                )
            )

        if st.session_state.voice_pending_audio:
            transcript = st.text_area(
                "Edit transcribed text before sending",
                key="voice_transcript_text",
                height=120,
                placeholder="Your transcribed voice message will appear here.",
            )
            if not (transcript or "").strip():
                st.warning("No speech was detected. Please try again with clearer audio.")
            if st.button("Send to Chat", type="primary", use_container_width=True):
                clean_transcript, transcript_error = validate_chat_question(transcript, max_length=1200)
                if transcript_error:
                    st.warning(transcript_error)
                else:
                    st.session_state.study_chat_pending_prompt = clean_transcript
                    st.rerun()

    with st.expander("Attach files to next message", expanded=False):
        chat_uploaded_files = st.file_uploader(
            "Attach images, PDFs, DOCX, PPTX, TXT, or Markdown files",
            type=["png", "jpg", "jpeg", "webp", "pdf", "docx", "pptx", "txt", "md"],
            accept_multiple_files=True,
            key=f"chat_attachments_{st.session_state.chat_attachment_uploader_key}",
            help=(
                f"Up to {CHAT_MAX_ATTACHMENTS} files. Images up to 5 MB each; "
                "documents/PDF/PPTX up to 20 MB each."
            ),
        )
        if chat_uploaded_files:
            st.caption("Files ready for your next message:")
            for uploaded in chat_uploaded_files[:CHAT_MAX_ATTACHMENTS]:
                file_type = Path(uploaded.name).suffix.replace(".", "").upper()
                st.markdown(
                    f"{_attachment_icon(file_type)} **{html.escape(uploaded.name)}** "
                    f"`{html.escape(file_type)}` - {_format_size(getattr(uploaded, 'size', 0))}"
                )
            if len(chat_uploaded_files) > CHAT_MAX_ATTACHMENTS:
                st.warning(f"Only the first {CHAT_MAX_ATTACHMENTS} files will be sent.")
        else:
            st.caption("Upload Notes is for permanent Study Library files. Chat attachments are saved only with this chat.")

    pending_prompt = st.session_state.pop("study_chat_pending_prompt", "")
    typed_prompt = st.chat_input("Ask StudyMate anything... Follow-up questions are welcome.")
    prompt = pending_prompt or typed_prompt

    if prompt:
        clean_prompt, prompt_error = validate_chat_question(prompt)
        if prompt_error:
            st.warning(prompt_error)
            st.stop()

        saved_memories = _extract_memories_from_prompt(clean_prompt)
        if saved_memories:
            st.toast(f"Saved {len(saved_memories)} useful memory item(s).")

        if chat_mode == "Teach Me Mode":
            context = dict(st.session_state.get("study_chat_teach_context", {}))
            if not context:
                context = {
                    "subject_id": None,
                    "document_ids": [],
                    "label": f"Teach Me: {clean_prompt[:60]}",
                    "badge": "Teach Me Mode",
                    "chat_mode": "Teach Me Mode",
                    "topic": clean_prompt[:80],
                    "material_source": "General Knowledge",
                    "learning_level": "Normal",
                    "language_style": "Simple English",
                    "teaching_depth": "Balanced",
                    "source_label": "Voice/Text Prompt",
                    "first_lesson": False,
                }
                st.session_state.study_chat_teach_context = context
            context["first_lesson"] = False
        elif chat_mode != "General Chat" and not selected_subject:
            st.warning("Select a subject first, or switch to General Chat.")
            st.stop()

        if chat_mode == "Chat with Specific Notes" and not selected_documents:
            st.warning("Select one uploaded note first, or switch to General Chat.")
            st.stop()

        if chat_mode == "Chat with Multiple Notes" and not selected_documents:
            st.warning("Select at least one uploaded note first, or switch to General Chat.")
            st.stop()

        active_session_id = _sync_active_chat_context(chat_mode, context)
        processed_attachments, attachment_warnings = _save_and_process_chat_attachments(
            chat_uploaded_files,
            active_session_id,
        )
        pending_audio_attachment = st.session_state.get("voice_pending_audio")
        if pending_audio_attachment:
            processed_attachments.append(pending_audio_attachment)
        for attachment_warning in attachment_warnings:
            st.warning(attachment_warning)
        attachment_context, image_paths = _chat_attachment_context(processed_attachments)

        st.session_state.study_chat_last_question = clean_prompt
        st.session_state.study_chat_last_request = {
            "question": clean_prompt,
            "answer_style": answer_style,
            "chat_mode": chat_mode,
            "context": context,
            "attachment_context": attachment_context,
            "image_paths": image_paths,
        }
        loading_slot = st.empty()
        with loading_slot:
            render_ai_loading("StudyMate is thinking with your study context")
        try:
            answer_data = generate_chat_answer(
                question=clean_prompt,
                answer_style=answer_style,
                chat_mode=chat_mode,
                context=context,
                attachment_context=attachment_context,
                image_paths=image_paths,
            )
        finally:
            loading_slot.empty()

        add_chat_pair(clean_prompt, answer_data, context, attachments=processed_attachments)
        st.session_state.chat_attachment_uploader_key += 1
        if pending_audio_attachment:
            st.session_state.voice_pending_audio = None
            st.session_state.voice_transcript_text = ""
            st.session_state.voice_transcription_status = None
            st.session_state.voice_audio_uploader_key += 1
        st.rerun()
