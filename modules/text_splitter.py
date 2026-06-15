import os


MAX_CHUNKS_PER_DOCUMENT = int(os.getenv("STUDYMATE_MAX_CHUNKS_PER_DOCUMENT", "600"))


def split_text(text, chunk_size=900, overlap=150, max_chunks=MAX_CHUNKS_PER_DOCUMENT):
    """Split long text into small overlapping chunks for vector search.

    A chunk cap keeps very large documents from making uploads feel stuck while
    still indexing the most useful opening portion of the material.
    """
    cleaned_text = " ".join(text.split())
    if not cleaned_text:
        return []

    chunks = []
    start = 0

    while start < len(cleaned_text):
        if max_chunks and len(chunks) >= max_chunks:
            break

        end = start + chunk_size
        chunks.append(cleaned_text[start:end])
        start = end - overlap

        if start < 0:
            start = 0
        if start >= len(cleaned_text):
            break

    return chunks
