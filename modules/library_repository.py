"""
Library Repository facade module for StudyMate AI (Phase 4A).
Directs all Subject and Study Library (Notes metadata) queries to Supabase when online,
and falls back to SQLite read-only operations when Supabase is offline.
Bypasses Supabase Storage/uploaded_files table until Phase 4B.
"""

import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

# Import SQLite connection utilities
from modules.database import get_connection, DB_PATH
from modules.user_repository import is_supabase_online, log_audit_event

logger = logging.getLogger("studymate.library_repository")

def _ensure_sqlite_schema():
    try:
        with closing(get_connection()) as conn:
            cursor = conn.execute("PRAGMA table_info(uploaded_documents)")
            cols_doc = [row[1] for row in cursor.fetchall()]
            if "supabase_id" not in cols_doc:
                logger.info("Altering SQLite uploaded_documents table to add supabase_id column...")
                conn.execute("ALTER TABLE uploaded_documents ADD COLUMN supabase_id TEXT;")
                conn.commit()
                
            cursor = conn.execute("PRAGMA table_info(subjects)")
            cols_subj = [row[1] for row in cursor.fetchall()]
            if "supabase_id" not in cols_subj:
                logger.info("Altering SQLite subjects table to add supabase_id column...")
                conn.execute("ALTER TABLE subjects ADD COLUMN supabase_id TEXT;")
                conn.commit()
    except Exception as e:
        logger.error(f"Failed to ensure SQLite schema: {e}")

_ensure_sqlite_schema()

# =====================================================================
# UTILITIES AND CLIENT ACCESS
# =====================================================================
def _get_client():
    """Return default Supabase client redirected to admin client to bypass RLS in the repo facade."""
    from modules.supabase_client import get_supabase_admin_client
    return get_supabase_admin_client()


def _get_admin_client():
    """Return administrative Supabase client (Service Role Key)."""
    from modules.supabase_client import get_supabase_admin_client
    return get_supabase_admin_client()


# =====================================================================
# SUBJECT CRUD OPERATIONS
# =====================================================================
def add_subject(name: str, description: str = "", user_id: Any = None, group_id: Any = None) -> Optional[str]:
    """
    Add a subject for the current user.
    Creates in Supabase if online, blocks writes if offline.
    """
    if not user_id:
        return None
        
    if not is_supabase_online():
        logger.warning("Supabase offline. Cannot write subject to SQLite fallback.")
        return None
        
    admin_client = _get_admin_client()
    if not admin_client:
        return None
        
    clean_name = (name or "").strip()
    clean_desc = (description or "").strip()
    
    try:
        data = {
            "owner_id": str(user_id),
            "subject_name": clean_name,
            "description": clean_desc
        }
        response = admin_client.table("subjects").insert(data).execute()
        if response.data:
            subj_uuid = response.data[0]["id"]
            log_audit_event(user_id, "SUBJECT_CREATED", "subjects", subj_uuid)
            logger.info(f"Subject '{clean_name}' created in Supabase (UUID: {subj_uuid})")
            return subj_uuid
        return None
    except Exception as e:
        logger.error(f"Failed to create subject in Supabase: {e}")
        return None


def create_subject(name: str, description: str = "", user_id: Any = None) -> bool:
    """Compatibility wrapper for dashboard page. Returns True if created successfully."""
    return add_subject(name, description, user_id=user_id) is not None


def get_subjects(user_id: Any = None) -> List[Dict[str, Any]]:
    """
    Retrieve subjects for the current user.
    Queries Supabase first, falling back to SQLite read if offline.
    """
    if not user_id:
        return []
        
    if not is_supabase_online():
        logger.warning(f"Supabase offline. Reading subjects from SQLite fallback for user {user_id}")
        return _sqlite_get_subjects(user_id)
        
    client = _get_client()
    if not client:
        return _sqlite_get_subjects(user_id)
        
    try:
        response = client.table("subjects").select("*").eq("owner_id", str(user_id)).is_("deleted_at", "null").order("created_at", desc=True).execute()
        subjects = []
        if response.data:
            # Look up study group names from SQLite for compatibility
            group_names = {}
            try:
                with closing(get_connection()) as conn:
                    rows = conn.execute("SELECT id, name FROM study_groups").fetchall()
                    for r in rows:
                        group_names[r["id"]] = r["name"]
            except Exception:
                pass

            for s in response.data:
                # Map Supabase columns to SQLite keys
                subjects.append({
                    "id": s["id"],
                    "user_id": s["owner_id"],
                    "name": s["subject_name"],
                    "description": s["description"],
                    "created_at": s["created_at"],
                    "is_deleted": 0,
                    "group_id": None,
                    "group_name": None
                })
        return subjects
    except Exception as e:
        logger.error(f"Supabase get_subjects error: {e}. Falling back to SQLite.")
        return _sqlite_get_subjects(user_id)


