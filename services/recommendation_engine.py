"""
AI Recommendation Engine service for StudyMate AI (Phase 4D).
Analyzes quiz histories, spaced repetition intervals, and calendar deadlines
to generate versioned recommendations with confidence and priority ratings.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from modules.supabase_client import get_supabase_admin_client
from modules.user_repository import is_supabase_online, log_audit_event

logger = logging.getLogger("studymate.recommendation_engine")

class RecommendationEngine:
    """Generates and versions study recommendations using AI or rule-based fallback."""

    @classmethod
    def generate_recommendations(cls, owner_id: str) -> List[Dict[str, Any]]:
        """Analyze learning data, create versioned recommendations, and insert them into DB."""
        if not is_supabase_online():
            return cls._rule_based_fallback(owner_id)

        client = get_supabase_admin_client()
        if not client:
            return cls._rule_based_fallback(owner_id)

        try:
            # 1. Gather context
            # Weak topics
            wt_resp = client.table("weak_topics").select("topic, weakness_score, trend").eq("owner_id", owner_id).limit(5).execute()
            weak_topics = wt_resp.data or []

            # Upcoming planner deadlines
            plan_resp = client.table("revision_plans").select("title, planned_date, priority").eq("owner_id", owner_id).eq("status", "Pending").limit(3).execute()
            upcoming_plans = plan_resp.data or []

            # General analytics profile
            profile_resp = client.table("learning_profiles").select("*").eq("owner_id", owner_id).execute()
            profile = profile_resp.data[0] if profile_resp.data else {}

            # 2. Compile prompt
            prompt_parts = [
                "You are an expert AI tutor. Analyze the student study profile below and suggest 3 highly actionable study recommendations.",
                "Student Profile:",
                f"- Overall accuracy: {profile.get('overall_accuracy', 0.0)}%",
                f"- Flashcard retention: {profile.get('retention_score', 0.0)}%",
                f"- Study level: {profile.get('study_level', 'Beginner')}",
                "\nWeak Topics Tracker:",
            ]
            for topic in weak_topics:
                prompt_parts.append(f"  * {topic['topic']} (Score: {topic['weakness_score']}, Trend: {topic['trend']})")
                
            prompt_parts.append("\nUpcoming Planner Tasks:")
            for p in upcoming_plans:
                prompt_parts.append(f"  * {p['title']} (Planned Date: {p['planned_date']}, Priority: {p['priority']})")

            prompt_parts.append(
                "\nReturn exactly 3 recommendations. You MUST format your response as a valid JSON list of objects, where each object has fields: "
                '"recommendation", "reason", "priority" (choose High, Medium, or Low), and "confidence" (float between 0.0 and 1.0). '
                "Do not include quotes or formatting backticks around the json."
            )
            
            prompt_str = "\n".join(prompt_parts)

            # 3. Request LLM
            recommendations_json = []
            try:
                from modules import ai_engine
                answer = ai_engine.ask_ai(prompt_str)
                # Clean prompt formatting if LLM wraps in backticks
                if "```json" in answer:
                    answer = answer.split("```json")[1].split("```")[0].strip()
                elif "```" in answer:
                    answer = answer.split("```")[1].split("```")[0].strip()
                recommendations_json = json.loads(answer.strip())
            except Exception as e:
                logger.warning(f"AI recommendation call failed. Using rule-based fallback: {e}")
                return cls._rule_based_fallback(owner_id)

            # 4. Save and return versioned recommendations
            if recommendations_json and isinstance(recommendations_json, list):
                # Delete old Pending recommendations to avoid bloating
                client.table("ai_recommendations").delete().eq("owner_id", owner_id).eq("status", "Pending").execute()
                
                saved = []
                for rec in recommendations_json[:3]:
                    data = {
                        "owner_id": owner_id,
                        "recommendation": rec.get("recommendation", "Review weak study topics."),
                        "reason": rec.get("reason", "You have topics marked weak."),
                        "priority": rec.get("priority", "Medium"),
                        "confidence": float(rec.get("confidence", 0.85)),
                        "status": "Pending",
                        "created_at": datetime.utcnow().isoformat()
                    }
                    resp = client.table("ai_recommendations").insert(data).execute()
                    if resp.data:
                        saved.append(resp.data[0])
                
                log_audit_event(owner_id, "RECOMMENDATIONS_GENERATED", "ai_recommendations", f"{len(saved)} recs")
                return saved
                
            return cls._rule_based_fallback(owner_id)

        except Exception as e:
            logger.error(f"Error generating AI recommendations: {e}")
            return cls._rule_based_fallback(owner_id)

    @classmethod
    def _rule_based_fallback(cls, owner_id: str) -> List[Dict[str, Any]]:
        """Static rule-based backup recommendations if LLM provider fails."""
        logger.info("Triggered rule-based fallback recommendation generation.")
        client = get_supabase_admin_client()
        if not client:
            return []
        try:
            # Delete old Pending recommendations
            client.table("ai_recommendations").delete().eq("owner_id", owner_id).eq("status", "Pending").execute()
            
            recs = [
                {
                    "recommendation": "Review your weakest subject's notes.",
                    "reason": "Prioritizing weak subjects maximizes exam preparation gains.",
                    "priority": "High",
                    "confidence": 0.90
                },
                {
                    "recommendation": "Complete pending Revision Planner tasks.",
                    "reason": "Maintaining consistent study routines helps prevent cramming.",
                    "priority": "Medium",
                    "confidence": 0.80
                },
                {
                    "recommendation": "Start a fresh Pomodoro focus cycle.",
                    "reason": "Spaced breaks enhance long-term memory consolidation.",
                    "priority": "Medium",
                    "confidence": 0.75
                }
            ]
            saved = []
            for r in recs:
                r["owner_id"] = owner_id
                r["status"] = "Pending"
                r["created_at"] = datetime.utcnow().isoformat()
                resp = client.table("ai_recommendations").insert(r).execute()
                if resp.data:
                    saved.append(resp.data[0])
            return saved
        except Exception as e:
            logger.error(f"Fallback recommendations insertion failed: {e}")
            return []
