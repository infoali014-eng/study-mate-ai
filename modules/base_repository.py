"""
Base Repository module for StudyMate AI (Phase 4D).
Provides shared boilerplate logic, availability assertions,
error logging, and transaction boundaries.
"""

import logging
from typing import Any, Dict, List, Optional
from modules.user_repository import is_supabase_online

logger = logging.getLogger("studymate.base_repository")

class BaseRepository:
    """Base repository class with standard database validation helpers."""
    
    @staticmethod
    def is_online() -> bool:
        """Verify Supabase connection is healthy."""
        return is_supabase_online()

    @staticmethod
    def get_client():
        """Retrieve the administrative client handle."""
        from modules.supabase_client import get_supabase_admin_client
        return get_supabase_admin_client()

    @classmethod
    def check_ownership(cls, table: str, record_id: str, owner_id: str) -> bool:
        """Validate if the given user owns the database record."""
        if not cls.is_online():
            return False
        client = cls.get_client()
        if not client:
            return False
        try:
            resp = client.table(table).select("owner_id").eq("id", record_id).execute()
            if resp.data:
                return str(resp.data[0].get("owner_id")) == str(owner_id)
            return False
        except Exception as e:
            logger.error(f"Ownership check failed on {table} for {record_id}: {e}")
            return False