def get_subject(subject_id: Any, user_id: Any = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve details of a single subject.
    Queries Supabase first, falling back to SQLite read if offline.
    """
    if not user_id or not subject_id:
        return None
        
    if not is_supabase_online():
        logger.warning(f"Supabase offline. Reading subject {subject_id} from SQLite fallback.")
        return _sqlite_get_subject(subject_id, user_id)
        
    client = _get_client()
    if not client:
        return _sqlite_get_subject(subject_id, user_id)
        
    try:
        response = client.table("subjects").select("*").eq("id", str(subject_id)).eq("owner_id", str(user_id)).is_("deleted_at", "null").execute()
        if response.data:
            s = response.data[0]
            return {
                "id": s["id"],
                "user_id": s["owner_id"],
                "name": s["subject_name"],
                "description": s["description"],
                "created_at": s["created_at"],
                "is_deleted": 0,
                "group_id": None,
                "group_name": None
            }
        return None
    except Exception as e:
        logger.error(f"Supabase get_subject error: {e}. Falling back to SQLite.")
        return _sqlite_get_subject(subject_id, user_id)


def delete_subject(subject_id: Any, user_id: Any = None) -> bool:
    """
    Delete a subject.
    Deletes in Supabase if online (blocks if offline).
    Cleans up associated items in SQLite (flashcards, quiz results) to maintain integrity.
    """
    if not user_id or not subject_id:
        return False
        
    if not is_supabase_online():
        logger.warning("Supabase offline. Cannot delete subject during SQLite fallback.")
        return False
        
    admin_client = _get_admin_client()
    if not admin_client:
        return False
        
    try:
        # Check ownership
        if not subject_belongs_to_user(subject_id, user_id):
            logger.warning(f"Access denied: Subject {subject_id} does not belong to user {user_id}")
            return False
            
        # 1. Soft-delete subject in Supabase
        now = datetime.utcnow().isoformat()
        admin_client.table("subjects").update({"deleted_at": now}).eq("id", str(subject_id)).execute()
        
        # 2. Delete related documents from study_library in Supabase
        admin_client.table("study_library").delete().eq("subject_id", str(subject_id)).execute()
        
        # 3. Cascade cleanups in local SQLite (flashcards, quizzes, and file paths)
        _sqlite_cascade_delete_subject(subject_id, user_id)
        
        log_audit_event(user_id, "SUBJECT_DELETED", "subjects", subject_id)
        return True
    except Exception as e:
        logger.error(f"Failed to delete subject in Supabase: {e}")
        return False


def subject_belongs_to_user(subject_id: Any, user_id: Any) -> bool:
    """Check if subject belongs to user in Supabase (falling back to SQLite)."""
    if not subject_id or not user_id:
        return False
    if not is_supabase_online():
        return _sqlite_subject_belongs_to_user(subject_id, user_id)
        
    client = _get_client()
    if not client:
        return _sqlite_subject_belongs_to_user(subject_id, user_id)
        
    try:
        response = client.table("subjects").select("id").eq("id", str(subject_id)).eq("owner_id", str(user_id)).is_("deleted_at", "null").execute()
        return len(response.data) > 0
    except Exception:
        return _sqlite_subject_belongs_to_user(subject_id, user_id)


# =====================================================================
# STUDY LIBRARY (uploaded_documents) CRUD OPERATIONS
# =====================================================================
def save_uploaded_document_metadata(
    subject_id: Any,
    file_name: str,
    file_path: str,
    chunk_count: int = 0,
    extracted_text_path: str = "",
    file_type: str = "PDF",
    description: str = "",
    extraction_method: str = "",
    extraction_status: str = "",
    warning_message: str = "",
    page_count: int = 0,
    user_id: Any = None,
) -> Optional[str]:
    """
    Save library item metadata.
    Primary details are saved in Supabase 'study_library' table.
    File-specific metadata remains in local SQLite 'uploaded_documents' table.
    """
    if not user_id or not subject_id:
        return None
        
    if not is_supabase_online():
        logger.warning("Supabase offline. Cannot save document metadata in SQLite fallback.")
        return None
        
    admin_client = _get_admin_client()
    if not admin_client:
        return None
        
    # Verify subject ownership
    if not subject_belongs_to_user(subject_id, user_id):
        logger.warning(f"Access denied: Subject {subject_id} does not belong to user {user_id}")
        return None
        
    clean_title = (file_name or "").strip()
    clean_desc = (description or "").strip()
    
    try:
        # 1. Insert user-facing metadata into Supabase study_library
        lib_data = {
            "owner_id": str(user_id),
            "subject_id": str(subject_id),
            "title": clean_title,
            "description": clean_desc,
            "tags": []
        }
        lib_resp = admin_client.table("study_library").insert(lib_data).execute()
        if not lib_resp.data:
            return None
            
        doc_uuid = lib_resp.data[0]["id"]
        
        # 2. Save physical file details in SQLite uploaded_documents referencing Supabase doc_uuid
        with closing(get_connection()) as conn:
            conn.execute(
                """
                INSERT INTO uploaded_documents
                    (
                        supabase_id, user_id, subject_id, file_name, file_path, file_type,
                        extracted_text_path, chunk_count, extraction_method,
                        extraction_status, warning_message, page_count, description
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_uuid,
                    str(user_id),
                    str(subject_id),
                    clean_title,
                    file_path,
                    file_type.upper(),
                    extracted_text_path,
                    chunk_count,
                    extraction_method,
                    extraction_status,
                    warning_message,
                    int(page_count or 0),
                    clean_desc
                )
            )
            conn.commit()
            
        log_audit_event(user_id, "LIBRARY_ITEM_CREATED", "study_library", doc_uuid)
        logger.info(f"Library item '{clean_title}' saved on Supabase & SQLite (UUID: {doc_uuid})")
        return doc_uuid
    except Exception as e:
        logger.error(f"Failed to save document metadata: {e}")
        return None


