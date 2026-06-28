"""
Analytics Repository module for StudyMate AI (Phase 4D).
Aggregates Pomodoro times, tracks daily streaks, maintains cached learning profiles,
and evaluates student achievement locks.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, date, timedelta

from modules.base_repository import BaseRepository
from modules.user_repository import log_audit_event

logger = logging.getLogger("studymate.analytics_repository")

class AnalyticsRepository(BaseRepository):
    """Repository computing study metrics, achievements, and statistics caches."""

    @classmethod
    def log_activity_session(cls, owner_id: str, subject_id: str = None, duration_minutes: int = 5, session_type: str = "Focus", notes: str = ""):
        """Log a study activity session to increment streaks and track learning progress."""
        if not cls.is_online():
            return
        client = cls.get_client()
        if not client:
            return
        try:
            today_str = date.today().isoformat()
            existing = client.table("study_sessions") \
                .select("id") \
                .eq("owner_id", owner_id) \
                .eq("session_type", session_type) \
                .gte("completed_at", today_str) \
                .execute()
            if existing.data:
                from services.event_dispatcher import dispatch_event
                dispatch_event("study_session", owner_id, {"duration_minutes": duration_minutes})
                return

            payload = {
                "owner_id": owner_id,
                "duration_minutes": duration_minutes,
                "session_type": session_type,
                "notes": notes,
            }
            if subject_id:
                payload["subject_id"] = subject_id
            client.table("study_sessions").insert(payload).execute()
            from services.event_dispatcher import dispatch_event
            dispatch_event("study_session", owner_id, {"duration_minutes": duration_minutes})
            logger.info(f"Successfully logged {session_type} activity session for user {owner_id}")
        except Exception as e:
            logger.warning(f"Failed to log activity session: {e}")

    @classmethod
    def get_dashboard_statistics(cls, owner_id: str) -> Dict[str, Any]:
        """Fetch the cached learning profile statistics for a user, creating one if empty."""
        if not cls.is_online():
            return cls._empty_stats()
        
        client = cls.get_client()
        if not client:
            return cls._empty_stats()

        try:
            # 1. Fetch cached learning profile
            resp = client.table("learning_profiles").select("*").eq("owner_id", owner_id).execute()
            if not resp.data:
                # Cache miss: recalculate and cache right away
                cls.recalculate_profile_stats(owner_id, "FORCE_RECALCULATE", {})
                resp = client.table("learning_profiles").select("*").eq("owner_id", owner_id).execute()
                
            profile = resp.data[0] if resp.data else cls._empty_stats()

            # 2. Fetch recent quiz attempts and flashcard review counts in bulk for dashboard widgets
            quizzes_count = 0
            flashcards_count = 0
            subjects_count = 0
            documents_count = 0
            
            try:
                qc = client.table("quizzes").select("id", count="exact").eq("owner_id", owner_id).execute()
                quizzes_count = qc.count if qc.count is not None else 0
                
                fc = client.table("flashcards").select("id", count="exact").eq("owner_id", owner_id).execute()
                flashcards_count = fc.count if fc.count is not None else 0

                sc = client.table("subjects").select("id", count="exact").eq("owner_id", owner_id).eq("is_deleted", False).execute()
                subjects_count = sc.count if sc.count is not None else 0

                # Note: uploaded_files (Phase 4B)
                dc = client.table("uploaded_files").select("id", count="exact").eq("owner_id", owner_id).execute()
                documents_count = dc.count if dc.count is not None else 0
            except Exception:
                pass

            # 3. Retrieve unlocked achievements
            achievements = []
            try:
                ac_resp = client.table("user_achievements").select("achievement_type").eq("owner_id", owner_id).execute()
                achievements = [a["achievement_type"] for a in ac_resp.data] if ac_resp.data else []
            except Exception:
                pass

            # 4. Resolve strongest and weakest subject names
            strongest_subject_name = "None yet"
            weakest_subject_name = "None yet"
            try:
                if profile.get("strongest_subject_id"):
                    sub_s = client.table("subjects").select("name").eq("id", profile["strongest_subject_id"]).execute()
                    if sub_s.data:
                        strongest_subject_name = sub_s.data[0]["name"]
                if profile.get("weakest_subject_id"):
                    sub_w = client.table("subjects").select("name").eq("id", profile["weakest_subject_id"]).execute()
                    if sub_w.data:
                        weakest_subject_name = sub_s.data[0]["name"]
            except Exception:
                pass

            # 5. Calculate daily study hours
            study_time_hours = cls.calculate_study_time(owner_id, "daily")

            return {
                "subjects": subjects_count,
                "documents": documents_count,
                "flashcards": flashcards_count,
                "quizzes": quizzes_count,
                "overall_accuracy": float(profile.get("overall_accuracy") or 0.00),
                "retention_score": float(profile.get("retention_score") or 0.00),
                "current_streak": int(profile.get("current_streak") or 0),
                "longest_streak": int(profile.get("longest_streak") or 0),
                "study_level": profile.get("study_level", "Beginner"),
                "strongest_subject": strongest_subject_name,
                "weakest_subject": weakest_subject_name,
                "study_hours_today": study_time_hours,
                "achievements": achievements
            }

        except Exception as e:
            logger.error(f"Failed to fetch dashboard stats: {e}")
            return cls._empty_stats()

    @classmethod
    def calculate_study_time(cls, owner_id: str, range_type: str = "daily") -> float:
        """Sum Pomodoro study duration logged in study_sessions table (returned in hours)."""
        if not cls.is_online():
            return 0.0
        client = cls.get_client()
        if not client:
            return 0.0
        try:
            today_start = datetime.utcnow().date()
            if range_type == "weekly":
                start_date = today_start - timedelta(days=7)
            elif range_type == "monthly":
                start_date = today_start - timedelta(days=30)
            else:
                start_date = today_start

            resp = client.table("study_sessions") \
                .select("duration_minutes") \
                .eq("owner_id", owner_id) \
                .gte("completed_at", start_date.isoformat()) \
                .execute()

            minutes = sum(int(r["duration_minutes"]) for r in resp.data) if resp.data else 0
            return round(minutes / 60.0, 2)
        except Exception as e:
            logger.error(f"Failed to sum study time: {e}")
            return 0.0

    @classmethod
    def recalculate_profile_stats(cls, owner_id: str, event_type: str, data: Dict[str, Any]):
        """Recalculate learning profile values and store in cache."""
        if not cls.is_online():
            return
        client = cls.get_client()
        if not client:
            return

        try:
            # 1. Overall Quiz Accuracy
            quiz_resp = client.table("quizzes").select("percentage").eq("owner_id", owner_id).execute()
            accuracy = 0.0
            if quiz_resp.data:
                percentages = [float(q["percentage"] or 0.0) for q in quiz_resp.data]
                accuracy = sum(percentages) / len(percentages)

            # 2. Flashcard Retention Score (Learned vs Total)
            card_resp = client.table("flashcards").select("status").eq("owner_id", owner_id).execute()
            retention = 0.0
            if card_resp.data:
                learned = sum(1 for c in card_resp.data if c["status"] == "Learned")
                retention = (learned / len(card_resp.data)) * 100.0

            # 3. Streaks Calculation
            streak_days = cls._compute_consecutive_days_streak(owner_id, client)
            current_streak, longest_streak = streak_days

            # 4. Resolve Strongest / Weakest Subject IDs
            # Select subject accuracy aggregates
            strongest_id = None
            weakest_id = None
            try:
                sub_accuracy = client.table("quizzes") \
                    .select("subject_id, percentage") \
                    .eq("owner_id", owner_id) \
                    .execute()
                if sub_accuracy.data:
                    sub_map = {}
                    for item in sub_accuracy.data:
                        sub_id = item["subject_id"]
                        sub_map.setdefault(sub_id, []).append(float(item["percentage"] or 0.0))
                    
                    sub_averages = {sid: (sum(vals)/len(vals)) for sid, vals in sub_map.items()}
                    sorted_subs = sorted(sub_averages.items(), key=lambda x: x[1])
                    if sorted_subs:
                        weakest_id = sorted_subs[0][0]
                        strongest_id = sorted_subs[-1][0]
            except Exception:
                pass

            # Determine Study Level
            study_level = "Beginner"
            if len(quiz_resp.data or []) > 20:
                study_level = "Scholar"
            elif len(quiz_resp.data or []) > 5:
                study_level = "Intermediate"

            profile_data = {
                "owner_id": owner_id,
                "overall_accuracy": round(accuracy, 2),
                "retention_score": round(retention, 2),
                "current_streak": current_streak,
                "longest_streak": longest_streak,
                "strongest_subject_id": strongest_id,
                "weakest_subject_id": weakest_id,
                "study_level": study_level,
                "last_active": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            # Upsert into learning_profiles table
            client.table("learning_profiles").upsert(profile_data).execute()
            logger.info(f"Learning profile recalculated successfully for user {owner_id}.")

        except Exception as e:
            logger.error(f"Failed to recalculate profile statistics: {e}")

    @classmethod
    def check_achievements(cls, owner_id: str, event_type: str, data: Dict[str, Any]):
        """Unlock milestone achievements based on current streak, quiz, or time totals."""
        if not cls.is_online():
            return
        client = cls.get_client()
        if not client:
            return

        try:
            achievements_to_check = []
            
            # Fetch stats
            profile_resp = client.table("learning_profiles").select("*").eq("owner_id", owner_id).execute()
            profile = profile_resp.data[0] if profile_resp.data else {}
            
            # 1. Streak milestones
            streak = int(profile.get("current_streak") or 0)
            if streak >= 7:
                achievements_to_check.append(("7-Day Streak", {"streak": streak}))

            # 2. Perfect quiz
            if event_type == "QUIZ_COMPLETED" and data.get("score") == data.get("total_questions") and data.get("total_questions", 0) > 0:
                achievements_to_check.append(("Perfect Quiz", {"score": data["score"]}))

            # 3. Flashcard quantities
            fc_resp = client.table("flashcards").select("id", count="exact").eq("owner_id", owner_id).execute()
            total_fc = fc_resp.count if fc_resp.count is not None else 0
            if total_fc >= 100:
                achievements_to_check.append(("100 Flashcards", {"total": total_fc}))

            # 4. Quiz quantities
            q_resp = client.table("quizzes").select("id", count="exact").eq("owner_id", owner_id).execute()
            total_q = q_resp.count if q_resp.count is not None else 0
            if total_q >= 50:
                achievements_to_check.append(("50 Quizzes", {"total": total_q}))

            # 5. Study hours total
            hours_total = cls.calculate_study_time(owner_id, "monthly") * 30.0 # general projection or sum all
            # Sum all sessions duration
            session_resp = client.table("study_sessions").select("duration_minutes").eq("owner_id", owner_id).execute()
            total_minutes = sum(int(s["duration_minutes"]) for s in session_resp.data) if session_resp.data else 0
            if total_minutes >= 600: # 10 hours
                achievements_to_check.append(("10 Hours Studied", {"minutes": total_minutes}))

            # Unlocking achievements
            for ach_type, metadata in achievements_to_check:
                try:
                    client.table("user_achievements").insert({
                        "owner_id": owner_id,
                        "achievement_type": ach_type,
                        "metadata": metadata,
                        "unlocked_at": datetime.utcnow().isoformat()
                    }).execute()
                    log_audit_event(owner_id, "ACHIEVEMENT_UNLOCKED", "user_achievements", ach_type)
                    logger.info(f"🏆 Achievement unlocked: '{ach_type}' for user {owner_id}.")
                except Exception:
                    # Ignore unique constraint violations (already unlocked)
                    pass

        except Exception as e:
            logger.error(f"Failed checking achievements: {e}")

    @classmethod
    def _compute_consecutive_days_streak(cls, owner_id: str, client) -> tuple:
        """Compute current and longest study streak in days."""
        try:
            # Fetch completed dates for study sessions, quizzes, and flashcard reviews
            dates = set()
            
            # Study sessions
            ss = client.table("study_sessions").select("completed_at").eq("owner_id", owner_id).execute()
            for row in (ss.data or []):
                dates.add(datetime.fromisoformat(row["completed_at"].replace("Z", "+00:00")).date())
                
            # Quizzes
            qz = client.table("quizzes").select("created_at").eq("owner_id", owner_id).execute()
            for row in (qz.data or []):
                dates.add(datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")).date())

            if not dates:
                return 0, 0

            sorted_dates = sorted(list(dates), reverse=True)
            current_streak = 0
            longest_streak = 0
            
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            # Check if active today or yesterday
            if sorted_dates[0] not in (today, yesterday):
                current_streak = 0
            else:
                current_streak = 1
                for i in range(len(sorted_dates) - 1):
                    diff = sorted_dates[i] - sorted_dates[i+1]
                    if diff == timedelta(days=1):
                        current_streak += 1
                    elif diff > timedelta(days=1):
                        break

            # Calculate longest streak
            temp_streak = 1
            sorted_asc = sorted(list(dates))
            for i in range(len(sorted_asc) - 1):
                diff = sorted_asc[i+1] - sorted_asc[i]
                if diff == timedelta(days=1):
                    temp_streak += 1
                elif diff > timedelta(days=1):
                    longest_streak = max(longest_streak, temp_streak)
                    temp_streak = 1
            longest_streak = max(longest_streak, temp_streak, current_streak)

            return current_streak, longest_streak
        except Exception as e:
            logger.warning(f"Error computing streaks: {e}")
            return 0, 0

    @classmethod
    def _empty_stats(cls) -> Dict[str, Any]:
        return {
            "subjects": 0, "documents": 0, "flashcards": 0, "quizzes": 0,
            "overall_accuracy": 0.0, "retention_score": 0.0,
            "current_streak": 0, "longest_streak": 0, "study_level": "Beginner",
            "strongest_subject": "None yet", "weakest_subject": "None yet",
            "study_hours_today": 0.0, "achievements": []
        }
