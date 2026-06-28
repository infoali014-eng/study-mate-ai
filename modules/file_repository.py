"""
File Repository facade module for StudyMate AI (Phase 4B).
Handles Supabase Storage (user-uploads bucket), uploaded_files metadata,
and document_embeddings pgvector RAG search.
Defines a pluggable EmbeddingProvider architecture and background-ready document pipeline.
"""

import logging
import time
import os
import hashlib
import math
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import closing

from modules.user_repository import is_supabase_online, log_audit_event
from modules.text_splitter import split_text
from modules.document_processor import process_uploaded_file

logger = logging.getLogger("studymate.file_repository")

# =====================================================================
# PLUGGABLE EMBEDDING PROVIDERS
# =====================================================================
class EmbeddingProvider:
    """Base class for all embedding calculation providers."""
    def get_embedding(self, text: str) -> List[float]:
        raise NotImplementedError("Subclasses must implement get_embedding")

    def get_dimension(self) -> int:
        raise NotImplementedError("Subclasses must implement get_dimension")

    def get_model_name(self) -> str:
        raise NotImplementedError("Subclasses must implement get_model_name")


class HashEmbeddingProvider(EmbeddingProvider):
    """Default offline-friendly hash embedding provider (dimension 384)."""
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def get_embedding(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        words = text.lower().split()
        for word in words:
            digest = hashlib.sha256(word.encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % self.dimension
            vector[index] += 1.0

        length = math.sqrt(sum(v * v for v in vector))
        if length == 0:
            return vector
        return [v / length for v in vector]

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_name(self) -> str:
        return f"hash_{self.dimension}"


def get_embedding_provider() -> EmbeddingProvider:
    """
    Return the active embedding provider.
    Currently returns HashEmbeddingProvider, but is extensible to Gemini, OpenAI, or local sentence-transformers.
    """
    provider_name = os.getenv("STUDYMATE_EMBEDDING_PROVIDER", "hash")
    if provider_name == "hash":
        return HashEmbeddingProvider()
    else:
        return HashEmbeddingProvider()


# =====================================================================
# SUPABASE CLIENT HELPERS
# =====================================================================
def _get_client():
    from modules.supabase_client import get_supabase_admin_client
    return get_supabase_admin_client()


# =====================================================================
# REPOSITORY METHODS
# =====================================================================
def upload_file(
    owner_id: str,
    subject_id: str,
    file_name: str,
    file_data: bytes,
    mime_type: str
) -> Optional[str]:
    """
    Validate size and type, upload file to Supabase storage,
    and create an initial record in 'uploaded_files' table with UPLOADED status.
    """
    if not is_supabase_online():
        logger.error("Supabase offline. Cannot upload file.")
        return None

    client = _get_client()
    if not client:
        return None

    # Enforce constraints (25MB size limit)
    size_mb = len(file_data) / (1024 * 1024)
    if size_mb > 25:
        logger.warning(f"File upload rejected: {file_name} is {size_mb:.2f}MB (max limit: 25MB).")
        return None

    try:
        # 1. Upload to Supabase Storage bucket 'user-uploads' under {owner_id}/{file_name}
        storage_path = f"{owner_id}/{file_name}"
        logger.info(f"Uploading file '{file_name}' to user-uploads storage bucket...")
        
        # Determine content-type header
        options = {"content-type": mime_type, "upsert": "true"}
        client.storage.from_("user-uploads").upload(
            path=storage_path,
            file=file_data,
            file_options=options
        )

        # 2. Insert metadata record in 'uploaded_files' table
        meta_data = {
            "owner_id": owner_id,
            "subject_id": subject_id,
            "original_filename": file_name,
            "stored_filename": file_name,
            "file_type": Path(file_name).suffix.replace(".", "").upper() or "PDF",
            "file_size": len(file_data),
            "storage_path": storage_path,
            "storage_provider": "supabase",
            "processing_status": "UPLOADED",
            "embedding_status": "pending",
            "processing_version": "1.0",
            "embedding_model": get_embedding_provider().get_model_name(),
            "embedding_dimension": get_embedding_provider().get_dimension()
        }
        resp = client.table("uploaded_files").insert(meta_data).execute()
        if not resp.data:
            # Clean up uploaded storage object if metadata insertion fails
            client.storage.from_("user-uploads").remove([storage_path])
            return None

        file_uuid = resp.data[0]["id"]
        
        # 3. Create linked card entry in study_library
        lib_data = {
            "owner_id": owner_id,
            "subject_id": subject_id,
            "title": file_name,
            "description": "",
            "uploaded_file_id": file_uuid
        }
        client.table("study_library").insert(lib_data).execute()

        log_audit_event(owner_id, "FILE_UPLOADED", "uploaded_files", file_uuid)
        logger.info(f"File uploaded successfully. Metadata ID: {file_uuid}")
        return file_uuid

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return None


def download_file(file_uuid: str, owner_id: str) -> Optional[bytes]:
    """Retrieve file raw bytes from Supabase storage."""
    if not is_supabase_online():
        logger.error("Supabase offline. Cannot download file.")
        return None

    client = _get_client()
    if not client:
        return None

    try:
        meta = get_file(file_uuid, owner_id)
        if not meta:
            return None
            
        storage_path = meta.get("storage_path")
        logger.info(f"Downloading file from path: {storage_path}...")
        return client.storage.from_("user-uploads").download(storage_path)
    except Exception as e:
        logger.error(f"Download file failed: {e}")
        return None


def generate_signed_url(file_uuid: str, owner_id: str, expires_in: int = 3600) -> Optional[str]:
    """Generate a secure, expiring download URL for a file."""
    if not is_supabase_online():
        return None

    client = _get_client()
    if not client:
        return None

    try:
        meta = get_file(file_uuid, owner_id)
        if not meta:
            return None
            
        storage_path = meta.get("storage_path")
        resp = client.storage.from_("user-uploads").create_signed_url(storage_path, expires_in)
        return resp.get("signedURL") if isinstance(resp, dict) else resp
    except Exception as e:
        logger.error(f"Failed to generate signed URL: {e}")
        return None


def delete_file(file_uuid: str, owner_id: str) -> bool:
    """Delete storage object, metadata row, and linked embeddings."""
    if not is_supabase_online():
        logger.error("Supabase offline. Cannot delete file.")
        return False

    client = _get_client()
    if not client:
        return False

    try:
        meta = get_file(file_uuid, owner_id)
        if not meta:
            return False

        storage_path = meta.get("storage_path")
        
        # 1. Delete from Supabase Storage
        try:
            client.storage.from_("user-uploads").remove([storage_path])
        except Exception as se:
            logger.warning(f"Failed to delete storage file (might be missing): {se}")

        # 2. Delete document embeddings
        client.table("document_embeddings").delete().eq("uploaded_file_id", file_uuid).execute()

        # 3. Delete study_library entry
        client.table("study_library").delete().eq("uploaded_file_id", file_uuid).execute()

        # 4. Delete uploaded_files metadata
        client.table("uploaded_files").delete().eq("id", file_uuid).execute()

        # 5. Clean up SQLite references in study_library / local paths (Phase 4A transition fallback)
        try:
            from modules.database import get_connection
            with closing(get_connection()) as conn:
                conn.execute("DELETE FROM uploaded_documents WHERE id = ? OR supabase_id = ?", (file_uuid, file_uuid))
                conn.execute("DELETE FROM document_summaries WHERE document_id = ?", (file_uuid,))
                conn.commit()
        except Exception as se:
             logger.warning(f"Local SQLite transition cleanup warnings: {se}")

        log_audit_event(owner_id, "FILE_DELETED", "uploaded_files", file_uuid)
        logger.info(f"File and embeddings successfully deleted: {file_uuid}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        return False


# =====================================================================
# METADATA WRAPPERS
# =====================================================================
def get_file(file_uuid: str, owner_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve metadata for a single file."""
    if not is_supabase_online():
        return None

    client = _get_client()
    if not client:
        return None

    try:
        resp = client.table("uploaded_files").select("*").eq("id", file_uuid).eq("owner_id", owner_id).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.error(f"get_file metadata failed: {e}")
        return None


def get_user_files(owner_id: str, subject_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve list of files uploaded by a user."""
    if not is_supabase_online():
        return []

    client = _get_client()
    if not client:
        return []

    try:
        query = client.table("uploaded_files").select("*").eq("owner_id", owner_id)
        if subject_id:
            query = query.eq("subject_id", subject_id)
        resp = query.order("uploaded_at", desc=True).execute()
        return resp.data or []
    except Exception as e:
        logger.error(f"get_user_files failed: {e}")
        return []


def update_metadata(file_uuid: str, owner_id: str, updates: Dict[str, Any]) -> bool:
    """Update metadata fields of an uploaded file."""
    if not is_supabase_online():
        return False

    client = _get_client()
    if not client:
        return False

    try:
        client.table("uploaded_files").update(updates).eq("id", file_uuid).eq("owner_id", owner_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update metadata: {e}")
        return False


# =====================================================================
# DECOUPLED BACKGROUND-READY DOCUMENT PROCESSING SERVICE
# =====================================================================
def process_document_pipeline(file_uuid: str, owner_id: str) -> bool:
    """
    Decoupled background-ready document processing pipeline.
    Richer Lifecycle: UPLOADED -> PROCESSING -> OCR_RUNNING -> CHUNKING -> EMBEDDING -> READY
    Saves chunks and generated embeddings directly into Supabase.
    """
    t_start = time.time()
    logger.info(f"[PIPELINE] Starting process pipeline for file {file_uuid}...")

    # 1. Update status to PROCESSING
    update_metadata(file_uuid, owner_id, {"processing_status": "PROCESSING"})

    temp_path = None
    try:
        # Retrieve metadata
        meta = get_file(file_uuid, owner_id)
        if not meta:
            raise ValueError(f"File {file_uuid} metadata not found.")

        # Download raw bytes locally to a temp file for reading
        file_bytes = download_file(file_uuid, owner_id)
        if not file_bytes:
            raise ValueError("Download file bytes returned None.")

        # Determine file type
        file_type = meta.get("file_type", "PDF").upper()
        orig_name = meta.get("original_filename", "notes.pdf")

        # Save to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type.lower()}") as tf:
            tf.write(file_bytes)
            temp_path = Path(tf.name)

        # 2. Text Extraction & OCR Decision
        logger.info("[PIPELINE] Extracting text...")
        if file_type in {"PNG", "JPG", "JPEG", "WEBP", "BMP"}:
            update_metadata(file_uuid, owner_id, {"processing_status": "OCR_RUNNING"})

        process_result = process_uploaded_file(str(temp_path), file_type)
        extracted_text = process_result.get("text", "").strip()
        method = process_result.get("method", "text")
        page_count = process_result.get("page_count", 1)
        ocr_used = ("ocr" in method or file_type in {"PNG", "JPG", "JPEG", "WEBP"})

        if ocr_used:
             update_metadata(file_uuid, owner_id, {"processing_status": "OCR_RUNNING", "ocr_used": True})

        if not extracted_text:
             logger.warning("[PIPELINE] No text extracted from file.")

        # 3. Chunking
        logger.info("[PIPELINE] Chunking text...")
        update_metadata(file_uuid, owner_id, {"processing_status": "CHUNKING"})
        chunks = split_text(extracted_text)

        # 4. Generating Embeddings
        logger.info(f"[PIPELINE] Generating embeddings for {len(chunks)} chunks...")
        update_metadata(file_uuid, owner_id, {"processing_status": "EMBEDDING"})

        provider = get_embedding_provider()
        client = _get_client()

        # Delete any existing embeddings first (for retries)
        client.table("document_embeddings").delete().eq("uploaded_file_id", file_uuid).execute()

        # Insert chunks and embeddings in batches of 50 to prevent size overflows
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i : i + batch_size]
            embeddings_batch = []
            
            for idx, chunk in enumerate(batch_chunks):
                chunk_idx = i + idx
                vec = provider.get_embedding(chunk)
                
                # Estimate page number from page-split markings if available
                page_num = 1
                try:
                    parts = extracted_text.split(f"--- Page ")
                    if len(parts) > 1:
                        for p_idx, part in enumerate(parts):
                            if chunk in part:
                                page_num = int(part.split(" ---")[0].strip())
                                break
                except Exception:
                    pass

                embeddings_batch.append({
                    "uploaded_file_id": file_uuid,
                    "owner_id": owner_id,
                    "chunk_index": chunk_idx,
                    "text_chunk": chunk,
                    "embedding_model": provider.get_model_name(),
                    "embedding_vector": vec,
                    "page_number": page_num
                })

            if embeddings_batch:
                client.table("document_embeddings").insert(embeddings_batch).execute()

        # 5. Completed Successfully
        duration = round(time.time() - t_start, 2)
        logger.info(f"[PIPELINE] Completed successfully in {duration}s.")
        
        update_metadata(file_uuid, owner_id, {
            "processing_status": "READY",
            "embedding_status": "completed",
            "page_count": page_count,
            "text_length": len(extracted_text),
            "chunk_count": len(chunks),
            "processing_duration": duration,
            "ocr_used": ocr_used
        })

        # Save to SQLite local study_library metadata for backward page compatibility (Phase 4A transition bridge)
        try:
            from modules.database import get_connection
            with closing(get_connection()) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO uploaded_documents
                    (supabase_id, user_id, subject_id, file_name, file_path, file_type, chunk_count, page_count, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_uuid,
                        owner_id,
                        meta.get("subject_id"),
                        orig_name,
                        meta.get("storage_path"),
                        file_type,
                        len(chunks),
                        page_count,
                        meta.get("description", "")
                    )
                )
                conn.commit()
        except Exception as se:
            logger.warning(f"Local SQLite backward-compat insertion warning: {se}")

        log_audit_event(owner_id, "FILE_PROCESSED", "uploaded_files", file_uuid)
        return True

    except Exception as e:
        logger.error(f"[PIPELINE ERROR] Processing failed: {e}")
        duration = round(time.time() - t_start, 2)
        update_metadata(file_uuid, owner_id, {
            "processing_status": "FAILED",
            "embedding_status": "failed",
            "processing_duration": duration
        })
        return False

    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


# =====================================================================
# PGVECTOR VECTOR SIMILARITY SEARCH
# =====================================================================
def search_document(
    query: str,
    owner_id: str,
    subject_id: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search document chunks using pgvector match function.
    Returns format compatible with ChromaDB queries.
    """
    if not is_supabase_online():
        logger.warning("Supabase offline. Cannot run pgvector search.")
        return []

    client = _get_client()
    if not client:
        return []

    try:
        provider = get_embedding_provider()
        query_vector = provider.get_embedding(query)

        params = {
            "query_embedding": query_vector,
            "match_limit": limit,
            "filter_user_id": owner_id
        }
        if subject_id:
            params["filter_subject_id"] = subject_id

        logger.info(f"Querying match_document_embeddings on Supabase (Limit: {limit})...")
        resp = client.rpc("match_document_embeddings", params).execute()
        
        matches = []
        if resp.data:
            file_names = {}
            try:
                files_resp = client.table("uploaded_files").select("id, original_filename, file_type").eq("owner_id", owner_id).execute()
                for f in files_resp.data:
                    file_names[f["id"]] = (f["original_filename"], f["file_type"])
            except Exception:
                pass

            for r in resp.data:
                file_uuid = r["uploaded_file_id"]
                fname, ftype = file_names.get(file_uuid, ("notes", "PDF"))
                
                matches.append({
                    "text": r["text_chunk"],
                    "metadata": {
                        "user_id": owner_id,
                        "subject_id": subject_id,
                        "document_id": file_uuid,
                        "file_name": fname,
                        "file_type": ftype,
                        "chunk_index": r["chunk_index"],
                        "page_number": r["page_number"]
                    },
                    "distance": float(r["similarity"])
                })
        return matches

    except Exception as e:
        logger.error(f"pgvector search_document failed: {e}")
        return []