def add_document(subject_id: Any, file_name: str, file_path: str, chunk_count: int, user_id: Any = None) -> Optional[str]:
    """Compatibility helper wrapper for upload page."""
    return save_uploaded_document_metadata(
        subject_id=subject_id,
        file_name=file_name,
        file_path=file_path,
        chunk_count=chunk_count,
        user_id=user_id
    )


def get_documents(subject_id: Any = None, user_id: Any = None) -> List[Dict[str, Any]]:
    """
    Retrieve document list for a user, optionally filtered by subject.
    Queries Supabase first for primary list, then attaches local SQLite file paths.
    """
    if not user_id:
        return []
        
    if not is_supabase_online():
        logger.warning(f"Supabase offline. Fallback reading documents from SQLite for user {user_id}")
        return _sqlite_get_documents(subject_id, user_id)
        
    client = _get_client()
    if not client:
        return _sqlite_get_documents(subject_id, user_id)
        
    try:
        # 1. Query Supabase study_library
        query = client.table("study_library").select("*, subjects(subject_name)").eq("owner_id", str(user_id))
        if subject_id:
            query = query.eq("subject_id", str(subject_id))
            
        response = query.order("created_at", desc=True).execute()
        
        # 2. Query SQLite file paths in bulk
        sqlite_files = {}
        try:
            with closing(get_connection()) as conn:
                rows = conn.execute("SELECT * FROM uploaded_documents WHERE is_deleted = 0").fetchall()
                for r in rows:
                    rd = dict(r)
                    key = rd.get("supabase_id") or str(rd.get("id"))
                    sqlite_files[key] = rd
        except Exception as se:
            logger.error(f"SQLite file path lookup failed: {se}")

        documents = []
        if response.data:
            for item in response.data:
                item_id = item["id"]
                file_info = sqlite_files.get(item_id, {})
                
                # Merge Supabase records with local SQLite file references
                documents.append({
                    "id": item_id,
                    "user_id": item["owner_id"],
                    "subject_id": item["subject_id"],
                    "subject_name": item["subjects"]["subject_name"] if item.get("subjects") else "General",
                    "file_name": item["title"],
                    "file_path": file_info.get("file_path", ""),
                    "file_type": file_info.get("file_type", "PDF"),
                    "extracted_text_path": file_info.get("extracted_text_path", ""),
                    "chunk_count": file_info.get("chunk_count", 0),
                    "page_count": file_info.get("page_count", 0),
                    "description": item["description"],
                    "uploaded_at": item["created_at"],
                    "is_deleted": 0
                })
        return documents
    except Exception as e:
        logger.error(f"Supabase get_documents error: {e}. Falling back to SQLite.")
        return _sqlite_get_documents(subject_id, user_id)


def get_documents_by_subject(subject_id: Any, user_id: Any = None) -> List[Dict[str, Any]]:
    """Return all uploaded documents for one owned subject."""
    return get_documents(subject_id=subject_id, user_id=user_id)


def get_all_documents(user_id: Any = None) -> List[Dict[str, Any]]:
    """Return all uploaded documents with their subject names."""
    return get_documents(user_id=user_id)


