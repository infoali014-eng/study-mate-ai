"""
User Repository facade module for StudyMate AI (Phase 3).
Directs all user-related queries to Supabase when online, and falls back
to SQLite read-only operations when Supabase is offline.
"""

import base64
import hashlib
import logging
import os
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from passlib.hash import pbkdf2_sha256

# Import local SQLite utilities
from modules.database import get_connection, DB_PATH

logger = logging.getLogger("studymate.user_repository")

# Module-level online status cache (used when Streamlit session state is not available, e.g. FastAPI backend)
_supabase_online_status: Optional[bool] = None

# =====================================================================
# CONNECTION HEALTH AND STATUS HELPERS
# =====================================================================
def is_supabase_online() -> bool:
    """
    Check if Supabase is reachable, caching the status to prevent redundant network requests.
    Checks Streamlit session state first, then local module cache, then runs health check.
    """
    global _supabase_online_status
    
    # 1. Try Streamlit session state cache
    try:
        import streamlit as st
        if hasattr(st, "session_state") and "supabase_connection_status" in st.session_state:
            return bool(st.session_state.supabase_connection_status)
    except Exception:
        pass
        
    # 2. Try local module-level cache
    if _supabase_online_status is not None:
        return _supabase_online_status
        
    # 3. Fallback to direct client health check
    try:
        from modules.supabase_client import health_check
        _supabase_online_status = health_check()
        # Save to Streamlit session state if available
        try:
            import streamlit as st
            if hasattr(st, "session_state"):
                st.session_state.supabase_connection_status = _supabase_online_status
        except Exception:
            pass
        return _supabase_online_status
    except Exception as e:
        logger.warning(f"Error checking Supabase availability: {e}")
        _supabase_online_status = False
        return False


def _get_client():
    """Return default Supabase client (Anon Key)."""
    from modules.supabase_client import get_supabase_client
    return get_supabase_client()


def _get_admin_client():
    """Return administrative Supabase client (Service Role Key)."""
    from modules.supabase_client import get_supabase_admin_client
    return get_supabase_admin_client()


