"""
Memory Extractor service for StudyMate AI (Phase 4C).
Defines a pluggable pipeline for parsing student conversations, identifying
durable user preferences/facts, and storing them in the AI memory database.
"""

import re
import logging
from typing import Any, Dict, List

from modules.memory_repository import create_memory

logger = logging.getLogger("studymate.memory_extractor")

SENSITIVE_WORDS = {
    "password", "secret", "token", "key", "credential",
    "apikey", "session", "auth", "login", "card", "cvv"
}

class MemoryExtractionPipeline:
    """Pluggable memory extraction pipeline to identify user facts from messages."""
    def __init__(self, mode: str = "rule-based"):
        self.mode = mode

    def extract_and_save(self, user_id: str, message: str) -> List[str]:
        """
        Analyze message content, extract profile facts, save to DB,
        and return list of saved memory descriptions.
        """
        if not user_id or not message.strip():
            return []

        text = message.strip()
        lowered = text.lower()

        # Security check: avoid extracting credentials or secrets
        if any(word in lowered for word in SENSITIVE_WORDS):
            logger.info("Skipping memory extraction: message contains potential secrets.")
            return []

        if self.mode == "llm":
            return self._extract_via_llm(user_id, text)
        else:
            return self._extract_via_rules(user_id, text)

    def _extract_via_rules(self, user_id: str, text: str) -> List[str]:
        """Regex-based rule extraction matching profile preferences, language, goals, etc."""
        saved = []
        lowered = text.lower()

        # 1. Preferred Name
        name_match = re.search(
            r"\b(?:my name is|call me|i am|i'm)\s+([A-Za-z][A-Za-z .'-]{1,40}?)(?:[,.]| and | but |$)",
            text,
            flags=re.IGNORECASE,
        )
        if name_match and "weak" not in name_match.group(1).lower():
            candidate = name_match.group(1).strip()
            if len(candidate.split()) <= 4:
                mem_id = create_memory(user_id, "preferred_name", candidate, "preference", confidence=1.0)
                if mem_id:
                    saved.append(f"preferred_name: {candidate}")

        # 2. Language Preference
        language_patterns = [
            (r"\b(?:prefer|use|explain (?:me )?in|answer in)\s+(roman urdu)\b", "Roman Urdu"),
            (r"\b(?:prefer|use|explain (?:me )?in|answer in)\s+(mixed english\s*\+?\s*roman urdu)\b", "Mixed English + Roman Urdu"),
            (r"\b(?:prefer|use|explain (?:me )?in|answer in)\s+(simple english)\b", "Simple English"),
        ]
        for pattern, value in language_patterns:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                mem_id = create_memory(user_id, "language_preference", value, "preference", confidence=1.0)
                if mem_id:
                    saved.append(f"language_preference: {value}")
                break

        # 3. Answer Length Preference
        if re.search(r"\b(?:prefer|give|explain).{0,30}\bshort\b", lowered):
            mem_id = create_memory(user_id, "answer_style", "short exam-style answers", "learning_style", confidence=0.8)
            if mem_id:
                saved.append("answer_style: short exam-style answers")
        elif re.search(r"\b(?:prefer|give|answer).{0,30}\b(?:exam style|exam-style)\b", lowered):
            mem_id = create_memory(user_id, "answer_style", "exam-style answers", "learning_style", confidence=0.8)
            if mem_id:
                saved.append("answer_style: exam-style answers")

        # 4. Academic Weaknesses
        weak_match = re.search(
            r"\b(?:i am weak in|i'm weak in|weak in|i do not understand|i don't understand)\s+([A-Za-z0-9 +#_.-]{2,60})",
            text,
            flags=re.IGNORECASE,
        )
        if weak_match:
            topic = weak_match.group(1).strip(" .,!?:;")
            key_topic = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")[:50]
            if key_topic:
                mem_id = create_memory(user_id, f"weak_topic_{key_topic}", topic, "goal", confidence=0.7)
                if mem_id:
                    saved.append(f"weak_topic_{key_topic}: {topic}")

        # 5. Exam Schedules / Goals
        exam_match = re.search(
            r"\b(?:my exam is|exam is|i have exam|i have an exam)\s+([A-Za-z0-9 ,./-]{2,80})",
            text,
            flags=re.IGNORECASE,
        )
        if exam_match:
            exam_info = exam_match.group(1).strip(" .,!?:;")
            mem_id = create_memory(user_id, "exam_info", exam_info, "goal", confidence=0.9)
            if mem_id:
                saved.append(f"exam_info: {exam_info}")

        return saved

    def _extract_via_llm(self, user_id: str, text: str) -> List[str]:
        """Placeholder for future LLM-driven memory extraction."""
        # Can leverage ask_ai to retrieve JSON formatting of user facts
        # and create/update them dynamically.
        return self._extract_via_rules(user_id, text)