def get_document_by_id(document_id: Any, user_id: Any = None) -> Optional[Dict[str, Any]]:
    """Retrieve details of a single document."""
    if not user_id or not document_id:
        return None
        
    if not is_supabase_online():
        logger.warning(f"Supabase offline. Fallback reading document {document_id} from SQLite.")
        return _sqlite_get_document_by_id(document_id, user_id)
        
    client = _get_client()
    if not client:
        return _sqlite_get_document_by_id(document_id, user_id)
        
    try:
        response = client.table("study_library").select("*, subjects(subject_name)").eq("id", str(document_id)).eq("owner_id", str(user_id)).execute()
        if response.data:
            item = response.data[0]
            # Look up SQLite details
            file_info = {}
            try:
                with closing(get_connection()) as conn:
                    row = conn.execute(
                        "SELECT * FROM uploaded_documents WHERE supabase_id = ? OR id = ?",
                        (str(document_id), str(document_id))
                    ).fetchone()
                    if row:
                        file_info = dict(row)
            except Exception:
                pass
                
            return {
                "id": item["id"],
                "user_id": item["owner_id"],
                "subject_id": item["subject_id"],
                "subject_name": item["subjects"]["subject_name"] if item.get("subjects") else "General",
                "file_name": item["title"],
                "file_path": file_info.get("file_path", ""),
                "file_type": file_info.get("file_type", "PDF"),
                "extracted_text_path": file_info.get("extracted_text_path", ""),
                "chunk_count": file_info.get("chunk_count", 0),
                "page_count": file_info.get("page_count", 0),
                "description": item["description"],
                "uploaded_at": item["created_at"],
                "is_deleted": 0
            }
        return None
    except Exception as e:
        logger.error(f"Supabase get_document_by_id error: {e}. Falling back to SQLite.")
        return _sqlite_get_document_by_id(document_id, user_id)


def delete_document(document_id: Any, user_id: Any = None) -> bool:
    """Delete a document from Supabase and SQLite, purging local files."""
    if not user_id or not document_id:
        return False
        
    if not is_supabase_online():
        logger.warning("Supabase offline. Cannot delete document during SQLite fallback.")
        return False
        
    admin_client = _get_admin_client()
    if not admin_client:
        return False
        
    try:
        # Check ownership
        if not document_belongs_to_user(document_id, user_id):
            logger.warning(f"Access denied: Document {document_id} does not belong to user {user_id}")
            return False
            
        # 1. Fetch file paths for local disk deletion
        file_info = _sqlite_get_document_by_id(document_id, user_id)
        if file_info:
            from modules.database import _delete_file_if_inside_user_data
            _delete_file_if_inside_user_data(file_info.get("file_path"), user_id)
            _delete_file_if_inside_user_data(file_info.get("extracted_text_path"), user_id)
            
        # 2. Delete from Supabase study_library
        admin_client.table("study_library").delete().eq("id", str(document_id)).execute()
        
        # 3. Delete from SQLite uploaded_documents & summaries
        with closing(get_connection()) as conn:
            conn.execute("DELETE FROM document_summaries WHERE document_id = ? OR document_id IN (SELECT id FROM uploaded_documents WHERE supabase_id = ?)", (str(document_id), str(document_id)))
            conn.execute("DELETE FROM uploaded_documents WHERE supabase_id = ? OR id = ?", (str(document_id), str(document_id)))
            conn.commit()
            
        log_audit_event(user_id, "LIBRARY_ITEM_DELETED", "study_library", document_id)
        return True
    except Exception as e:
        logger.error(f"Failed to delete document in Supabase: {e}")
        return False


def get_document_count_by_subject(subject_id: Any, user_id: Any = None) -> int:
    """Return the number of uploaded documents for one owned subject."""
    if not user_id or not subject_id:
        return 0
        
    if not is_supabase_online():
        return _sqlite_get_document_count_by_subject(subject_id, user_id)
        
    client = _get_client()
    if not client:
        return _sqlite_get_document_count_by_subject(subject_id, user_id)
        
    try:
        response = client.table("study_library").select("id", count="exact").eq("subject_id", str(subject_id)).eq("owner_id", str(user_id)).execute()
        return response.count if response.count is not None else 0
    except Exception as e:
        logger.error(f"Supabase get_document_count_by_subject error: {e}. Falling back to SQLite.")
        return _sqlite_get_document_count_by_subject(subject_id, user_id)


def get_subject_document_counts(user_id: Any = None) -> List[Dict[str, Any]]:
    """Return each owned subject with its uploaded document count."""
    if not user_id:
        return []
        
    if not is_supabase_online():
        return _sqlite_get_subject_document_counts(user_id)
        
    client = _get_client()
    if not client:
        return _sqlite_get_subject_document_counts(user_id)
        
    try:
        subjects = get_subjects(user_id)
        for s in subjects:
            s["document_count"] = get_document_count_by_subject(s["id"], user_id)
        return subjects
    except Exception as e:
        logger.error(f"Supabase get_subject_document_counts error: {e}. Falling back to SQLite.")
        return _sqlite_get_subject_document_counts(user_id)


