def split_text(text, chunk_size=900, overlap=150):
    """Split long text into small overlapping chunks for vector search."""
    cleaned_text = " ".join(text.split())
    if not cleaned_text:
        return []

    chunks = []
    start = 0

    while start < len(cleaned_text):
        end = start + chunk_size
        chunks.append(cleaned_text[start:end])
        start = end - overlap

        if start < 0:
            start = 0
        if start >= len(cleaned_text):
            break

    return chunks

