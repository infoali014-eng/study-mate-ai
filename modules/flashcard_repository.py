"""
Flashcard Repository module for StudyMate AI (Phase 4D).
Handles Supabase flashcard persistence, reviews, and SM-2 spaced repetition calculations.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from modules.base_repository import BaseRepository
from services.event_dispatcher import dispatch_event
from modules.user_repository import log_audit_event

logger = logging.getLogger("studymate.flashcard_repository")

class FlashcardRepository(BaseRepository):
    """Repository managing flashcard metadata, tags, and SM-2 calculations."""
    
    @classmethod
    def create_flashcard(
        cls,
        owner_id: str,
        subject_id: str,
        question: str,
        answer: str,
        difficulty: str = "medium",
        tags: Optional[List[str]] = None,
        topic: Optional[str] = None
    ) -> Optional[str]:
        if not cls.is_online():
            return None
        client = cls.get_client()
        if not client:
            return None
        try:
            data = {
                "owner_id": owner_id,
                "subject_id": subject_id,
                "question": question.strip(),
                "answer": answer.strip(),
                "difficulty": difficulty,
                "tags": tags or [],
                "topic": topic.strip() if topic else "General",
                "status": "New",
                "easiness_factor": 2.50,
                "interval": 0,
                "repetition": 0,
                "next_review": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            resp = client.table("flashcards").insert(data).execute()
            if resp.data:
                card_uuid = resp.data[0]["id"]
                log_audit_event(owner_id, "FLASHCARD_CREATED", "flashcards", card_uuid)
                return card_uuid
            return None
        except Exception as e:
            logger.error(f"Failed to create flashcard: {e}")
            return None

    @classmethod
    def get_flashcard(cls, owner_id: str, card_id: str) -> Optional[Dict[str, Any]]:
        if not cls.is_online():
            return None
        client = cls.get_client()
        if not client:
            return None
        try:
            resp = client.table("flashcards").select("*").eq("id", card_id).eq("owner_id", owner_id).execute()
            return resp.data[0] if resp.data else None
        except Exception as e:
            logger.error(f"Failed to fetch flashcard {card_id}: {e}")
            return None

    @classmethod
    def get_flashcards(cls, owner_id: str, subject_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not cls.is_online():
            return []
        client = cls.get_client()
        if not client:
            return []
        try:
            q = client.table("flashcards").select("*").eq("owner_id", owner_id)
            if subject_id:
                q = q.eq("subject_id", subject_id)
            resp = q.order("created_at", desc=False).execute()
            return resp.data or []
        except Exception as e:
            logger.error(f"Failed to fetch flashcards: {e}")
            return []

    @classmethod
    def update_flashcard(cls, owner_id: str, card_id: str, updates: Dict[str, Any]) -> bool:
        if not cls.is_online():
            return False
        client = cls.get_client()
        if not client:
            return False
        try:
            updates["updated_at"] = datetime.utcnow().isoformat()
            resp = client.table("flashcards").update(updates).eq("id", card_id).eq("owner_id", owner_id).execute()
            return bool(resp.data)
        except Exception as e:
            logger.error(f"Failed to update flashcard {card_id}: {e}")
            return False

    @classmethod
    def delete_flashcard(cls, owner_id: str, card_id: str) -> bool:
        if not cls.is_online():
            return False
        client = cls.get_client()
        if not client:
            return False
        try:
            resp = client.table("flashcards").delete().eq("id", card_id).eq("owner_id", owner_id).execute()
            return bool(resp.data)
        except Exception as e:
            logger.error(f"Failed to delete flashcard {card_id}: {e}")
            return False

    @classmethod
    def delete_flashcards_by_subject(cls, owner_id: str, subject_id: str) -> bool:
        if not cls.is_online():
            return False
        client = cls.get_client()
        if not client:
            return False
        try:
            resp = client.table("flashcards").delete().eq("subject_id", subject_id).eq("owner_id", owner_id).execute()
            log_audit_event(owner_id, "FLASHCARDS_PURGED", "flashcards", subject_id)
            return True
        except Exception as e:
            logger.error(f"Failed to purge flashcards for subject {subject_id}: {e}")
            return False

    @classmethod
    def review_flashcard(cls, owner_id: str, card_id: str, rating: int) -> bool:
        """
        Record a flashcard review and update its SM-2 intervals.
        Rating is expected in range 0-5.
        """
        card = cls.get_flashcard(owner_id, card_id)
        if not card:
            return False

        # Apply SM-2 Spaced Repetition logic
        easiness_factor = float(card.get("easiness_factor") or 2.50)
        repetition = int(card.get("repetition") or 0)
        interval = int(card.get("interval") or 0)

        # 1. Update Easiness Factor
        easiness_factor = easiness_factor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
        if easiness_factor < 1.3:
            easiness_factor = 1.3

        # 2. Update repetition and interval
        if rating >= 3:
            if repetition == 0:
                interval = 1
            elif repetition == 1:
                interval = 6
            else:
                interval = int(round(interval * easiness_factor))
            repetition += 1
            status = "Learned"
        else:
            repetition = 0
            interval = 1
            status = "Weak"

        next_review_time = datetime.utcnow() + timedelta(days=interval)

        updates = {
            "review_count": int(card.get("review_count") or 0) + 1,
            "correct_count": int(card.get("correct_count") or 0) + (1 if rating >= 3 else 0),
            "incorrect_count": int(card.get("incorrect_count") or 0) + (0 if rating >= 3 else 1),
            "last_review": datetime.utcnow().isoformat(),
            "next_review": next_review_time.isoformat(),
            "easiness_factor": round(easiness_factor, 2),
            "interval": interval,
            "repetition": repetition,
            "status": status
        }

        success = cls.update_flashcard(owner_id, card_id, updates)
        if success:
            # Dispatch event to update analytics & streaks
            dispatch_event("FLASHCARD_REVIEWED", owner_id, {
                "card_id": card_id,
                "subject_id": card["subject_id"],
                "rating": rating,
                "status": status,
                "topic": card.get("topic")
            })
            log_audit_event(owner_id, "FLASHCARD_REVIEWED", "flashcards", card_id)

        return success

    @classmethod
    def search_flashcards(cls, owner_id: str, query: str) -> List[Dict[str, Any]]:
        if not cls.is_online() or not query.strip():
            return []
        client = cls.get_client()
        if not client:
            return []
        try:
            resp = client.table("flashcards") \
                .select("*") \
                .eq("owner_id", owner_id) \
                .or_(f"question.ilike.%{query}%,answer.ilike.%{query}%,topic.ilike.%{query}%") \
                .execute()
            return resp.data or []
        except Exception as e:
            logger.error(f"Failed to search flashcards: {e}")
            return []