def document_belongs_to_user(document_id: Any, user_id: Any) -> bool:
    """Check if document belongs to user in Supabase (falling back to SQLite)."""
    if not document_id or not user_id:
        return False
    if not is_supabase_online():
        return _sqlite_document_belongs_to_user(document_id, user_id)
        
    client = _get_client()
    if not client:
        return _sqlite_document_belongs_to_user(document_id, user_id)
        
    try:
        response = client.table("study_library").select("id").eq("id", str(document_id)).eq("owner_id", str(user_id)).execute()
        return len(response.data) > 0
    except Exception:
        return _sqlite_document_belongs_to_user(document_id, user_id)


# =====================================================================
# SEARCH & PAGINATION (Supabase Core Queries)
# =====================================================================
def get_user_library(
    user_id: Any,
    subject_id: Any = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    sort_by: str = "uploaded_at",
    sort_order: str = "desc",
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Get user's study library items supporting sorting, filtering, and pagination.
    """
    if not user_id:
        return []
        
    if not is_supabase_online():
        return get_documents(subject_id, user_id)
        
    client = _get_client()
    if not client:
        return get_documents(subject_id, user_id)
        
    try:
        query = client.table("study_library").select("*, subjects(subject_name)").eq("owner_id", str(user_id))
        
        # Filters
        if subject_id:
            query = query.eq("subject_id", str(subject_id))
        if filters:
            for k, v in filters.items():
                query = query.eq(k, v)
                
        # Sorting
        sort_col = "created_at" if sort_by == "uploaded_at" else "title"
        query = query.order(sort_col, desc=(sort_order == "desc"))
        
        # Pagination
        if page is not None and page_size is not None:
            start = (page - 1) * page_size
            end = start + page_size - 1
            query = query.range(start, end)
            
        response = query.execute()
        
        # Fetch file refs from SQLite
        sqlite_files = {}
        try:
            with closing(get_connection()) as conn:
                rows = conn.execute("SELECT * FROM uploaded_documents WHERE is_deleted = 0").fetchall()
                for r in rows:
                    rd = dict(r)
                    key = rd.get("supabase_id") or str(rd.get("id"))
                    sqlite_files[key] = rd
        except Exception:
            pass

        documents = []
        if response.data:
            for item in response.data:
                item_id = item["id"]
                file_info = sqlite_files.get(item_id, {})
                documents.append({
                    "id": item_id,
                    "user_id": item["owner_id"],
                    "subject_id": item["subject_id"],
                    "subject_name": item["subjects"]["subject_name"] if item.get("subjects") else "General",
                    "file_name": item["title"],
                    "file_path": file_info.get("file_path", ""),
                    "file_type": file_info.get("file_type", "PDF"),
                    "extracted_text_path": file_info.get("extracted_text_path", ""),
                    "chunk_count": file_info.get("chunk_count", 0),
                    "page_count": file_info.get("page_count", 0),
                    "description": item["description"],
                    "uploaded_at": item["created_at"],
                    "is_deleted": 0
                })
        return documents
    except Exception as e:
        logger.error(f"Failed to query user library: {e}")
        return get_documents(subject_id, user_id)


def search_library(query: str, user_id: Any) -> List[Dict[str, Any]]:
    """
    Search library items by title or description case-insensitively.
    """
    if not user_id or not query:
        return get_documents(user_id=user_id)
        
    if not is_supabase_online():
         # Fallback to local SQLite filter
         docs = get_documents(user_id=user_id)
         q = query.strip().lower()
         return [d for d in docs if q in d["file_name"].lower() or q in d["description"].lower()]
         
    client = _get_client()
    if not client:
        return get_documents(user_id=user_id)
        
    try:
        clean_q = query.strip()
        response = client.table("study_library").select("*, subjects(subject_name)").eq("owner_id", str(user_id)).or_(f"title.ilike.%{clean_q}%,description.ilike.%{clean_q}%").order("created_at", desc=True).execute()
        
        # Load SQLite details
        sqlite_files = {}
        try:
            with closing(get_connection()) as conn:
                rows = conn.execute("SELECT * FROM uploaded_documents WHERE is_deleted = 0").fetchall()
                for r in rows:
                    rd = dict(r)
                    key = rd.get("supabase_id") or str(rd.get("id"))
                    sqlite_files[key] = rd
        except Exception:
            pass

        documents = []
        if response.data:
            for item in response.data:
                item_id = item["id"]
                file_info = sqlite_files.get(item_id, {})
                documents.append({
                    "id": item_id,
                    "user_id": item["owner_id"],
                    "subject_id": item["subject_id"],
                    "subject_name": item["subjects"]["subject_name"] if item.get("subjects") else "General",
                    "file_name": item["title"],
                    "file_path": file_info.get("file_path", ""),
                    "file_type": file_info.get("file_type", "PDF"),
                    "extracted_text_path": file_info.get("extracted_text_path", ""),
                    "chunk_count": file_info.get("chunk_count", 0),
                    "page_count": file_info.get("page_count", 0),
                    "description": item["description"],
                    "uploaded_at": item["created_at"],
                    "is_deleted": 0
                })
        return documents
    except Exception as e:
        logger.error(f"Supabase search_library error: {e}")
        return get_documents(user_id=user_id)


# =====================================================================
# ONE-TIME IDEMPOTENT SYNC MIGRATION UTILITY
# =====================================================================
def sync_sqlite_to_supabase(user_id: Any, dry_run: bool = False) -> Dict[str, Any]:
    """
    Idempotently migrates all subjects and document records from SQLite to Supabase.
    Performs dry-runs, skip duplicates, verifies parent keys, and handles rollbacks on failure.
    """
    report = {
        "subjects_migrated": 0,
        "subjects_skipped": 0,
        "documents_migrated": 0,
        "documents_skipped": 0,
        "errors": []
    }
    
    if not is_supabase_online():
        msg = "Cannot run sync: Supabase is offline."
        report["errors"].append(msg)
        logger.error(msg)
        return report
        
    admin_client = _get_admin_client()
    if not admin_client:
        msg = "Cannot run sync: Admin client initialization failed."
        report["errors"].append(msg)
        return report
        
    # Temporary mappings to link old SQLite subject IDs to Supabase UUIDs
    subject_mapping = {}
    inserted_subjects = []
    inserted_library_items = []
    
    try:
        # 1. Migrate Subjects
        logger.info(f"[MIGRATION] Fetching subjects from SQLite for user {user_id}...")
        sqlite_subjects = []
        with closing(get_connection()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM subjects WHERE is_deleted = 0").fetchall()
            sqlite_subjects = [dict(r) for r in rows]
            
        # Fetch existing subjects in Supabase to prevent duplicates
        supabase_subjects_resp = admin_client.table("subjects").select("id, subject_name").eq("owner_id", str(user_id)).is_("deleted_at", "null").execute()
        existing_subjects = {s["subject_name"].strip().lower(): s["id"] for s in supabase_subjects_resp.data} if supabase_subjects_resp.data else {}
        
        for subj in sqlite_subjects:
            subj_name = subj["name"].strip()
            subj_name_lower = subj_name.lower()
            old_subj_id = subj["id"]
            
            if subj_name_lower in existing_subjects:
                subj_uuid = existing_subjects[subj_name_lower]
                subject_mapping[old_subj_id] = subj_uuid
                report["subjects_skipped"] += 1
                logger.info(f"[MIGRATION] Subject '{subj_name}' already exists in Supabase. Mapped: {old_subj_id} -> {subj_uuid}")
            else:
                if not dry_run:
                    data = {
                        "owner_id": str(user_id),
                        "subject_name": subj_name,
                        "description": subj["description"]
                    }
                    response = admin_client.table("subjects").insert(data).execute()
                    if response.data:
                        subj_uuid = response.data[0]["id"]
                        subject_mapping[old_subj_id] = subj_uuid
                        inserted_subjects.append(subj_uuid)
                        report["subjects_migrated"] += 1
                        logger.info(f"[MIGRATION] Created subject '{subj_name}' in Supabase (UUID: {subj_uuid})")
                        
                        # Update references in SQLite child tables (using dry_run=False since we are writing)
                        with closing(get_connection()) as conn:
                            conn.execute("UPDATE subjects SET supabase_id = ? WHERE id = ?", (subj_uuid, old_subj_id))
                            conn.execute("UPDATE flashcards SET subject_id = ? WHERE subject_id = ?", (subj_uuid, old_subj_id))
                            conn.execute("UPDATE quiz_results SET subject_id = ? WHERE subject_id = ?", (subj_uuid, old_subj_id))
                            conn.execute("UPDATE revision_plans SET subject_id = ? WHERE subject_id = ?", (subj_uuid, old_subj_id))
                            conn.execute("UPDATE uploaded_documents SET subject_id = ? WHERE subject_id = ?", (subj_uuid, old_subj_id))
                            conn.commit()
                else:
                    report["subjects_migrated"] += 1
                    logger.info(f"[DRY-RUN] Subject '{subj_name}' would be migrated.")

        # 2. Migrate uploaded documents (notes metadata)
        logger.info(f"[MIGRATION] Fetching uploaded documents from SQLite...")
        sqlite_docs = []
        with closing(get_connection()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM uploaded_documents WHERE is_deleted = 0").fetchall()
            sqlite_docs = [dict(r) for r in rows]

        # Fetch existing library items in Supabase to prevent duplicates
        supabase_lib_resp = admin_client.table("study_library").select("id, title, subject_id").eq("owner_id", str(user_id)).execute()
        existing_lib = {(l["title"].strip().lower(), l["subject_id"]): l["id"] for l in supabase_lib_resp.data} if supabase_lib_resp.data else {}

        for doc in sqlite_docs:
            doc_title = doc["file_name"].strip()
            doc_title_lower = doc_title.lower()
            old_subj_id = doc["subject_id"]
            old_doc_id = doc["id"]
            
            # Resolve Supabase subject UUID
            new_subj_uuid = subject_mapping.get(old_subj_id)
            if not new_subj_uuid:
                # If subject exists as a UUID string already, check it
                try:
                    UUID(str(old_subj_id))
                    new_subj_uuid = str(old_subj_id)
                except ValueError:
                    msg = f"Skipping doc '{doc_title}': parent subject ID {old_subj_id} could not be resolved."
                    report["errors"].append(msg)
                    logger.error(msg)
                    continue

            key = (doc_title_lower, new_subj_uuid)
            if key in existing_lib:
                # Already exists
                report["documents_skipped"] += 1
                logger.info(f"[MIGRATION] Library item '{doc_title}' already exists. Skipping.")
            else:
                if not dry_run:
                    # 1. Insert into Supabase study_library
                    lib_data = {
                        "owner_id": str(user_id),
                        "subject_id": new_subj_uuid,
                        "title": doc_title,
                        "description": doc["description"]
                    }
                    lib_resp = admin_client.table("study_library").insert(lib_data).execute()
                    if lib_resp.data:
                        new_doc_uuid = lib_resp.data[0]["id"]
                        inserted_library_items.append(new_doc_uuid)
                        report["documents_migrated"] += 1
                        logger.info(f"[MIGRATION] Created library item '{doc_title}' in Supabase (UUID: {new_doc_uuid})")
                        
                        # 2. Update SQLite uploaded_documents ID to link it to Supabase UUID
                        with closing(get_connection()) as conn:
                            conn.execute("UPDATE document_summaries SET document_id = ? WHERE document_id = ? OR document_id IN (SELECT id FROM uploaded_documents WHERE supabase_id = ?)", (new_doc_uuid, old_doc_id, old_doc_id))
                            conn.execute(
                                "UPDATE uploaded_documents SET supabase_id = ?, subject_id = ? WHERE id = ?",
                                (new_doc_uuid, new_subj_uuid, old_doc_id)
                            )
                            conn.commit()
                else:
                    report["documents_migrated"] += 1
                    logger.info(f"[DRY-RUN] Library item '{doc_title}' would be migrated under subject {new_subj_uuid}.")
        
        logger.info(f"[MIGRATION] Completed successfully. Summary: {report}")
        return report
        
    except Exception as e:
        # ROLLBACK inserted items if error occurred during non-dry run
        logger.error(f"[MIGRATION ERROR] Migration failed: {e}. Initiating batch rollback...")
        report["errors"].append(f"Migration failed: {e}")
        
        if not dry_run:
            try:
                # Remove inserted library items
                for doc_id in inserted_library_items:
                    admin_client.table("study_library").delete().eq("id", doc_id).execute()
                # Remove inserted subjects
                for subj_id in inserted_subjects:
                    admin_client.table("subjects").delete().eq("id", subj_id).execute()
                logger.info("[MIGRATION ROLLBACK] Rollback successfully completed.")
            except Exception as re:
                logger.error(f"[MIGRATION ROLLBACK ERROR] Rollback failed: {re}")
                
        return report


# =====================================================================
# READ-ONLY SQLITE FALLBACK IMPLEMENTATIONS
# =====================================================================
def _sqlite_get_subjects(user_id: Any) -> List[Dict[str, Any]]:
    try:
        with closing(get_connection()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT s.*, sg.name AS group_name 
                FROM subjects s
                LEFT JOIN study_groups sg ON s.group_id = sg.id
                WHERE s.user_id = ? AND s.is_deleted = 0
                ORDER BY s.created_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"SQLite fallback _sqlite_get_subjects failed: {e}")
        return []


def _sqlite_get_subject(subject_id: Any, user_id: Any) -> Optional[Dict[str, Any]]:
    try:
        with closing(get_connection()) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT s.*, sg.name AS group_name 
                FROM subjects s
                LEFT JOIN study_groups sg ON s.group_id = sg.id
                WHERE s.id = ? AND s.user_id = ? AND s.is_deleted = 0
                """,
                (subject_id, user_id),
            ).fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.error(f"SQLite fallback _sqlite_get_subject failed: {e}")
        return None


