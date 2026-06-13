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


def add_text_chunks(subject_id, subject_name, document_id, file_name, chunks):
    """Store text chunks in ChromaDB with helpful metadata."""
    if not chunks:
        return 0

    ids = [
        f"subject-{subject_id}-document-{document_id}-chunk-{index}"
        for index in range(len(chunks))
    ]
    metadatas = [
        {
            "subject_id": int(subject_id),
            "subject_name": subject_name,
            "document_id": int(document_id),
            "file_name": file_name,
            "chunk_index": index,
        }
        for index in range(len(chunks))
    ]
    embeddings = [_hash_embedding(chunk) for chunk in chunks]

    try:
        collection = _collection()
        collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
            embeddings=embeddings,
        )
    except VectorStoreError:
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


def query_subject_notes(subject_id, question, limit=5):
    """Find the most relevant notes for a question in one subject."""
    query_embedding = _hash_embedding(question)

    try:
        collection = _collection()
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where={"subject_id": int(subject_id)},
        )

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
        records = [
            record
            for record in _read_fallback_records()
            if int(record.get("metadata", {}).get("subject_id", -1)) == int(subject_id)
        ]

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


def delete_subject_vectors(subject_id):
    """Delete all ChromaDB note chunks saved for one subject."""
    try:
        collection = _collection()
        collection.delete(where={"subject_id": int(subject_id)})
    except VectorStoreError:
        pass

    records = [
        record
        for record in _read_fallback_records()
        if int(record.get("metadata", {}).get("subject_id", -1)) != int(subject_id)
    ]
    _write_fallback_records(records)
    return True


def delete_document_vectors(document_id):
    """Delete all ChromaDB note chunks saved for one uploaded document."""
    try:
        collection = _collection()
        collection.delete(where={"document_id": int(document_id)})
    except VectorStoreError:
        pass

    records = [
        record
        for record in _read_fallback_records()
        if int(record.get("metadata", {}).get("document_id", -1)) != int(document_id)
    ]
    _write_fallback_records(records)
    return True
