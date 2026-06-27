"""
Supabase Database CRUD Helpers skeleton for StudyMate AI (Phase 2).
Exposes typed CRUD signatures and template implementations using the Supabase client.
Includes application-level AES-256 encryption/decryption for user API keys.
"""

import base64
import hashlib
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from cryptography.fernet import Fernet
from modules.supabase_client import get_supabase_client, get_supabase_admin_client

logger = logging.getLogger("studymate.supabase_db")

# =====================================================================
# 1. API KEY ENCRYPTION HELPERS
# =====================================================================
def _get_fernet_instance() -> Fernet:
    """Derive a 32-byte url-safe Fernet key from the APP_ENCRYPTION_KEY environment variable."""
    # Attempt to load APP_ENCRYPTION_KEY from environment or fallback
    secret = os.getenv("APP_ENCRYPTION_KEY", "fallback_default_secret_key_change_me_in_prod")
    # Derive a 32-byte key using SHA-256 and base64 URL encoding
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt_key(plain_key: str) -> str:
    """
    Encrypt a plaintext API key for safe database storage.
    Returns:
        str: Base64 encrypted token string.
    """
    if not plain_key:
        return ""
    try:
        fernet = _get_fernet_instance()
        return fernet.encrypt(plain_key.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt API key: {e}")
        raise ValueError("Encryption failure")


def decrypt_key(encrypted_key: str) -> str:
    """
    Decrypt an encrypted API key from the database.
    Returns:
        str: Original plaintext API key.
    """
    if not encrypted_key:
        return ""
    try:
        fernet = _get_fernet_instance()
        return fernet.decrypt(encrypted_key.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        raise ValueError("Decryption failure")


# =====================================================================
# 2. USERS & USER PREFERENCES CRUD
# =====================================================================
def create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new user. Usually handled during auth/signup."""
    client = get_supabase_admin_client()  # Creation requires admin context
    if not client:
        return None
    try:
        response = client.table("users").insert(user_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"create_user error: {e}")
        return None


def get_user_by_id(user_id: UUID) -> Optional[Dict[str, Any]]:
    """Fetch user profile by their UUID."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        response = client.table("users").select("*").eq("id", str(user_id)).is_("deleted_at", "null").execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"get_user_by_id error: {e}")
        return None


def update_user(user_id: UUID, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update user profile info."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        response = client.table("users").update(updates).eq("id", str(user_id)).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"update_user error: {e}")
        return None


def soft_delete_user(user_id: UUID) -> bool:
    """Soft delete a user by setting deleted_at timestamp."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        response = client.table("users").update({"deleted_at": now}).eq("id", str(user_id)).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"soft_delete_user error: {e}")
        return False


def get_user_preferences(user_id: UUID) -> Optional[Dict[str, Any]]:
    """Fetch preferences for a specific user."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        response = client.table("user_preferences").select("*").eq("id", str(user_id)).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"get_user_preferences error: {e}")
        return None


def update_user_preferences(user_id: UUID, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Upsert or update user preferences."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        response = client.table("user_preferences").upsert({"id": str(user_id), **updates}).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"update_user_preferences error: {e}")
        return None


# =====================================================================
# 3. SUBJECTS CRUD
# =====================================================================
def create_subject(owner_id: UUID, name: str, color: str, icon: str = "📚", description: str = "") -> Optional[Dict[str, Any]]:
    """Create a new subject."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        data = {
            "owner_id": str(owner_id),
            "subject_name": name,
            "color": color,
            "icon": icon,
            "description": description
        }
        response = client.table("subjects").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"create_subject error: {e}")
        return None


def get_subjects_by_owner(owner_id: UUID) -> List[Dict[str, Any]]:
    """Fetch active (non-deleted) subjects owned by user."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        response = client.table("subjects").select("*").eq("owner_id", str(owner_id)).is_("deleted_at", "null").execute()
        return response.data or []
    except Exception as e:
        logger.error(f"get_subjects_by_owner error: {e}")
        return []


# =====================================================================
# 4. UPLOADED FILES & LIBRARY CRUD
# =====================================================================
def create_uploaded_file(file_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Record an uploaded file's metadata."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        response = client.table("uploaded_files").insert(file_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"create_uploaded_file error: {e}")
        return None


def get_study_library(owner_id: UUID) -> List[Dict[str, Any]]:
    """Fetch library items for a specific user."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        response = client.table("study_library").select("*, uploaded_files(*)").eq("owner_id", str(owner_id)).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"get_study_library error: {e}")
        return []


# =====================================================================
# 5. CHAT CONVERSATIONS CRUD
# =====================================================================
def create_chat_session(owner_id: UUID, title: str, chat_mode: str, model: str, provider: str, subject_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
    """Initialize a new chat session."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        data = {
            "owner_id": str(owner_id),
            "title": title,
            "chat_mode": chat_mode,
            "model": model,
            "provider": provider,
            "subject_id": str(subject_id) if subject_id else None
        }
        response = client.table("chat_sessions").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"create_chat_session error: {e}")
        return None


def create_chat_message(session_id: UUID, role: str, message: str, attachments: List[Dict[str, Any]] = [], token_count: int = 0) -> Optional[Dict[str, Any]]:
    """Insert a message into a chat session."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        data = {
            "session_id": str(session_id),
            "role": role,
            "message": message,
            "attachments": attachments,
            "token_count": token_count
        }
        response = client.table("chat_messages").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"create_chat_message error: {e}")
        return None


# =====================================================================
# 6. AI MEMORY CRUD
# =====================================================================
def upsert_ai_memory(owner_id: UUID, key: str, value: str, importance: int = 1) -> Optional[Dict[str, Any]]:
    """Upsert user profile memory state."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        data = {
            "owner_id": str(owner_id),
            "memory_key": key,
            "memory_value": value,
            "importance": importance
        }
        response = client.table("ai_memory").upsert(data, on_conflict="owner_id,memory_key").execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"upsert_ai_memory error: {e}")
        return None


# =====================================================================
# 7. FLASHCARDS, QUIZZES, REVISION PLANS CRUD
# =====================================================================
def create_flashcard(owner_id: UUID, subject_id: UUID, question: str, answer: str, difficulty: str = "medium") -> Optional[Dict[str, Any]]:
    """Create a new study flashcard."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        data = {
            "owner_id": str(owner_id),
            "subject_id": str(subject_id),
            "question": question,
            "answer": answer,
            "difficulty": difficulty
        }
        response = client.table("flashcards").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"create_flashcard error: {e}")
        return None


def create_quiz_result(owner_id: UUID, subject_id: UUID, score: int, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Record a completed quiz result."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        data = {
            "owner_id": str(owner_id),
            "subject_id": str(subject_id),
            "score": score,
            "configuration": config
        }
        response = client.table("quizzes").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"create_quiz_result error: {e}")
        return None


def upsert_revision_plan(owner_id: UUID, subject_id: UUID, schedule: Dict[str, Any], progress: int = 0) -> Optional[Dict[str, Any]]:
    """Create or update a revision plan."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        data = {
            "owner_id": str(owner_id),
            "subject_id": str(subject_id),
            "schedule": schedule,
            "progress": progress
        }
        response = client.table("revision_plans").upsert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"upsert_revision_plan error: {e}")
        return None