def _sqlite_subject_belongs_to_user(subject_id: Any, user_id: Any) -> bool:
    try:
        with closing(get_connection()) as conn:
            row = conn.execute(
                "SELECT id FROM subjects WHERE id = ? AND user_id = ? AND is_deleted = 0",
                (subject_id, user_id),
            ).fetchone()
            return row is not None
    except Exception:
        return False


def _sqlite_get_documents(subject_id: Any, user_id: Any) -> List[Dict[str, Any]]:
    try:
        with closing(get_connection()) as conn:
            params = [user_id]
            where = "uploaded_documents.user_id = ? AND uploaded_documents.is_deleted = 0"
            if subject_id:
                where += " AND uploaded_documents.subject_id = ?"
                params.append(subject_id)
                
            rows = conn.execute(
                f"""
                SELECT uploaded_documents.*, subjects.name AS subject_name
                FROM uploaded_documents
                LEFT JOIN subjects ON subjects.id = uploaded_documents.subject_id
                WHERE {where}
                ORDER BY uploaded_documents.uploaded_at DESC
                """,
                params,
            ).fetchall()
            
            docs = []
            for r in rows:
                d = dict(r)
                # Map SQLite column names
                d["file_name"] = d["file_name"]
                d["uploaded_at"] = d["uploaded_at"]
                docs.append(d)
            return docs
    except Exception as e:
        logger.error(f"SQLite fallback _sqlite_get_documents failed: {e}")
        return []


