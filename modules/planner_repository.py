"""
Planner Repository module for StudyMate AI (Phase 4D).
Handles Supabase revision plans, task completions, progress updates, and rescheduled dates.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, date

from modules.base_repository import BaseRepository
from services.event_dispatcher import dispatch_event
from modules.user_repository import log_audit_event

logger = logging.getLogger("studymate.planner_repository")

class PlannerRepository(BaseRepository):
    """Repository managing revision plans, calendar entries, and progress logs."""
    
    @classmethod
    def create_revision_plan(
        cls,
        owner_id: str,
        subject_id: str,
        title: str = "Revision Task",
        description: Optional[str] = None,
        priority: str = "medium",
        planned_date: Optional[date] = None,
        estimated_duration: int = 0,
        exam_date: Optional[date] = None,
        preparation_level: int = 5,
        confidence_level: int = 5,
        plan_text: Optional[str] = None,
        weak_topics: Optional[str] = None
    ) -> Optional[str]:
        """Create a new revision task or standard plan row in Supabase."""
        if not cls.is_online():
            return None
        client = cls.get_client()
        if not client:
            return None
        try:
            data = {
                "owner_id": owner_id,
                "subject_id": subject_id,
                "title": title.strip(),
                "description": description.strip() if description else "",
                "priority": priority,
                "planned_date": (planned_date or date.today()).isoformat(),
                "estimated_duration": estimated_duration,
                "status": "Pending",
                "completion_percentage": 0.00,
                # Compatibility fields
                "exam_date": exam_date.isoformat() if exam_date else None,
                "preparation_level": preparation_level,
                "confidence_level": confidence_level,
                "plan_text": plan_text,
                "weak_topics": weak_topics,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            resp = client.table("revision_plans").insert(data).execute()
            if resp.data:
                plan_uuid = resp.data[0]["id"]
                log_audit_event(owner_id, "REVISION_PLAN_CREATED", "revision_plans", plan_uuid)
                return plan_uuid
            return None
        except Exception as e:
            logger.error(f"Failed to create revision plan: {e}")
            return None

    @classmethod
    def get_revision_plans(cls, owner_id: str, subject_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve revision plans for a user, newest first."""
        if not cls.is_online():
            return []
        client = cls.get_client()
        if not client:
            return []
        try:
            q = client.table("revision_plans").select("*, subjects(name)").eq("owner_id", owner_id)
            if subject_id:
                q = q.eq("subject_id", subject_id)
            resp = q.order("created_at", desc=True).execute()
            
            # Map subjects.name into flat structure for page compatibility
            results = []
            for row in (resp.data or []):
                subject_info = row.get("subjects")
                row["subject_name"] = subject_info.get("name") if subject_info else "Unknown Subject"
                results.append(row)
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve revision plans: {e}")
            return []

    @classmethod
    def update_progress(cls, owner_id: str, plan_id: str, completion_percentage: float) -> bool:
        """Update the percentage completion status of a planner task."""
        if not cls.is_online():
            return False
        client = cls.get_client()
        if not client:
            return False
        try:
            status = "Pending"
            if completion_percentage >= 100.0:
                status = "Completed"
            elif completion_percentage > 0.0:
                status = "In Progress"
                
            updates = {
                "completion_percentage": round(completion_percentage, 2),
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            resp = client.table("revision_plans").update(updates).eq("id", plan_id).eq("owner_id", owner_id).execute()
            return bool(resp.data)
        except Exception as e:
            logger.error(f"Failed to update revision plan progress: {e}")
            return False

    @classmethod
    def complete_task(cls, owner_id: str, plan_id: str, actual_duration: int = 0) -> bool:
        """Mark a task complete and dispatch a completion learning event."""
        if not cls.is_online():
            return False
        client = cls.get_client()
        if not client:
            return False
        try:
            updates = {
                "completion_percentage": 100.00,
                "status": "Completed",
                "completed_date": date.today().isoformat(),
                "actual_duration": actual_duration,
                "updated_at": datetime.utcnow().isoformat()
            }
            resp = client.table("revision_plans").update(updates).eq("id", plan_id).eq("owner_id", owner_id).execute()
            if resp.data:
                # Dispatch task completed event
                dispatch_event("REVISION_TASK_COMPLETED", owner_id, {
                    "plan_id": plan_id,
                    "subject_id": resp.data[0]["subject_id"],
                    "duration": actual_duration
                })
                log_audit_event(owner_id, "REVISION_TASK_COMPLETED", "revision_plans", plan_id)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to complete task: {e}")
            return False

    @classmethod
    def reschedule_task(cls, owner_id: str, plan_id: str, new_date: date) -> bool:
        """Reschedule a task planned date."""
        if not cls.is_online():
            return False
        client = cls.get_client()
        if not client:
            return False
        try:
            updates = {
                "planned_date": new_date.isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            resp = client.table("revision_plans").update(updates).eq("id", plan_id).eq("owner_id", owner_id).execute()
            return bool(resp.data)
        except Exception as e:
            logger.error(f"Failed to reschedule task: {e}")
            return False

    @classmethod
    def delete_plan(cls, owner_id: str, plan_id: str) -> bool:
        """Delete a plan task from Supabase."""
        if not cls.is_online():
            return False
        client = cls.get_client()
        if not client:
            return False
        try:
            resp = client.table("revision_plans").delete().eq("id", plan_id).eq("owner_id", owner_id).execute()
            return bool(resp.data)
        except Exception as e:
            logger.error(f"Failed to delete plan: {e}")
            return False

    @classmethod
    def calculate_completion(cls, owner_id: str, subject_id: Optional[str] = None) -> float:
        """Calculate overall task completion rate (percentage of completed tasks)."""
        plans = cls.get_revision_plans(owner_id, subject_id)
        if not plans:
            return 0.0
        completed = sum(1 for p in plans if p["status"] == "Completed")
        return round((completed / len(plans)) * 100, 2)
