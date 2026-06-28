"""
Chat Repository module for StudyMate AI (Phase 4C).
Provides Supabase database operations for chat sessions and chat messages,
supporting soft deletes, pagination, and token/cost metadata tracking.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from modules.user_repository import is_supabase_online, log_audit_event

logger = logging.getLogger("studymate.chat_repository")

def _get_client():
    from modules.supabase_client import get_supabase_admin_client
    return get_supabase_admin_client()

# =====================================================================
# CHAT SESSIONS CRUD
# =====================================================================
def create_chat(
    owner_id: str,
    title: str = "New Chat",
    mode: str = "General Chat",
    subject_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None,
    context_label: Optional[str] = None
) -> Optional[str]:
    """Create a new chat session in Supabase."""
    if not is_supabase_online():
        logger.error("Supabase offline. Cannot create chat session.")
        return None

    client = _get_client()
    if not client:
        return None

    try:
        # Convert document_ids to JSON strings or keep format
        doc_ids_json = json.dumps(document_ids or [])
        data = {
            "owner_id": owner_id,
            "title": title,
            "chat_mode": mode,
            "subject_id": subject_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "message_count": 0,
            "archived": False,
            "pinned": False,
            "favorite": False,
        }
        resp = client.table("chat_sessions").insert(data).execute()
        if resp.data:
            session_uuid = resp.data[0]["id"]
            log_audit_event(owner_id, "CHAT_CREATED", "chat_sessions", session_uuid)
            return session_uuid
        return None
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}")
        return None


def rename_chat(owner_id: str, chat_id: str, new_title: str) -> bool:
    """Rename an active chat session."""
    if not is_supabase_online():
        return False

    client = _get_client()
    if not client:
        return False

    try:
        resp = client.table("chat_sessions").update({
            "title": new_title,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", chat_id).eq("owner_id", owner_id).execute()
        return bool(resp.data)
    except Exception as e:
        logger.error(f"Failed to rename chat: {e}")
        return False


def delete_chat(owner_id: str, chat_id: str, soft: bool = True) -> bool:
    """
    Delete a chat session.
    By default, uses soft deletes by setting 'deleted_at' timestamp.
    """
    if not is_supabase_online():
        return False

    client = _get_client()
    if not client:
        return False

    try:
        if soft:
            # Soft delete: update deleted_at
            resp = client.table("chat_sessions").update({
                "deleted_at": datetime.utcnow().isoformat()
            }).eq("id", chat_id).eq("owner_id", owner_id).execute()
        else:
            # Hard delete: purge from database
            resp = client.table("chat_sessions").delete().eq("id", chat_id).eq("owner_id", owner_id).execute()

        log_audit_event(owner_id, "CHAT_DELETED", "chat_sessions", chat_id)
        return bool(resp.data)
    except Exception as e:
        logger.error(f"Failed to delete chat: {e}")
        return False


def archive_chat(owner_id: str, chat_id: str, archived: bool = True) -> bool:
    """Archive/Unarchive a chat session."""
    if not is_supabase_online():
        return False

    client = _get_client()
    if not client:
        return False

    try:
        resp = client.table("chat_sessions").update({
            "archived": archived,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", chat_id).eq("owner_id", owner_id).execute()
        return bool(resp.data)
    except Exception as e:
        logger.error(f"Failed to archive chat: {e}")
        return False


def pin_chat(owner_id: str, chat_id: str, pinned: bool = True) -> bool:
    """Pin/Unpin a chat session."""
    if not is_supabase_online():
        return False

    client = _get_client()
    if not client:
        return False

    try:
        resp = client.table("chat_sessions").update({
            "pinned": pinned,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", chat_id).eq("owner_id", owner_id).execute()
        return bool(resp.data)
    except Exception as e:
        logger.error(f"Failed to pin chat: {e}")
        return False


def get_chat(owner_id: str, chat_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve details of a single chat session."""
    if not is_supabase_online():
        return None

    client = _get_client()
    if not client:
        return None

    try:
        resp = client.table("chat_sessions").select("*").eq("id", chat_id).eq("owner_id", owner_id).is_("deleted_at", "null").execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.error(f"get_chat failed: {e}")
        return None