def _sqlite_get_document_by_id(document_id: Any, user_id: Any) -> Optional[Dict[str, Any]]:
    try:
        with closing(get_connection()) as conn:
            row = conn.execute(
                """
                SELECT uploaded_documents.*, subjects.name AS subject_name
                FROM uploaded_documents
                LEFT JOIN subjects ON subjects.id = uploaded_documents.subject_id
                WHERE uploaded_documents.id = ? AND uploaded_documents.user_id = ? AND uploaded_documents.is_deleted = 0
                """,
                (document_id, user_id),
            ).fetchone()
            if row:
                return dict(row)
    except Exception as e:
         logger.error(f"SQLite fallback _sqlite_get_document_by_id failed: {e}")
         return None


def _sqlite_get_document_count_by_subject(subject_id: Any, user_id: Any) -> int:
    try:
        with closing(get_connection()) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM uploaded_documents WHERE subject_id = ? AND user_id = ? AND is_deleted = 0",
                (subject_id, user_id),
            ).fetchone()
            return row[0] if row else 0
    except Exception:
        return 0


def _sqlite_get_subject_document_counts(user_id: Any) -> List[Dict[str, Any]]:
    try:
        with closing(get_connection()) as conn:
            rows = conn.execute(
                """
                SELECT subjects.*, COUNT(uploaded_documents.id) AS document_count
                FROM subjects
                LEFT JOIN uploaded_documents
                    ON uploaded_documents.subject_id = subjects.id
                    AND uploaded_documents.user_id = ?
                    AND uploaded_documents.is_deleted = 0
                WHERE subjects.user_id = ? AND subjects.is_deleted = 0
                GROUP BY subjects.id
                ORDER BY subjects.created_at DESC
                """,
                (user_id, user_id),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"SQLite fallback _sqlite_get_subject_document_counts failed: {e}")
        return []