# =====================================================================
# 8. USER API KEYS CRUD (With Encryption/Decryption)
# =====================================================================
def save_user_api_key(owner_id: UUID, provider: str, plain_key: str, default_model: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Encrypt and save a user's custom API key.
    """
    client = get_supabase_client()
    if not client:
        return None
    try:
        encrypted = encrypt_key(plain_key)
        data = {
            "owner_id": str(owner_id),
            "provider": provider,
            "encrypted_api_key": encrypted,
            "default_model": default_model
        }
        response = client.table("user_api_keys").upsert(data, on_conflict="owner_id,provider").execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"save_user_api_key error: {e}")
        return None


def get_user_api_key(owner_id: UUID, provider: str) -> Optional[str]:
    """
    Fetch and decrypt a user's custom API key.
    """
    client = get_supabase_client()
    if not client:
        return None
    try:
        response = client.table("user_api_keys").select("encrypted_api_key").eq("owner_id", str(owner_id)).eq("provider", provider).execute()
        if response.data:
            encrypted = response.data[0]["encrypted_api_key"]
            return decrypt_key(encrypted)
        return None
    except Exception as e:
        logger.error(f"get_user_api_key error: {e}")
        return None


# =====================================================================
# 9. AUDIT LOGS CRUD
# =====================================================================
def log_audit_event(user_id: UUID, action: str, resource: str, resource_id: Optional[str] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> bool:
    """Record an audit trail event."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        data = {
            "user_id": str(user_id),
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        response = client.table("audit_logs").insert(data).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"log_audit_event error: {e}")
        return False


# =====================================================================
# 10. DOCUMENT EMBEDDINGS CRUD
# =====================================================================
def insert_document_embeddings(file_id: UUID, chunk_index: int, text_chunk: str, model: str, vector_data: List[float]) -> bool:
    """Insert high-dimensional vector embeddings for document chunks."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        data = {
            "uploaded_file_id": str(file_id),
            "chunk_index": chunk_index,
            "text_chunk": text_chunk,
            "embedding_model": model,
            "embedding_vector": vector_data
        }
        response = client.table("document_embeddings").insert(data).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"insert_document_embeddings error: {e}")
        return False
