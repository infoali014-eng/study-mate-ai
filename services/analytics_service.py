"""
Analytics Service Layer for StudyMate AI (Phase 5D).
Decouples database/repository lookups from the frontend representation.
Centralizes filtering, sessional calculations, smart timeline mappings, and goals tracking.
"""

import os
import logging
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional
from modules.supabase_client import get_supabase_admin_client

logger = logging.getLogger("studymate.analytics_service")

class AnalyticsService:
    """Service layer coordinating study analytics data retrieval and client caching."""

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Convert ISO date string safely to UTC timezone-aware datetime."""
        if not dt_str:
            return None
        try:
            # Handle plain dates
            if len(dt_str) == 10 and dt_str.count("-") == 2:
                return datetime.strptime(dt_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            # Handle standard ISO strings
            clean_str = dt_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_str)
        except Exception:
            return None

    @classmethod
    def _is_in_range(cls, dt_str: Optional[str], start_date: Optional[datetime]) -> bool:
        """Evaluate if an ISO date string falls after the filter threshold."""
        if not start_date:
            return True
        dt = cls._parse_datetime(dt_str)
        if not dt:
            return False
        return dt >= start_date

    @classmethod
    def get_dashboard_data(cls, user_id: str, subject_id: Optional[str] = None, date_range: str = "All Time") -> Dict[str, Any]:
        """
        Fetch all user collections in bulk and process them in Python memory.
        Applies date and subject filters, compiles smart timeline activity items,
        tracks engagement goals, and evaluates visual achievements progress.
        """
        client = get_supabase_admin_client()
        if not client:
            return cls._empty_payload()

        try:
            # ── 1. Determine Date Range Start Threshold ──────────────────────
            now = datetime.now(timezone.utc)
            start_date = None
            if date_range == "Today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif date_range == "Last 7 Days":
                start_date = now - timedelta(days=7)
            elif date_range == "Last 30 Days":
                start_date = now - timedelta(days=30)
            elif date_range == "Last 90 Days":
                start_date = now - timedelta(days=90)

            # ── 2. Bulk Database Queries ──────────────────────────────────────
            # Fetch subjects list
            subj_resp = client.table("subjects").select("*").eq("owner_id", user_id).is_("deleted_at", "null").execute()
            subjects = subj_resp.data or []
            subject_map = {s["id"]: s["subject_name"] for s in subjects}

            # Fetch learning profile
            profile_resp = client.table("learning_profiles").select("*").eq("owner_id", user_id).execute()
            profile = profile_resp.data[0] if profile_resp.data else {}

            # Fetch uploaded notes files
            files_resp = client.table("uploaded_files").select("*").eq("owner_id", user_id).execute()
            all_files = files_resp.data or []
            file_map = {f["id"]: f["original_filename"] for f in all_files}

            # Fetch study library items
            lib_resp = client.table("study_library").select("*").eq("owner_id", user_id).execute()
            all_lib = lib_resp.data or []

            # Fetch AI chats
            chats_resp = client.table("chat_sessions").select("*").eq("owner_id", user_id).execute()
            all_chats = chats_resp.data or []

            # Fetch flashcards
            fc_resp = client.table("flashcards").select("*").eq("owner_id", user_id).execute()
            all_fc = fc_resp.data or []

            # Fetch quizzes
            quizzes_resp = client.table("quizzes").select("*").eq("owner_id", user_id).execute()
            all_quizzes = quizzes_resp.data or []
            quiz_map = {q["id"]: q for q in all_quizzes}

            # Fetch revision plans
            plans_resp = client.table("revision_plans").select("*").eq("owner_id", user_id).execute()
            all_plans = plans_resp.data or []
            plan_map = {p["id"]: p["title"] for p in all_plans}

            # Fetch study sessions (Pomodoro focus)
            sessions_resp = client.table("study_sessions").select("*").eq("owner_id", user_id).execute()
            all_sessions = sessions_resp.data or []

            # Fetch achievements
            ach_resp = client.table("user_achievements").select("*").eq("owner_id", user_id).execute()
            unlocked_ach = ach_resp.data or []
            unlocked_types = {a["achievement_type"] for a in unlocked_ach}

            # Fetch AI recommendations
            recs_resp = client.table("ai_recommendations").select("*").eq("owner_id", user_id).eq("status", "Pending").execute()
            recs = recs_resp.data or []

            # Fetch recent audit logs
            audit_resp = client.table("audit_logs").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(80).execute()
            all_audits = audit_resp.data or []

            # ── 3. Apply Filters In-Memory ────────────────────────────────────
            # Filter functions
            def keep(row: dict, date_field: str = "created_at") -> bool:
                if subject_id and row.get("subject_id") != subject_id:
                    return False
                return cls._is_in_range(row.get(date_field), start_date)

            filtered_files = [f for f in all_files if keep(f, "uploaded_at")]
            filtered_lib = [l for l in all_lib if keep(l, "created_at")]
            filtered_chats = [c for c in all_chats if keep(c, "created_at")]
            filtered_fc = [f for f in all_fc if keep(f, "created_at")]
            filtered_quizzes = [q for q in all_quizzes if keep(q, "created_at")]
            filtered_plans = [p for p in all_plans if keep(p, "planned_date")]
            filtered_sessions = [s for s in all_sessions if keep(s, "completed_at")]

            # ── 4. Calculate Overview Metrics ─────────────────────────────────
            total_study_minutes = sum(int(s["duration_minutes"] or 0) for s in filtered_sessions)
            total_study_hours = round(total_study_minutes / 60.0, 1)

            overview = {
                "study_time_hours": total_study_hours,
                "total_subjects": len(subjects) if not subject_id else 1,
                "notes_uploaded": len(filtered_files),
                "documents_processed": len(filtered_lib),
                "ai_chats": len(filtered_chats),
                "flashcards": len(filtered_fc),
                "quiz_attempts": len(filtered_quizzes),
                "revision_plans": len(filtered_plans)
            }

            # ── 5. Goals Tracker ──────────────────────────────────────────────
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = now - timedelta(days=7)

            today_minutes = sum(int(s["duration_minutes"] or 0) for s in all_sessions if cls._is_in_range(s["completed_at"], today_start))
            week_minutes = sum(int(s["duration_minutes"] or 0) for s in all_sessions if cls._is_in_range(s["completed_at"], week_start))

            today_hours = round(today_minutes / 60.0, 1)
            week_hours = round(week_minutes / 60.0, 1)

            today_goal = 3.0
            week_goal = 15.0

            goals = {
                "today_hours": today_hours,
                "today_goal": today_goal,
                "today_pct": min(100, int((today_hours / today_goal) * 100)) if today_goal else 0,
                "week_hours": week_hours,
                "week_goal": week_goal,
                "week_pct": min(100, int((week_hours / week_goal) * 100)) if week_goal else 0
            }

            # ── 6. Computed Quick Insights ────────────────────────────────────
            # Today's Focus (subject with most study time today)
            today_sub_minutes = {}
            for s in all_sessions:
                if cls._is_in_range(s["completed_at"], today_start) and s.get("subject_id"):
                    today_sub_minutes[s["subject_id"]] = today_sub_minutes.get(s["subject_id"], 0) + int(s["duration_minutes"] or 0)
            today_focus = "None"
            if today_sub_minutes:
                best_sub_id = max(today_sub_minutes, key=today_sub_minutes.get)
                today_focus = subject_map.get(best_sub_id, "Unknown")

            # Quizzes grouping for strongest/weakest subject
            sub_percentages = {}
            for q in all_quizzes:
                if q.get("subject_id"):
                    sub_percentages.setdefault(q["subject_id"], []).append(float(q["percentage"] or 0.0))
            
            sub_averages = {sid: (sum(vals) / len(vals)) for sid, vals in sub_percentages.items()}
            
            strongest_subject = "None yet"
            weakest_subject = "None yet"
            if sub_averages:
                strongest_id = max(sub_averages, key=sub_averages.get)
                weakest_id = min(sub_averages, key=sub_averages.get)
                strongest_subject = subject_map.get(strongest_id, "Unknown")
                weakest_subject = subject_map.get(weakest_id, "Unknown")

            # Upcoming planner deadline
            upcoming_task = "None pending"
            pending_plans = [p for p in all_plans if p.get("status") == "Pending" and p.get("planned_date")]
            if pending_plans:
                sorted_pending = sorted(pending_plans, key=lambda x: x["planned_date"])
                upcoming_task = f"{sorted_pending[0]['title']} ({sorted_pending[0]['planned_date']})"

            # Longest study session
            longest_session = 0
            if filtered_sessions:
                longest_session = max(int(s["duration_minutes"] or 0) for s in filtered_sessions)

            # Average Quiz Score
            quiz_pcts = [float(q["percentage"] or 0.0) for q in filtered_quizzes]
            avg_quiz_score = round(sum(quiz_pcts) / len(quiz_pcts), 1) if quiz_pcts else 0.0

            insights = {
                "today_focus": today_focus,
                "need_revision": weakest_subject,
                "best_subject": strongest_subject,
                "weakest_subject": weakest_subject,
                "upcoming_deadline": upcoming_task,
                "longest_session_mins": longest_session,
                "average_quiz_score": avg_quiz_score
            }

            # ── 7. Learning Progress ──────────────────────────────────────────
            completed_plans = [p for p in filtered_plans if p.get("status") == "Completed"]
            completion_pct = round((len(completed_plans) / len(filtered_plans)) * 100, 1) if filtered_plans else 0.0

            progress = {
                "completion_percentage": completion_pct,
                "study_streak": int(profile.get("current_streak") or 0),
                "productivity_score": round((avg_quiz_score + float(profile.get("retention_score") or 0.0) + completion_pct) / 3.0, 1)
            }

            # ── 8. Performance ────────────────────────────────────────────────
            # Group weak topics
            wt_resp = client.table("weak_topics").select("*, subjects(subject_name)").eq("owner_id", user_id).execute()
            weak_topics_list = wt_resp.data or []
            filtered_wt = []
            for wt in weak_topics_list:
                if not subject_id or wt.get("subject_id") == subject_id:
                    subject_info = wt.get("subjects")
                    wt["subject_name"] = subject_info["subject_name"] if subject_info else "Unknown"
                    filtered_wt.append(wt)

            performance = {
                "quiz_accuracy": float(profile.get("overall_accuracy") or 0.00),
                "flashcard_retention": float(profile.get("retention_score") or 0.00),
                "weak_topics": filtered_wt
            }

            # ── 9. Study Activity Charts data ─────────────────────────────────
            # Daily study minutes for the last 7 days
            activity_days = []
            for i in range(6, -1, -1):
                d = (now - timedelta(days=i)).date()
                day_sessions = [s for s in filtered_sessions if cls._parse_datetime(s["completed_at"]).date() == d]
                mins = sum(int(s["duration_minutes"] or 0) for s in day_sessions)
                activity_days.append({"Date": d.strftime("%b %d"), "Minutes": mins})

            # Weekly study minutes for the last 4 weeks
            activity_weeks = []
            for i in range(3, -1, -1):
                w_end = now - timedelta(weeks=i)
                w_start = w_end - timedelta(days=7)
                week_sessions = [s for s in filtered_sessions if w_start <= cls._parse_datetime(s["completed_at"]) <= w_end]
                mins = sum(int(s["duration_minutes"] or 0) for s in week_sessions)
                activity_weeks.append({"Week": f"W-{i}", "Minutes": mins})

            activity = {
                "daily": activity_days,
                "weekly": activity_weeks
            }

            # ── 10. Subjects tabular statistics ────────────────────────────────
            subjects_stats = []
            for s in subjects:
                sub_id = s["id"]
                sub_docs = len([f for f in all_files if f.get("subject_id") == sub_id])
                sub_fc = len([f for f in all_fc if f.get("subject_id") == sub_id])
                sub_quizzes = len([q for q in all_quizzes if q.get("subject_id") == sub_id])
                sub_tasks = [t for t in all_plans if t.get("subject_id") == sub_id]
                sub_completed_tasks = [t for t in sub_tasks if t.get("status") == "Completed"]
                
                sub_progress = 0.0
                if sub_tasks:
                    sub_progress = round((len(sub_completed_tasks) / len(sub_tasks)) * 100, 1)

                subjects_stats.append({
                    "Subject": s["subject_name"],
                    "Progress": f"{sub_progress}%",
                    "Documents": sub_docs,
                    "Flashcards": sub_fc,
                    "Quizzes": sub_quizzes,
                    "Revision Tasks": len(sub_tasks)
                })

            subjects_data = {
                "list": subjects_stats
            }

            # ── 11. Smart timeline resolver ───────────────────────────────────
            timeline_items = []
            # Process audits
            for a in all_audits:
                timestamp = cls._parse_datetime(a["created_at"])
                if not timestamp:
                    continue
                
                # Check filter
                if start_date and timestamp < start_date:
                    continue

                act = a["action"]
                res_id = a["resource_id"]
                time_str = timestamp.strftime("%b %d, %H:%M")

                msg = ""
                if act == "FILE_UPLOADED":
                    fname = file_map.get(res_id, "Notes document")
                    msg = f"Uploaded notes: {fname}"
                elif act == "QUIZ_ATTEMPT_SAVED":
                    q = quiz_map.get(res_id, {})
                    sub_name = subject_map.get(q.get("subject_id"), "Study")
                    percentage = q.get("percentage", 0.0)
                    msg = f"Completed {sub_name} Quiz - {percentage}%"
                elif act == "FLASHCARD_REVIEWED":
                    msg = "Reviewed flashcard sessional deck"
                elif act == "REVISION_TASK_COMPLETED":
                    title = plan_map.get(res_id, "Revision task")
                    msg = f"Completed revision task: {title}"
                elif act == "CHAT_CREATED":
                    msg = "Started a new AI notes chat session"
                elif act == "ACHIEVEMENT_UNLOCKED":
                    msg = f"🏆 Unlocked achievement: {res_id or 'Milestone'}"
                
                if msg:
                    timeline_items.append({
                        "time": time_str,
                        "timestamp": timestamp,
                        "activity": msg,
                        "type": "audit"
                    })

            # Process Pomodoro focus sessions directly as timeline events
            for s in filtered_sessions:
                timestamp = cls._parse_datetime(s["completed_at"])
                if not timestamp:
                    continue
                time_str = timestamp.strftime("%b %d, %H:%M")
                sub_name = subject_map.get(s.get("subject_id"), "General Focus")
                timeline_items.append({
                    "time": time_str,
                    "timestamp": timestamp,
                    "activity": f"Finished {s['duration_minutes']}-minute Pomodoro Focus cycle ({sub_name})",
                    "type": "pomodoro"
                })

            # Sort timeline by real timestamp desc
            timeline_items.sort(key=lambda x: x["timestamp"], reverse=True)

            # ── 12. Visual Achievements Progress Tracker ──────────────────────
            # Map default milestones to actual values
            milestones = [
                {
                    "title": "Study Beginner",
                    "metric": "Total Focus Hours",
                    "current": round(sum(int(s["duration_minutes"] or 0) for s in all_sessions) / 60.0, 1),
                    "target": 10.0,
                    "unlocked": "10 Hours Studied" in unlocked_types
                },
                {
                    "title": "Upload Master",
                    "metric": "Uploaded Notes Files",
                    "current": len(all_files),
                    "target": 20,
                    "unlocked": "20 Files Uploaded" in unlocked_types or len(all_files) >= 20
                },
                {
                    "title": "Quiz Scholar",
                    "metric": "Quizzes Completed",
                    "current": len(all_quizzes),
                    "target": 50,
                    "unlocked": "50 Quizzes" in unlocked_types
                },
                {
                    "title": "Streak Champion",
                    "metric": "Daily Study Streak",
                    "current": int(profile.get("current_streak") or 0),
                    "target": 7,
                    "unlocked": "7-Day Streak" in unlocked_types
                }
            ]
            for m in milestones:
                pct = min(100, int((m["current"] / m["target"]) * 100)) if m["target"] else 0
                m["percentage"] = pct

            return {
                "overview": overview,
                "goals": goals,
                "insights": insights,
                "progress": progress,
                "performance": performance,
                "activity": activity,
                "subjects": subjects_data,
                "timeline": timeline_items[:15], # Limit to recent 15
                "achievements": milestones,
                "recommendations": recs[:3]
            }

        except Exception as e:
            logger.error(f"Error compiling dashboard data: {e}")
            return cls._empty_payload()

    @classmethod
    def dismiss_recommendation(cls, rec_id: str) -> bool:
        """Update recommendation status in DB to Dismissed."""
        client = get_supabase_admin_client()
        if not client:
            return False
        try:
            resp = client.table("ai_recommendations").update({"status": "Dismissed"}).eq("id", rec_id).execute()
            return bool(resp.data)
        except Exception as e:
            logger.error(f"Failed to dismiss recommendation {rec_id}: {e}")
            return False

    @classmethod
    def _empty_payload(cls) -> Dict[str, Any]:
        return {
            "overview": {"study_time_hours": 0.0, "total_subjects": 0, "notes_uploaded": 0, "documents_processed": 0, "ai_chats": 0, "flashcards": 0, "quiz_attempts": 0, "revision_plans": 0},
            "goals": {"today_hours": 0.0, "today_goal": 3.0, "today_pct": 0, "week_hours": 0.0, "week_goal": 15.0, "week_pct": 0},
            "insights": {"today_focus": "None", "need_revision": "None", "best_subject": "None", "weakest_subject": "None", "upcoming_deadline": "None", "longest_session_mins": 0, "average_quiz_score": 0.0},
            "progress": {"completion_percentage": 0.0, "study_streak": 0, "productivity_score": 0.0},
            "performance": {"quiz_accuracy": 0.0, "flashcard_retention": 0.0, "weak_topics": []},
            "activity": {"daily": [], "weekly": []},
            "subjects": {"list": []},
            "timeline": [],
            "achievements": [],
            "recommendations": []
        }