def _sqlite_document_belongs_to_user(document_id: Any, user_id: Any) -> bool:
    try:
        with closing(get_connection()) as conn:
            row = conn.execute(
                "SELECT id FROM uploaded_documents WHERE id = ? AND user_id = ? AND is_deleted = 0",
                (document_id, user_id),
            ).fetchone()
            return row is not None
    except Exception:
        return False


def _sqlite_cascade_delete_subject(subject_id: Any, user_id: Any) -> None:
    try:
        with closing(get_connection()) as conn:
            # Delete children
            conn.execute("DELETE FROM uploaded_documents WHERE subject_id = ? AND user_id = ?", (str(subject_id), str(user_id)))
            conn.execute("DELETE FROM quiz_results WHERE subject_id = ? AND user_id = ?", (str(subject_id), str(user_id)))
            conn.execute("DELETE FROM flashcards WHERE subject_id = ? AND user_id = ?", (str(subject_id), str(user_id)))
            conn.execute("DELETE FROM weak_topics WHERE subject_id = ? AND user_id = ?", (str(subject_id), str(user_id)))
            conn.execute("DELETE FROM revision_plans WHERE subject_id = ? AND user_id = ?", (str(subject_id), str(user_id)))
            conn.execute("DELETE FROM document_summaries WHERE subject_id = ? AND user_id = ?", (str(subject_id), str(user_id)))
            conn.execute("DELETE FROM subjects WHERE id = ? AND user_id = ?", (str(subject_id), str(user_id)))
            conn.commit()
    except Exception as e:
        logger.error(f"SQLite local cascade delete failed: {e}")
