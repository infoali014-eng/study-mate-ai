"""
Context Builder service for StudyMate AI (Phase 4C).
Assembles AI prompt context by ranking and merging the system prompt, user profile
memories, recent chat window history, and relevant study notes search matches.
"""

import logging
from typing import Any, Dict, List, Optional

from modules.library_repository import get_document_by_id
from modules.vector_store import query_subject_notes
from modules.memory_repository import summarize_memory

logger = logging.getLogger("studymate.context_builder")

def build_context(
    question: str,
    user_id: str,
    subject_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    chat_summary: Optional[str] = None,
    general_chat: bool = False,
    limit_notes: int = 5,
    limit_history: int = 20
) -> Dict[str, Any]:
    """
    Rank information and build the consolidated context for the AI prompt.
    Returns prompt payload and retrieved notes sources.
    """
    logger.info(f"Assembling AI prompt context for user {user_id}...")

    # 1. Retrieve & Rank Notes Context
    sources = []
    notes_context = ""
    if not general_chat and subject_id:
        try:
            raw_sources = query_subject_notes(
                subject_id=subject_id,
                question=question,
                limit=limit_notes,
                document_ids=document_ids,
                user_id=user_id
            )
            # Rank and score by similarity distance (lower cosine distance = higher similarity)
            # Distance values represent 1.0 - similarity in some engines.
            # In our pgvector setup, pgvector search returns cosine similarity as distance.
            # Sort with highest similarity (distance) first
            sources = sorted(raw_sources, key=lambda x: x.get("distance", 0.0), reverse=True)
            
            # Format notes context
            notes_context = "\n\n".join(
                f"Source {index} [{source['metadata'].get('file_name', 'Document')}]: {source['text']}"
                for index, source in enumerate(sources, start=1)
            )
        except Exception as e:
            logger.warning(f"Vector search failed during context building: {e}")

    # 2. Retrieve User AI Memories
    user_memory = summarize_memory(user_id)

    # 3. Format Recent Conversation Window with Summary Prepending
    formatted_history = ""
    history_lines = []
    
    if chat_history:
        # Take the last configurable number of messages
        recent_messages = chat_history[-limit_history:]
        for msg in recent_messages:
            role_label = "Student" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"{role_label}: {msg['content']}")
            
        formatted_history = "\n".join(history_lines)

    # Prepend chat summary if available (context compression)
    if chat_summary:
        summary_prefix = f"[Earlier Conversation Summary: {chat_summary}]\n"
        formatted_history = summary_prefix + formatted_history

    # 4. Generate system prompt
    from modules.ai_engine import build_study_assistant_system_prompt, get_memory_display_name, get_current_user_display_name
    display_name = get_memory_display_name(user_id, get_current_user_display_name())
    system_prompt = build_study_assistant_system_prompt(display_name, general_chat=general_chat)

    return {
        "system_prompt": system_prompt,
        "notes_context": notes_context,
        "user_memory": user_memory,
        "chat_history": formatted_history,
        "sources": sources
    }
