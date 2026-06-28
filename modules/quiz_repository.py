"""
Quiz Repository module for StudyMate AI (Phase 4D).
Handles Supabase quiz configurations, attempts history, and statistics calculation.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from modules.base_repository import BaseRepository
from services.event_dispatcher import dispatch_event
from modules.user_repository import log_audit_event

logger = logging.getLogger("studymate.quiz_repository")

class QuizRepository(BaseRepository):
    """Repository managing quiz metadata, answers validation, and attempt histories."""
    
    @classmethod
    def create_quiz(
        cls,
        owner_id: str,
        subject_id: str,
        quiz_type: str = "MCQ",
        difficulty: str = "Medium",
        question_count: int = 5,
        topic: Optional[str] = None
    ) -> Optional[str]:
        """Create a new quiz session template."""
        if not cls.is_online():
            return None
        client = cls.get_client()
        if not client:
            return None
        try:
            data = {
                "owner_id": owner_id,
                "subject_id": subject_id,
                "quiz_type": quiz_type,
                "difficulty": difficulty,
                "question_count": question_count,
                "total_questions": question_count,
                "score": 0,
                "percentage": 0.00,
                "topic": topic or "General",
                "created_at": datetime.utcnow().isoformat()
            }
            resp = client.table("quizzes").insert(data).execute()
            if resp.data:
                quiz_uuid = resp.data[0]["id"]
                log_audit_event(owner_id, "QUIZ_CREATED", "quizzes", quiz_uuid)
                return quiz_uuid
            return None
        except Exception as e:
            logger.error(f"Failed to create quiz: {e}")
            return None

    @classmethod
    def save_attempt(
        cls,
        owner_id: str,
        subject_id: str,
        score: int,
        total_questions: int,
        topic: str = "General",
        quiz_type: str = "MCQ",
        difficulty: str = "Medium",
        time_taken: int = 0,
        wrong_answers: Optional[List[Dict[str, Any]]] = None,
        correct_answers: Optional[List[Dict[str, Any]]] = None,
        weak_topics: Optional[List[str]] = None
    ) -> Optional[str]:
        """Record a completed quiz attempt permanently into public.quizzes table."""
        if not cls.is_online():
            return None
        client = cls.get_client()
        if not client:
            return None
        try:
            percentage = round((score / total_questions) * 100, 2) if total_questions > 0 else 0.00
            
            # Fetch current attempt count for this topic/subject to increment attempt_number
            attempt_number = 1
            existing = client.table("quizzes") \
                .select("id") \
                .eq("owner_id", owner_id) \
                .eq("subject_id", subject_id) \
                .execute()
            if existing.data:
                attempt_number = len(existing.data) + 1

            data = {
                "owner_id": owner_id,
                "subject_id": subject_id,
                "quiz_type": quiz_type,
                "difficulty": difficulty,
                "question_count": total_questions,
                "total_questions": total_questions,
                "score": score,
                "percentage": percentage,
                "time_taken": time_taken,
                "attempt_number": attempt_number,
                "topic": topic or "General",
                "wrong_answers": wrong_answers or [],
                "correct_answers": correct_answers or [],
                "weak_topics": weak_topics or [],
                "created_at": datetime.utcnow().isoformat()
            }
            
            resp = client.table("quizzes").insert(data).execute()
            if resp.data:
                attempt_id = resp.data[0]["id"]
                log_audit_event(owner_id, "QUIZ_ATTEMPT_SAVED", "quizzes", attempt_id)
                
                # Dispatch event to update statistics and weaknesses
                dispatch_event("QUIZ_COMPLETED", owner_id, {
                    "attempt_id": attempt_id,
                    "subject_id": subject_id,
                    "score": score,
                    "total_questions": total_questions,
                    "percentage": percentage,
                    "topic": topic,
                    "weak_topics": weak_topics or []
                })
                
                return attempt_id
            return None
        except Exception as e:
            logger.error(f"Failed to save quiz attempt: {e}")
            return None

    @classmethod
    def get_quiz_history(cls, owner_id: str, subject_id: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetch list of completed quizzes for a user, with resolved subject names."""
        if not cls.is_online():
            return []
        client = cls.get_client()
        if not client:
            return []
        try:
            q = client.table("quizzes").select("*, subjects(name)").eq("owner_id", owner_id)
            if subject_id:
                q = q.eq("subject_id", subject_id)
            resp = q.order("created_at", desc=True).limit(limit).execute()
            
            # Map subjects.name into flat dict format
            results = []
            for row in (resp.data or []):
                subject_info = row.get("subjects")
                row["subject_name"] = subject_info.get("name") if subject_info else "Unknown Subject"
                results.append(row)
            return results
        except Exception as e:
            logger.error(f"Failed to fetch quiz history: {e}")
            return []

    @classmethod
    def get_quiz_statistics(cls, owner_id: str, subject_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate statistics for quiz reviews."""
        history = cls.get_quiz_history(owner_id, subject_id, limit=200)
        if not history:
            return {"attempts_count": 0, "average_score": 0.0, "average_percentage": 0.0}
        
        scores = [h["score"] for h in history]
        percentages = [float(h["percentage"] or 0.0) for h in history]
        return {
            "attempts_count": len(history),
            "average_score": round(sum(scores) / len(scores), 2),
            "average_percentage": round(sum(percentages) / len(percentages), 2)
        }
