"""
Event Dispatcher service for StudyMate AI (Phase 4D).
Dispatches learning events (quizzes, flashcard reviews, pomodoro sessions)
to analytical and gamified achievement listeners.
"""

import logging
from typing import Any, Dict, List, Callable

logger = logging.getLogger("studymate.event_dispatcher")

# Registry mapping event keys to handler functions
_registry: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}

def register_listener(event_type: str, handler: Callable[[str, Dict[str, Any]], None]):
    """Register a callback listener for a learning event."""
    _registry.setdefault(event_type, []).append(handler)

def dispatch_event(event_type: str, owner_id: str, data: Dict[str, Any]):
    """Trigger the learning event, running all registered listeners sequentially."""
    logger.info(f"Dispatching event {event_type} for user {owner_id}...")
    
    # 1. Run local registered callbacks
    handlers = _registry.get(event_type, [])
    for handler in handlers:
        try:
            handler(owner_id, data)
        except Exception as e:
            logger.error(f"Error executing listener {handler.__name__} for event {event_type}: {e}")

    # 2. Invoke default system handlers directly
    try:
        _handle_default_system_events(event_type, owner_id, data)
    except Exception as e:
        logger.error(f"Error in default system handler for {event_type}: {e}")

def _handle_default_system_events(event_type: str, owner_id: str, data: Dict[str, Any]):
    """Execute built-in calculations for streaks, weak topics, and achievements."""
    from modules.analytics_repository import recalculate_profile_stats, check_achievements
    
    # Recalculate overall profile cached stats (streaks, accuracy, retention)
    recalculate_profile_stats(owner_id, event_type, data)
    
    # Check for unlocked achievements
    check_achievements(owner_id, event_type, data)
