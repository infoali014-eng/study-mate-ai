"""
Supabase client module for StudyMate AI (Phase 1).
Provides singleton initializations for the default client (Anon Key) and
admin client (Service Role Key), robust credentials loading, and database connectivity health checks.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple, Any

# Configure a module-specific logger
logger = logging.getLogger("studymate.supabase")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Global client singletons
_client_instance: Optional[Any] = None
_admin_client_instance: Optional[Any] = None


def load_supabase_credentials() -> Tuple[str, str, str]:
    """
    Load Supabase credentials from Streamlit Secrets or .env / environment variables.
    Priority: Streamlit Secrets > os.environ / .env
    Returns: (supabase_url, supabase_anon_key, supabase_service_role_key)
    """
    url = ""
    anon_key = ""
    service_role_key = ""

    # 1. Try Streamlit Secrets (for production/cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets is not None:
            url = st.secrets.get("SUPABASE_URL", "")
            anon_key = st.secrets.get("SUPABASE_ANON_KEY", "")
            service_role_key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    except Exception:
        pass

    # 2. Try OS environment variables
    if not url:
        url = os.getenv("SUPABASE_URL", "")
    if not anon_key:
        anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not service_role_key:
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # 3. Manual .env fallback (in case python-dotenv failed with colon separators)
    if not url or not anon_key or not service_role_key:
        base_dir = Path(__file__).resolve().parent.parent
        env_path = base_dir / ".env"
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    content = f.read()
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Split on the first occurrence of ':' or '='
                    if ":" in line:
                        parts = line.split(":", 1)
                    elif "=" in line:
                        parts = line.split("=", 1)
                    else:
                        continue

                    key = parts[0].strip()
                    val = parts[1].strip()
                    if key == "SUPABASE_URL" and not url:
                        url = val
                    elif key == "SUPABASE_ANON_KEY" and not anon_key:
                        anon_key = val
                    elif key == "SUPABASE_SERVICE_ROLE_KEY" and not service_role_key:
                        service_role_key = val
            except Exception as e:
                logger.debug(f"Failed to parse .env file manually: {e}")

    return url.strip(), anon_key.strip(), service_role_key.strip()


def validate_credentials() -> Tuple[bool, str]:
    """
    Validate that all required Supabase environment variables are present and non-empty.
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    url, anon_key, service_key = load_supabase_credentials()
    missing = []
    if not url:
        missing.append("SUPABASE_URL")
    if not anon_key:
        missing.append("SUPABASE_ANON_KEY")
    if not service_key:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")

    if missing:
        msg = f"Missing required Supabase environment variable(s): {', '.join(missing)}"
        logger.error(msg)
        return False, msg

    if not url.startswith(("http://", "https://")):
        msg = "SUPABASE_URL must start with http:// or https://"
        logger.error(msg)
        return False, msg

    logger.info("Supabase credentials validation: OK (all keys detected)")
    return True, ""


def get_supabase_client() -> Optional[Any]:
    """
    Return a cached singleton instance of the default Supabase Client.
    Uses the Anon Key. Under no circumstances does this use or expose the Service Role Key.
    Returns:
        Optional[Client]: Initialized client, or None if configuration is invalid.
    """
    global _client_instance
    if _client_instance is not None:
        return _client_instance

    url, anon_key, _ = load_supabase_credentials()
    if not url or not anon_key:
        logger.error("Cannot initialize Supabase client: missing URL or Anon Key.")
        return None

    try:
        from supabase import create_client
        _client_instance = create_client(url, anon_key)
        logger.info("Supabase client initialized (using Anon Key)")
        return _client_instance
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None


def get_supabase_admin_client() -> Optional[Any]:
    """
    Return a cached singleton instance of the server-side Supabase Admin Client.
    Uses the Service Role Key. This client is restricted to admin/server operations.
    Returns:
        Optional[Client]: Initialized admin client, or None if configuration is invalid.
    """
    global _admin_client_instance
    if _admin_client_instance is not None:
        return _admin_client_instance

    url, _, service_role_key = load_supabase_credentials()
    if not url or not service_role_key:
        logger.error("Cannot initialize Supabase admin client: missing URL or Service Role Key.")
        return None

    try:
        from supabase import create_client
        _admin_client_instance = create_client(url, service_role_key)
        logger.info("Supabase admin client initialized (using Service Role Key)")
        return _admin_client_instance
    except Exception as e:
        logger.error(f"Failed to create Supabase admin client: {e}")
        return None


def health_check() -> bool:
    """
    Perform a lightweight authenticated database test query to verify connectivity.
    Returns:
        bool: True if connection is active and database responds, False otherwise.
    """
    url, anon_key, _ = load_supabase_credentials()
    if not url or not anon_key:
        logger.warning("Supabase health check failed: missing credentials.")
        return False

    client = get_supabase_client()
    if client is None:
        logger.warning("Supabase health check failed: client could not be instantiated.")
        return False

    try:
        logger.info("Performing Supabase connection health check query...")
        # Query a dummy table '_connection_test'. Since the table does not exist,
        # a successful database connection will return a "relation does not exist" API error.
        # This confirms that authentication succeeded and Postgres responded.
        client.table("_connection_test").select("*").limit(1).execute()
        logger.info("Supabase connection health check passed.")
        return True
    except Exception as e:
        err_msg = str(e)
        # If the database responded that the relation (table) doesn't exist,
        # or it could not find it in the schema cache, it means we authenticated
        # successfully and reached PostgreSQL/PostgREST.
        if ("relation" in err_msg and "does not exist" in err_msg) or "PGRST205" in err_msg or "schema cache" in err_msg:
            logger.info("Supabase connection health check passed (database connection active).")
            return True

        if "401" in err_msg or "Unauthorized" in err_msg:
            logger.error("Supabase connection test failed: Invalid credentials (401 Unauthorized).")
        elif "timeout" in err_msg.lower():
            logger.error("Supabase connection test failed: Timeout during connection test.")
        else:
            logger.error(f"Supabase connection test failed: {err_msg}")

        logger.warning("Supabase unavailable (falling back to local SQLite).")
        return False


def is_supabase_available() -> bool:
    """
    Alias for health_check(). Check if Supabase is configured and reachable.
    Returns:
        bool: True if connection is successful, False otherwise.
    """
    return health_check()
