import hashlib
import json
import math
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "data" / "chroma"
FALLBACK_DIR = BASE_DIR / "data" / "vector_fallback"
FALLBACK_FILE = FALLBACK_DIR / "study_notes.json"
COLLECTION_NAME = "study_notes"
VECTOR_SIZE = 384
VECTOR_BATCH_SIZE = int(os.getenv("STUDYMATE_VECTOR_BATCH_SIZE", "96"))


class VectorStoreError(Exception):
    """Raised when ChromaDB cannot be loaded or used."""


def _load_chromadb():
    """Import ChromaDB lazily so a cloud import issue does not crash every page."""
    try:
        os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
        import chromadb

        return chromadb
    except Exception as exc:
        raise VectorStoreError(
            "ChromaDB could not start on this deployment. "
            "Use Python 3.11 and reinstall requirements, then restart the app."
        ) from exc


def _client():
    """Return a persistent local ChromaDB client."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    chromadb = _load_chromadb()
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _collection():
    """Return the notes collection. Embeddings are supplied by our code."""
    return _client().get_or_create_collection(name=COLLECTION_NAME)


def _read_fallback_records():
    """Read fallback vector records from a small local JSON file."""
    if not FALLBACK_FILE.exists():
        return []

    try:
        return json.loads(FALLBACK_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise VectorStoreError(
            "The fallback vector store could not be read. Please clear app data and retry."
        ) from exc


def _write_fallback_records(records):
    """Write fallback vector records to disk."""
    try:
        FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
        FALLBACK_FILE.write_text(json.dumps(records), encoding="utf-8")
    except OSError as exc:
        raise VectorStoreError(
            "The fallback vector store could not be saved on this deployment."
        ) from exc


def _hash_embedding(text):
    """
    Create a simple local embedding without downloading any model.

    This keeps the app offline. It is not as smart as a neural embedding model,
    but it is good enough for a beginner-friendly local search baseline.
    """
    vector = [0.0] * VECTOR_SIZE
    words = text.lower().split()

    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % VECTOR_SIZE
        vector[index] += 1.0

    length = math.sqrt(sum(value * value for value in vector))
    if length == 0:
        return vector
    return [value / length for value in vector]


def _cosine_distance(left, right):
    """Return a small distance for similar normalized vectors."""
    similarity = sum(a * b for a, b in zip(left, right))
    return 1.0 - similarity


def _safe_user_id(user_id):
    """Return an integer user id for metadata filters."""
    if user_id is None:
        return None
    return int(user_id)


def add_text_chunks(
    subject_id,
    subject_name,
    document_id,
    file_name,
    chunks,
    user_id=None,
    file_type="",
    extraction_method="",
):
    """Store text chunks in ChromaDB with helpful metadata."""
    if not chunks:
        return 0

    clean_user_id = _safe_user_id(user_id)
    if clean_user_id is None:
        raise VectorStoreError("Cannot save note chunks without a logged-in user.")

    ids = [
        f"user-{clean_user_id}-subject-{subject_id}-document-{document_id}-chunk-{index}"
        for index in range(len(chunks))
    ]
    metadatas = [
        {
            "user_id": clean_user_id,
            "subject_id": int(subject_id),
            "subject_name": subject_name,
            "document_id": int(document_id),
            "file_name": file_name,
            "file_type": file_type,
            "extraction_method": extraction_method,
            "chunk_index": index,
        }
        for index in range(len(chunks))
    ]
    embeddings = [_hash_embedding(chunk) for chunk in chunks]

    try:
        collection = _collection()
        for start in range(0, len(ids), VECTOR_BATCH_SIZE):
            end = start + VECTOR_BATCH_SIZE
            collection.upsert(
                ids=ids[start:end],
                documents=chunks[start:end],
                metadatas=metadatas[start:end],
                embeddings=embeddings[start:end],
            )
    except Exception:
        records = _read_fallback_records()
        existing_ids = set(ids)
        records = [record for record in records if record.get("id") not in existing_ids]

        for chunk_id, chunk, metadata, embedding in zip(ids, chunks, metadatas, embeddings):
            records.append(
                {
                    "id": chunk_id,
                    "document": chunk,
                    "metadata": metadata,
                    "embedding": embedding,
                }
            )

        _write_fallback_records(records)

    return len(chunks)


def _build_chroma_filter(subject_id=None, document_ids=None, user_id=None):
    """Build a ChromaDB metadata filter for subject and document selection."""
    filters = []

    if user_id is not None:
        filters.append({"user_id": int(user_id)})

    if subject_id is not None:
        filters.append({"subject_id": int(subject_id)})

    if document_ids:
        clean_ids = [int(document_id) for document_id in document_ids]
        if len(clean_ids) == 1:
            filters.append({"document_id": clean_ids[0]})
        else:
            filters.append({"document_id": {"$in": clean_ids}})

    if not filters:
        return None

    if len(filters) == 1:
        return filters[0]

    return {"$and": filters}


def query_subject_notes(subject_id, question, limit=5, document_ids=None, user_id=None):
    """Find the most relevant notes for a question in one subject/doc filter."""
    if user_id is None:
        return []

    query_embedding = _hash_embedding(question)
    chroma_filter = _build_chroma_filter(
        subject_id=subject_id,
        document_ids=document_ids,
        user_id=user_id,
    )

    try:
        collection = _collection()
        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": limit,
        }
        if chroma_filter:
            query_kwargs["where"] = chroma_filter

        result = collection.query(**query_kwargs)

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        matches = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            matches.append(
                {
                    "text": document,
                    "metadata": metadata,
                    "distance": distance,
                }
            )
        return matches
    except VectorStoreError:
        clean_document_ids = {int(document_id) for document_id in document_ids or []}
        records = []
        for record in _read_fallback_records():
            metadata = record.get("metadata", {})

            if user_id is not None and int(metadata.get("user_id", -1)) != int(user_id):
                continue

            if subject_id is not None and int(metadata.get("subject_id", -1)) != int(subject_id):
                continue

            if clean_document_ids and int(metadata.get("document_id", -1)) not in clean_document_ids:
                continue

            records.append(record)

        scored_records = []
        for record in records:
            distance = _cosine_distance(query_embedding, record.get("embedding", []))
            scored_records.append((distance, record))

        scored_records.sort(key=lambda item: item[0])
        return [
            {
                "text": record.get("document", ""),
                "metadata": record.get("metadata", {}),
                "distance": distance,
            }
            for distance, record in scored_records[:limit]
        ]


def delete_subject_vectors(subject_id, user_id=None):
    """Delete all ChromaDB note chunks saved for one subject."""
    if user_id is None:
        return False

    where = _build_chroma_filter(subject_id=subject_id, user_id=user_id)
    try:
        collection = _collection()
        collection.delete(where=where)
    except Exception:
        pass

    try:
        records = [
            record
            for record in _read_fallback_records()
            if not (
                int(record.get("metadata", {}).get("subject_id", -1)) == int(subject_id)
                and (
                    user_id is None
                    or int(record.get("metadata", {}).get("user_id", -1)) == int(user_id)
                )
            )
        ]
        _write_fallback_records(records)
    except Exception:
        pass

    return True


def delete_document_vectors(document_id, user_id=None):
    """Delete all ChromaDB note chunks saved for one uploaded document."""
    if user_id is None:
        return False

    where = _build_chroma_filter(document_ids=[document_id], user_id=user_id)
    try:
        collection = _collection()
        collection.delete(where=where)
    except Exception:
        pass

    try:
        records = [
            record
            for record in _read_fallback_records()
            if not (
                int(record.get("metadata", {}).get("document_id", -1)) == int(document_id)
                and (
                    user_id is None
                    or int(record.get("metadata", {}).get("user_id", -1)) == int(user_id)
                )
            )
        ]
        _write_fallback_records(records)
    except Exception:
        pass

    return True