def get_recent_chats(owner_id: str, limit: int = 50, archived: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieve list of active chat sessions.
    Returns pinned chats first, then sorts by updated_at descending.
    """
    if not is_supabase_online():
        return []

    client = _get_client()
    if not client:
        return []

    try:
        resp = client.table("chat_sessions") \
            .select("*") \
            .eq("owner_id", owner_id) \
            .eq("archived", archived) \
            .is_("deleted_at", "null") \
            .order("pinned", desc=True) \
            .order("updated_at", desc=True) \
            .limit(limit) \
            .execute()
        return resp.data or []
    except Exception as e:
        logger.error(f"Failed to retrieve recent chats: {e}")
        return []


# =====================================================================
# CHAT MESSAGES CRUD
# =====================================================================
def get_chat_messages(owner_id: str, chat_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Retrieve list of messages for a chat session.
    Ordered chronologically by message_index (or created_at).
    """
    if not is_supabase_online():
        return []

    client = _get_client()
    if not client:
        return []

    try:
        resp = client.table("chat_messages") \
            .select("*") \
            .eq("session_id", chat_id) \
            .eq("owner_id", owner_id) \
            .order("message_index", desc=False) \
            .range(offset, offset + limit - 1) \
            .execute()
        return resp.data or []
    except Exception as e:
        logger.error(f"Failed to get chat messages: {e}")
        return []


def save_message(
    owner_id: str,
    chat_id: str,
    role: str,
    content: str,
    context_json: Optional[Dict[str, Any]] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
    sources_json: Optional[List[Dict[str, Any]]] = None,
    warning: str = "",
    source_count: int = 0,
    suggestions_json: Optional[List[str]] = None,
    model_used: Optional[str] = None,
    response_time: Optional[float] = None,
    token_count: int = 0,
    estimated_cost: float = 0.0,
    response_metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Save a new message inside Supabase chat_messages table.
    Increments index, updates last_message on chat_sessions.
    """
    if not is_supabase_online():
        return None

    client = _get_client()
    if not client:
        return None

    try:
        # 1. Fetch current message count to determine next message_index
        chat = get_chat(owner_id, chat_id)
        if not chat:
            return None

        next_idx = chat.get("message_count", 0) + 1

        # 2. Insert message record
        msg_data = {
            "session_id": chat_id,
            "chat_id": chat_id,
            "owner_id": owner_id,
            "role": role,
            "message": content,
            "content": content,
            "token_count": token_count,
            "estimated_cost": estimated_cost,
            "response_time": response_time,
            "message_index": next_idx,
            "context_json": context_json or {},
            "metadata_json": metadata_json or {},
            "sources_json": sources_json or [],
            "warning": warning,
            "source_count": source_count,
            "suggestions_json": suggestions_json or [],
            "response_metadata": response_metadata or {}
        }
        resp = client.table("chat_messages").insert(msg_data).execute()
        if not resp.data:
            return None

        msg_uuid = resp.data[0]["id"]

        # 3. Update chat_sessions metadata counters
        client.table("chat_sessions").update({
            "message_count": next_idx,
            "last_message": content[:300],
            "model_used": model_used or chat.get("model_used"),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", chat_id).eq("owner_id", owner_id).execute()

        log_audit_event(owner_id, "MESSAGE_SAVED", "chat_messages", msg_uuid)
        
        # 4. Trigger auto-summarization at 20 message intervals
        if next_idx >= 20 and next_idx % 20 == 0:
            try:
                auto_summarize_chat(owner_id, chat_id)
            except Exception as se:
                logger.warning(f"Deferred auto-summarization failed: {se}")

        return msg_uuid
    except Exception as e:
        logger.error(f"Failed to save message: {e}")
        return None


def auto_summarize_chat(owner_id: str, chat_id: str):
    """Generate and store a summary of the conversation history to compress prompt contexts."""
    client = _get_client()
    if not client:
        return

    try:
        # Load last 40 messages to generate context
        messages = get_chat_messages(owner_id, chat_id, limit=40)
        if not messages:
            return

        history_lines = []
        for m in messages:
            role = "Student" if m["role"] == "user" else "Tutor"
            history_lines.append(f"{role}: {m['content']}")
        history_text = "\n".join(history_lines)

        from modules import ai_engine
        prompt = (
            "Write a concise summary paragraph of the student's study topics, "
            "questions, and learning progress discussed in this conversation. "
            "Focus on academic facts, weak areas, and preferences:\n\n"
            f"{history_text}"
        )
        summary = ai_engine.ask_ai(prompt)

        # Retrieve current version
        chat = get_chat(owner_id, chat_id)
        if not chat:
            return
            
        curr_ver = 1.0
        try:
            curr_ver = float(chat.get("summary_version") or "1.0")
        except ValueError:
            pass
        new_ver = f"{curr_ver + 0.1:.1f}"

        client.table("chat_sessions").update({
            "conversation_summary": summary,
            "summary_version": new_ver
        }).eq("id", chat_id).eq("owner_id", owner_id).execute()
        logger.info(f"Auto-summarized chat {chat_id} (Version: {new_ver})")
    except Exception as e:
        logger.error(f"Auto-summarization failed: {e}")


# =====================================================================
# SEARCH & AI HELPERS
# =====================================================================
def search_chats(owner_id: str, query: str) -> List[Dict[str, Any]]:
    """Search matches across chat session titles and message contents."""
    if not is_supabase_online() or not query.strip():
        return []

    client = _get_client()
    if not client:
        return []

    try:
        clean_q = query.strip()
        # Find matching session titles
        title_resp = client.table("chat_sessions") \
            .select("*") \
            .eq("owner_id", owner_id) \
            .is_("deleted_at", "null") \
            .ilike("title", f"%{clean_q}%") \
            .execute()

        # Find matching message contents
        msg_resp = client.table("chat_messages") \
            .select("session_id") \
            .eq("owner_id", owner_id) \
            .ilike("content", f"%{clean_q}%") \
            .execute()

        matching_session_ids = {m["session_id"] for m in msg_resp.data} if msg_resp.data else set()
        
        # Pull matching session rows in bulk
        sessions = {s["id"]: s for s in title_resp.data} if title_resp.data else {}
        for sid in matching_session_ids:
            if sid not in sessions:
                session_details = get_chat(owner_id, sid)
                if session_details:
                    sessions[sid] = session_details

        return list(sessions.values())
    except Exception as e:
        logger.error(f"search_chats failed: {e}")
        return []


def create_chat_title(message_content: str) -> str:
    """Generate a brief 3-5 word summary title using AI (with smart regex fallback)."""
    clean = message_content.strip()
    if not clean:
        return "New Chat"

    try:
        from modules import ai_engine
        prompt = f"Summarize the following topic into a concise 3 to 5 word chat title. Do not include quotes, prefix headers, or markdown punctuation.\n\nTopic: {clean}"
        title = ai_engine.ask_ai(prompt)
        title = title.strip().replace('"', '').replace("'", "").strip(" .!?-")
        if title and len(title.split()) <= 6:
            return title
    except Exception:
        pass

    # Safe text-based fallback
    words = clean.split()
    if len(words) > 5:
        return " ".join(words[:5]) + "..."
    return clean