# =====================================================================
# AUDIT LOGGING HELPER
# =====================================================================
def log_audit_event(user_id: Optional[str], action: str, resource: str, resource_id: Optional[str] = None) -> None:
    """Record an audit trail event to Supabase when online."""
    if not is_supabase_online():
        logger.warning(f"[OFFLINE AUDIT] User: {user_id} | Action: {action} | Resource: {resource} ({resource_id})")
        return
        
    client = _get_admin_client()
    if not client:
        return
        
    try:
        # Load user ip and user agent if streamlit context is active
        ip_address = None
        user_agent = None
        try:
            import streamlit as st
            if hasattr(st, "context") and hasattr(st.context, "headers"):
                ip_address = st.context.headers.get("x-forwarded-for") or st.context.headers.get("remote-addr")
                user_agent = st.context.headers.get("user-agent")
        except Exception:
            pass

        data = {
            "user_id": str(user_id) if user_id else None,
            "action": action,
            "resource": resource,
            "resource_id": str(resource_id) if resource_id else None,
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        client.table("audit_logs").insert(data).execute()
        logger.info(f"[AUDIT] {action} on {resource} recorded successfully.")
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


# =====================================================================
# CORE AUTHENTICATION UTILITIES
# =====================================================================
def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-SHA256."""
    return pbkdf2_sha256.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password matches hash."""
    try:
        return pbkdf2_sha256.verify(password, password_hash or "")
    except Exception:
        return False


# =====================================================================
# USER CRUD OPERATIONS
# =====================================================================
def create_user(name: str, email: str, password_hash: str, auth_provider: str = "email", role: str = "student") -> Optional[str]:
    """
    Create a new user on Supabase.
    Initializes default user preferences. Does NOT shadow write to SQLite.
    """
    clean_email = (email or "").strip().lower()
    clean_name = (name or "").strip()
    
    if not is_supabase_online():
        logger.error("Cannot create user: Supabase is offline.")
        return None
        
    admin_client = _get_admin_client()
    if not admin_client:
        return None
        
    try:
        # 1. Insert user
        user_data = {
            "full_name": clean_name,
            "email": clean_email,
            "password_hash": password_hash,
            "is_admin": (role == "admin"),
            "is_active": True,
            "email_verified": False
        }
        response = admin_client.table("users").insert(user_data).execute()
        if not response.data:
            logger.error("Supabase user insert returned empty data.")
            return None
            
        new_user = response.data[0]
        user_uuid = new_user["id"]
        
        # 2. Create default preferences
        pref_data = {
            "id": user_uuid,
            "theme": "light",
            "language": "en",
            "sidebar_state": "expanded",
            "default_ai_provider": "Gemini",
            "default_model": "gemini-2.0-flash",
            "teach_me_level": "Normal",
            "voice_enabled": False,
            "notifications": True,
            "timezone": "UTC"
        }
        admin_client.table("user_preferences").insert(pref_data).execute()
        
        # 3. Log audit event
        log_audit_event(user_uuid, "ACCOUNT_CREATED", "users", user_uuid)
        logger.info(f"User {clean_email} successfully registered on Supabase (UUID: {user_uuid})")
        return user_uuid
    except Exception as e:
        logger.error(f"Failed to create user in Supabase: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user by email.
    Queries Supabase first, falling back to SQLite if offline.
    """
    clean_email = (email or "").strip().lower()
    if not clean_email:
        return None
        
    if not is_supabase_online():
        logger.warning(f"Supabase offline. Falling back to SQLite read for user email {clean_email}")
        return _sqlite_get_user_by_email(clean_email)
        
    client = _get_client()
    if not client:
        return _sqlite_get_user_by_email(clean_email)
        
    try:
        response = client.table("users").select("*").eq("email", clean_email).is_("deleted_at", "null").execute()
        if response.data:
            u = response.data[0]
            # Map Supabase fields to SQLite compatibility dict
            return {
                "id": u["id"], # UUID string
                "name": u["full_name"],
                "email": u["email"],
                "password_hash": u["password_hash"],
                "role": "admin" if u["is_admin"] else "student",
                "is_active": u["is_active"],
                "created_at": u["created_at"],
                "updated_at": u["updated_at"]
            }
        return None
    except Exception as e:
        logger.error(f"Supabase get_user_by_email error: {e}. Falling back to SQLite.")
        return _sqlite_get_user_by_email(clean_email)


def get_user_by_id(user_id: Any) -> Optional[Dict[str, Any]]:
    """
    Retrieve user by ID (UUID or SQLite Integer).
    Queries Supabase first, falling back to SQLite if offline or if ID is an integer.
    """
    if not user_id:
        return None
        
    is_uuid = False
    try:
        UUID(str(user_id))
        is_uuid = True
    except ValueError:
        pass
        
    # If it is an integer ID or if Supabase is offline, query SQLite directly
    if not is_uuid or not is_supabase_online():
        logger.warning(f"Querying local SQLite for user ID: {user_id}")
        return _sqlite_get_user_by_id(user_id)
        
    client = _get_client()
    if not client:
        return _sqlite_get_user_by_id(user_id)
        
    try:
        response = client.table("users").select("*").eq("id", str(user_id)).is_("deleted_at", "null").execute()
        if response.data:
            u = response.data[0]
            return {
                "id": u["id"],
                "name": u["full_name"],
                "email": u["email"],
                "password_hash": u["password_hash"],
                "role": "admin" if u["is_admin"] else "student",
                "is_active": u["is_active"],
                "created_at": u["created_at"],
                "updated_at": u["updated_at"]
            }
        return None
    except Exception as e:
        logger.error(f"Supabase get_user_by_id error: {e}. Falling back to SQLite.")
        return _sqlite_get_user_by_id(user_id)


def update_user(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update user profile on Supabase. Falls back to SQLite if offline."""
    if not is_supabase_online():
        logger.warning(f"Supabase offline. Updating profile locally in SQLite for ID {user_id}")
        return _sqlite_update_user(user_id, updates)
        
    client = _get_client()
    if not client:
        return _sqlite_update_user(user_id, updates)
        
    try:
        # Translate keys to Supabase column names
        translated = {}
        if "name" in updates:
            translated["full_name"] = updates["name"]
        if "email" in updates:
            translated["email"] = updates["email"]
        if "profile_picture" in updates:
            translated["profile_picture"] = updates["profile_picture"]
            
        response = client.table("users").update(translated).eq("id", str(user_id)).execute()
        if response.data:
            u = response.data[0]
            log_audit_event(user_id, "PROFILE_UPDATED", "users", user_id)
            return {
                "id": u["id"],
                "name": u["full_name"],
                "email": u["email"],
                "password_hash": u["password_hash"],
                "role": "admin" if u["is_admin"] else "student"
            }
        return None
    except Exception as e:
        logger.error(f"Supabase update_user error: {e}. Falling back to SQLite.")
        return _sqlite_update_user(user_id, updates)


def change_password(user_id: str, new_password_hash: str) -> bool:
    """Update password hash on Supabase. Falls back to SQLite if offline."""
    if not is_supabase_online():
        logger.warning(f"Supabase offline. Changing password locally in SQLite for ID {user_id}")
        return _sqlite_change_password(user_id, new_password_hash)
        
    client = _get_client()
    if not client:
        return _sqlite_change_password(user_id, new_password_hash)
        
    try:
        response = client.table("users").update({"password_hash": new_password_hash}).eq("id", str(user_id)).execute()
        if response.data:
            log_audit_event(user_id, "PASSWORD_CHANGED", "users", user_id)
            logger.info(f"Password changed successfully in Supabase for user {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Supabase change_password error: {e}. Falling back to SQLite.")
        return _sqlite_change_password(user_id, new_password_hash)


def delete_user(user_id: str) -> bool:
    """Soft delete user on Supabase. Falls back to SQLite if offline."""
    if not is_supabase_online():
         logger.warning(f"Supabase offline. Soft deleting user locally in SQLite for ID {user_id}")
         return _sqlite_delete_user(user_id)
         
    client = _get_client()
    if not client:
        return _sqlite_delete_user(user_id)
        
    try:
        now = datetime.utcnow().isoformat()
        response = client.table("users").update({"deleted_at": now, "is_active": False}).eq("id", str(user_id)).execute()
        if response.data:
            log_audit_event(user_id, "ACCOUNT_DELETED", "users", user_id)
            return True
        return False
    except Exception as e:
        logger.error(f"Supabase delete_user error: {e}. Falling back to SQLite.")
        return _sqlite_delete_user(user_id)


# =====================================================================
# USER PREFERENCES OPERATIONS
# =====================================================================
def get_user_preferences(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch preferences from Supabase, falling back to local mock settings if offline."""
    if not is_supabase_online():
        return {
            "id": user_id,
            "theme": "light",
            "language": "en",
            "sidebar_state": "expanded"
        }
        
    client = _get_client()
    if not client:
        return None
        
    try:
        response = client.table("user_preferences").select("*").eq("id", str(user_id)).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Supabase get_user_preferences error: {e}")
        return None


def update_user_preferences(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update preferences on Supabase."""
    if not is_supabase_online():
        return None
        
    client = _get_client()
    if not client:
        return None
        
    try:
        response = client.table("user_preferences").update(updates).eq("id", str(user_id)).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Supabase update_user_preferences error: {e}")
        return None


# =====================================================================
# AUTHENTICATION LOGISTICS (verify_user_login)
# =====================================================================
def verify_user_login(email: str, password: str, verify_password_callback: Any, hash_password_callback: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user.
    Validates credentials against Supabase when online, writing LOGIN_SUCCESS or LOGIN_FAILED audits.
    Fails over to SQLite when offline.
    """
    clean_email = (email or "").strip().lower()
    if not clean_email or not password:
        return None
        
    if not is_supabase_online():
        logger.warning(f"Supabase offline. Authenticating user {clean_email} against SQLite.")
        from modules.database import verify_user_login as sqlite_verify
        return sqlite_verify(clean_email, password, verify_password_callback, hash_password_callback)
        
    user = get_user_by_email(clean_email)
    if not user:
        log_audit_event(None, "LOGIN_FAILED", "auth", clean_email)
        return None
        
    if not user.get("is_active", True):
        logger.warning(f"Login rejected: user account {clean_email} is marked inactive.")
        log_audit_event(user["id"], "LOGIN_FAILED", "auth", "Account Inactive")
        return None
        
    # Check password match
    if verify_password_callback(password, user["password_hash"]):
        log_audit_event(user["id"], "LOGIN_SUCCESS", "auth", user["id"])
        # If the user is an admin, audit it
        if user["role"] == "admin":
            log_audit_event(user["id"], "ADMIN_LOGIN", "auth", user["id"])
        return user
        
    log_audit_event(user["id"], "LOGIN_FAILED", "auth", "Incorrect Password")
    return None


# =====================================================================
# REMEMBER ME SESSIONS (Supabase Table backed)
# =====================================================================
def _hash_token(token: str) -> str:
    """Generate SHA-256 hash of plaintext cookie token."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_remember_session(user_id: str, days: int = 30) -> str:
    """
    Generate and persist a remember token in Supabase.
    Falls back to SQLite if offline.
    """
    token = secrets.token_hex(32)
    token_hash = _hash_token(token)
    expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
    
    if not is_supabase_online():
        logger.warning(f"Supabase offline. Creating remember session locally in SQLite.")
        from modules.database import create_remember_session as sqlite_create
        return sqlite_create(user_id, days)
        
    client = _get_client()
    if not client:
        return ""
        
    try:
        data = {
            "user_id": str(user_id),
            "token_hash": token_hash,
            "expires_at": expires_at
        }
        client.table("remember_sessions").insert(data).execute()
        return token
    except Exception as e:
        logger.error(f"Failed to create remember session in Supabase: {e}")
        return ""


def get_user_by_remember_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Find user matching cookie token in Supabase.
    Falls back to SQLite if offline.
    """
    if not token:
        return None
        
    token_hash = _hash_token(token)
    
    if not is_supabase_online():
        logger.warning("Supabase offline. Resolving remember token locally from SQLite.")
        from modules.database import get_user_by_remember_token as sqlite_resolve
        return sqlite_resolve(token)
        
    client = _get_client()
    if not client:
        return None
        
    try:
        now = datetime.utcnow().isoformat()
        response = client.table("remember_sessions").select("*, users(*)").eq("token_hash", token_hash).gt("expires_at", now).execute()
        if response.data:
            session = response.data[0]
            u = session["users"]
            if u and u.get("is_active", True):
                # Update last used timestamp
                client.table("remember_sessions").update({"last_used_at": now}).eq("token_hash", token_hash).execute()
                log_audit_event(u["id"], "LOGIN_SUCCESS", "auth", "Remember-Me Cookie Autologin")
                return {
                    "id": u["id"],
                    "name": u["full_name"],
                    "email": u["email"],
                    "password_hash": u["password_hash"],
                    "role": "admin" if u["is_admin"] else "student",
                    "is_active": u["is_active"]
                }
        return None
    except Exception as e:
        logger.error(f"Supabase get_user_by_remember_token error: {e}. Falling back to SQLite.")
        from modules.database import get_user_by_remember_token as sqlite_resolve
        return sqlite_resolve(token)


def delete_remember_session(token: str) -> None:
    """
    Delete remember token from Supabase.
    Falls back to SQLite if offline.
    """
    if not token:
        return
        
    token_hash = _hash_token(token)
    
    if not is_supabase_online():
        from modules.database import delete_remember_session as sqlite_delete
        sqlite_delete(token)
        return
        
    client = _get_client()
    if not client:
        return
        
    try:
        client.table("remember_sessions").delete().eq("token_hash", token_hash).execute()
    except Exception as e:
        logger.error(f"Failed to delete remember session from Supabase: {e}")


# =====================================================================
# ADMIN CONTROLS & MANAGEMENT
# =====================================================================
def get_all_users_with_stats(search_text: str = "") -> List[Dict[str, Any]]:
    """
    Fetch all users from Supabase with stats (subject/document count) extracted from SQLite.
    Falls back to pure SQLite if offline.
    """
    if not is_supabase_online():
        logger.warning("Supabase offline. Fetching user overview from SQLite.")
        from modules.database import get_all_users_with_stats as sqlite_get_all
        return sqlite_get_all(search_text)
        
    client = _get_client()
    if not client:
        from modules.database import get_all_users_with_stats as sqlite_get_all
        return sqlite_get_all(search_text)
        
    try:
        # 1. Fetch counts from SQLite mapped by email
        sqlite_counts = {}
        try:
            with closing(get_connection()) as conn:
                rows = conn.execute("""
                    SELECT users.email, 
                           COUNT(DISTINCT subjects.id) as sub_count, 
                           COUNT(DISTINCT uploaded_documents.id) as doc_count
                    FROM users
                    LEFT JOIN subjects ON subjects.user_id = users.id AND subjects.is_deleted = 0
                    LEFT JOIN uploaded_documents ON uploaded_documents.user_id = users.id AND uploaded_documents.is_deleted = 0
                    GROUP BY users.email
                """).fetchall()
                for row in rows:
                    sqlite_counts[row["email"].lower().strip()] = (row["sub_count"], row["doc_count"])
        except Exception as se:
            logger.error(f"Failed to get user activity counts from SQLite: {se}")

        # 2. Query users from Supabase
        query = client.table("users").select("*").is_("deleted_at", "null")
        if search_text.strip():
            clean_search = search_text.strip()
            query = query.or_(f"full_name.ilike.%{clean_search}%,email.ilike.%{clean_search}%")
            
        response = query.order("created_at", desc=True).execute()
        
        users_list = []
        if response.data:
            for u in response.data:
                email_key = u["email"].lower().strip()
                counts = sqlite_counts.get(email_key, (0, 0))
                
                users_list.append({
                    "id": u["id"],
                    "name": u["full_name"],
                    "email": u["email"],
                    "role": "admin" if u["is_admin"] else "student",
                    "is_active": u["is_active"],
                    "created_at": u["created_at"],
                    "subject_count": counts[0],
                    "document_count": counts[1]
                })
        return users_list
    except Exception as e:
        logger.error(f"Supabase get_all_users_with_stats error: {e}. Falling back to SQLite.")
        from modules.database import get_all_users_with_stats as sqlite_get_all
        return sqlite_get_all(search_text)


def update_user_role(target_user_id: str, role: str, admin_user_id: str) -> Tuple[bool, str]:
    """Update role of a user on Supabase."""
    if not is_supabase_online():
        logger.warning("Supabase offline. Refusing to alter user roles.")
        return False, "Supabase is offline. Cannot update roles."
        
    client = _get_client()
    if not client:
        return False, "Database client initialization failed."
        
    # Check if admin
    admin = get_user_by_id(admin_user_id)
    if not admin or admin["role"] != "admin":
        return False, "Access denied."
        
    clean_role = role if role in {"student", "admin"} else "student"
    is_admin_flag = (clean_role == "admin")
    
    try:
        # Prevent disabling the last admin
        target = get_user_by_id(target_user_id)
        if not target:
            return False, "User not found."
            
        if target["role"] == "admin" and not is_admin_flag:
            # Count current admins on Supabase
            admin_count_resp = client.table("users").select("id", count="exact").eq("is_admin", True).is_("deleted_at", "null").execute()
            if admin_count_resp.count is not None and admin_count_resp.count <= 1:
                return False, "Cannot remove the last administrator."
                
        response = client.table("users").update({"is_admin": is_admin_flag}).eq("id", str(target_user_id)).execute()
        if response.data:
            log_audit_event(admin_user_id, "ADMIN_ACTION", "users", f"Role update to {clean_role} for user {target_user_id}")
            return True, "User role updated successfully."
        return False, "Update failed."
    except Exception as e:
        logger.error(f"Failed to update user role in Supabase: {e}")
        return False, f"Database error: {e}"


def set_user_active(target_user_id: str, is_active: bool, admin_user_id: str) -> Tuple[bool, str]:
    """Enable or disable user account status on Supabase."""
    if not is_supabase_online():
        logger.warning("Supabase offline. Refusing to alter user status.")
        return False, "Supabase is offline. Cannot alter active statuses."
        
    client = _get_client()
    if not client:
        return False, "Database client initialization failed."
        
    # Check if admin
    admin = get_user_by_id(admin_user_id)
    if not admin or admin["role"] != "admin":
        return False, "Access denied."
        
    try:
        # Prevent disabling the last admin
        target = get_user_by_id(target_user_id)
        if not target:
            return False, "User not found."
            
        if target["role"] == "admin" and not is_active:
            # Count active admins on Supabase
            admin_count_resp = client.table("users").select("id", count="exact").eq("is_admin", True).eq("is_active", True).is_("deleted_at", "null").execute()
            if admin_count_resp.count is not None and admin_count_resp.count <= 1:
                return False, "Cannot disable the last active administrator."
                
        response = client.table("users").update({"is_active": is_active}).eq("id", str(target_user_id)).execute()
        if response.data:
            action_label = "ENABLED" if is_active else "DISABLED"
            log_audit_event(admin_user_id, "ADMIN_ACTION", "users", f"Account {action_label} for user {target_user_id}")
            return True, f"User account successfully {action_label.lower()}."
        return False, "Update failed."
    except Exception as e:
        logger.error(f"Failed to set user active status in Supabase: {e}")
        return False, f"Database error: {e}"


# =====================================================================
# DEFAULT ADMIN USER BOOTSTRAPPER (ensure_admin_user)
# =====================================================================
def ensure_admin_user(password_hash_callback: Any) -> Optional[str]:
    """
    Ensure the bootstrap administrator account exists and is valid.
    Creates or updates the admin on Supabase. Falls back to SQLite if offline.
    """
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    admin_name = os.getenv("ADMIN_NAME", "").strip() or "Admin User"
    
    if not admin_email or not admin_password:
        return None
        
    if not is_supabase_online():
        logger.warning("Supabase offline. Running admin bootstrapper on local SQLite.")
        from modules.database import ensure_admin_user as sqlite_ensure
        return sqlite_ensure(password_hash_callback)
        
    admin_client = _get_admin_client()
    if not admin_client:
        return None
        
    try:
        password_hash = password_hash_callback(admin_password)
        
        # Check if admin exists in Supabase
        response = admin_client.table("users").select("*").eq("email", admin_email).is_("deleted_at", "null").execute()
        if response.data:
            # Update password/name if needed
            existing = response.data[0]
            admin_client.table("users").update({
                "full_name": admin_name,
                "password_hash": password_hash,
                "is_admin": True,
                "is_active": True
            }).eq("id", existing["id"]).execute()
            return existing["id"]
        else:
            # Create bootstrap admin
            insert_data = {
                "full_name": admin_name,
                "email": admin_email,
                "password_hash": password_hash,
                "is_admin": True,
                "is_active": True,
                "email_verified": True
            }
            ins_response = admin_client.table("users").insert(insert_data).execute()
            if ins_response.data:
                admin_uuid = ins_response.data[0]["id"]
                # Default preferences
                pref_data = {
                    "id": admin_uuid,
                    "theme": "light",
                    "language": "en"
                }
                admin_client.table("user_preferences").insert(pref_data).execute()
                log_audit_event(admin_uuid, "ACCOUNT_CREATED", "users", admin_uuid)
                logger.info(f"Bootstrap administrator {admin_email} successfully created in Supabase.")
                return admin_uuid
        return None
    except Exception as e:
         logger.error(f"Failed to bootstrap admin user in Supabase: {e}")
         return None


# =====================================================================
# READ-ONLY SQLITE FALLBACK IMPLEMENTATIONS
# =====================================================================
def _sqlite_get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    try:
        with closing(get_connection()) as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.error(f"SQLite fallback _sqlite_get_user_by_email failed: {e}")
    return None


def _sqlite_get_user_by_id(user_id: Any) -> Optional[Dict[str, Any]]:
    try:
        with closing(get_connection()) as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.error(f"SQLite fallback _sqlite_get_user_by_id failed: {e}")
    return None


def _sqlite_update_user(user_id: Any, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        set_clause = []
        params = []
        if "name" in updates:
            set_clause.append("name = ?")
            params.append(updates["name"])
        if not set_clause:
            return _sqlite_get_user_by_id(user_id)
            
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(set_clause)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        with closing(get_connection()) as conn:
            conn.execute(query, params)
            conn.commit()
        return _sqlite_get_user_by_id(user_id)
    except Exception as e:
        logger.error(f"SQLite fallback _sqlite_update_user failed: {e}")
    return None


def _sqlite_change_password(user_id: Any, password_hash: str) -> bool:
    try:
        with closing(get_connection()) as conn:
            conn.execute("UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (password_hash, user_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"SQLite fallback _sqlite_change_password failed: {e}")
    return False


def _sqlite_delete_user(user_id: Any) -> bool:
    try:
        with closing(get_connection()) as conn:
            conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"SQLite fallback _sqlite_delete_user failed: {e}")
    return False
