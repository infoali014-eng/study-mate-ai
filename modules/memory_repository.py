"""
Memory Repository module for StudyMate AI (Phase 4C).
Provides Supabase database operations for user AI long-term memory records,
supporting importance scoring, taxonomy, deduplication, and usage tracking.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from modules.user_repository import is_supabase_online, log_audit_event

logger = logging.getLogger("studymate.memory_repository")

def _get_client():
    from modules.supabase_client import get_supabase_admin_client
    return get_supabase_admin_client()

# =====================================================================
# AI MEMORY CRUD
# =====================================================================
def create_memory(
    owner_id: str,
    key: str,
    value: str,
    category: str = "general_fact",
    confidence: float = 1.0
) -> Optional[str]:
    """
    Save a long-term fact memory inside Supabase.
    Deduplicates based on (owner_id, memory_key).
    """
    if not is_supabase_online():
        logger.error("Supabase offline. Cannot save memory fact.")
        return None

    client = _get_client()
    if not client:
        return None

    try:
        clean_key = key.strip()
        clean_val = value.strip()
        
        # Check if already exists to prevent duplicates
        existing = client.table("ai_memory").select("id").eq("owner_id", owner_id).eq("memory_key", clean_key).execute()
        if existing.data:
            mem_id = existing.data[0]["id"]
            update_memory(owner_id, mem_id, clean_val, confidence=confidence)
            return mem_id

        # Insert new memory record
        data = {
            "owner_id": owner_id,
            "memory_key": clean_key,
            "memory_value": clean_val,
            "memory_type": category,
            "confidence": confidence,
            "importance": 5, # Default middle importance
            "times_referenced": 0,
            "last_used": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        resp = client.table("ai_memory").insert(data).execute()
        if resp.data:
            mem_uuid = resp.data[0]["id"]
            log_audit_event(owner_id, "MEMORY_CREATED", "ai_memory", mem_uuid)
            return mem_uuid
        return None
    except Exception as e:
        logger.error(f"Failed to create memory: {e}")
        return None


def update_memory(owner_id: str, memory_id: str, value: str, confidence: Optional[float] = None) -> bool:
    """Update a memory fact's content and decay values."""
    if not is_supabase_online():
        return False

    client = _get_client()
    if not client:
        return False

    try:
        updates = {
            "memory_value": value.strip(),
            "last_used": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        if confidence is not None:
            updates["confidence"] = confidence

        resp = client.table("ai_memory").update(updates).eq("id", memory_id).eq("owner_id", owner_id).execute()
        if resp.data:
            log_audit_event(owner_id, "MEMORY_UPDATED", "ai_memory", memory_id)
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to update memory: {e}")
        return False


def delete_memory(owner_id: str, memory_id: str) -> bool:
    """Delete a memory fact record."""
    if not is_supabase_online():
        return False

    client = _get_client()
    if not client:
        return False

    try:
        resp = client.table("ai_memory").delete().eq("id", memory_id).eq("owner_id", owner_id).execute()
        return bool(resp.data)
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}")
        return False


def get_memory(owner_id: str, memory_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve details of a single memory fact."""
    if not is_supabase_online():
        return None

    client = _get_client()
    if not client:
        return None

    try:
        resp = client.table("ai_memory").select("*").eq("id", memory_id).eq("owner_id", owner_id).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.error(f"get_memory failed: {e}")
        return None


def touch_memory(owner_id: str, memory_id: str) -> bool:
    """Increment use counter and update last_used timestamp."""
    if not is_supabase_online():
        return False

    client = _get_client()
    if not client:
        return False

    try:
        # Fetch current count
        resp = client.table("ai_memory").select("times_referenced").eq("id", memory_id).eq("owner_id", owner_id).execute()
        if not resp.data:
            return False
        
        current_refs = resp.data[0].get("times_referenced") or 0
        client.table("ai_memory").update({
            "times_referenced": current_refs + 1,
            "last_used": datetime.utcnow().isoformat()
        }).eq("id", memory_id).eq("owner_id", owner_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to touch memory: {e}")
        return False


def search_memory(owner_id: str, query: str) -> List[Dict[str, Any]]:
    """Search for relevant memory facts."""
    if not is_supabase_online() or not query.strip():
        return []

    client = _get_client()
    if not client:
        return []

    try:
        clean_q = query.strip()
        resp = client.table("ai_memory") \
            .select("*") \
            .eq("owner_id", owner_id) \
            .or_(f"memory_key.ilike.%{clean_q}%,memory_value.ilike.%{clean_q}%") \
            .order("importance", desc=True) \
            .execute()
        return resp.data or []
    except Exception as e:
        logger.error(f"search_memory failed: {e}")
        return []


def summarize_memory(owner_id: str) -> str:
    """Format all user memory facts into a structured prompt block."""
    if not is_supabase_online() or not owner_id:
        return "No user preferences profile saved."

    client = _get_client()
    if not client:
        return "No user preferences profile saved."

    try:
        resp = client.table("ai_memory") \
            .select("*") \
            .eq("owner_id", owner_id) \
            .order("memory_type") \
            .order("importance", desc=True) \
            .execute()

        if not resp.data:
            return "No user preferences profile saved."

        lines = []
        for r in resp.data:
            # Touch memory to indicate referencing it in context builder
            touch_memory(owner_id, r["id"])

            mtype = r.get("memory_type", "profile").replace("_", " ").capitalize()
            lines.append(f"- [{mtype}] {r['memory_key']}: {r['memory_value']}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"summarize_memory failed: {e}")
        return "No user preferences profile saved."


def merge_memories(owner_id: str, key_name: str, list_of_values: List[str]) -> bool:
    """Merge overlapping list values into a single memory key (e.g. weak topics list)."""
    if not list_of_values:
        return False
    value_str = ", ".join(set(val.strip() for val in list_of_values if val.strip()))
    return create_memory(owner_id, key_name, value_str) is not None
