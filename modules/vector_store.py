import hashlib
import math
from pathlib import Path

import chromadb


BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "data" / "chroma"
COLLECTION_NAME = "study_notes"
VECTOR_SIZE = 384


def _client():
    """Return a persistent local ChromaDB client."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _collection():
    """Return the notes collection. Embeddings are supplied by our code."""
    return _client().get_or_create_collection(name=COLLECTION_NAME)


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


def add_text_chunks(subject_id, subject_name, document_id, file_name, chunks):
    """Store text chunks in ChromaDB with helpful metadata."""
    if not chunks:
        return 0

    collection = _collection()
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

    collection.upsert(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    return len(chunks)


def query_subject_notes(subject_id, question, limit=5):
    """Find the most relevant notes for a question in one subject."""
    collection = _collection()
    result = collection.query(
        query_embeddings=[_hash_embedding(question)],
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


def delete_subject_vectors(subject_id):
    """Delete all ChromaDB note chunks saved for one subject."""
    collection = _collection()
    collection.delete(where={"subject_id": int(subject_id)})
    return True


def delete_document_vectors(document_id):
    """Delete all ChromaDB note chunks saved for one uploaded document."""
    collection = _collection()
    collection.delete(where={"document_id": int(document_id)})
    return True
