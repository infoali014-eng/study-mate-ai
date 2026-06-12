from pathlib import Path

import fitz


def extract_text_from_pdf(pdf_path):
    """Read a PDF with PyMuPDF and return all readable text."""
    path = Path(pdf_path)
    text_parts = []

    with fitz.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            page_text = page.get_text("text").strip()
            if page_text:
                text_parts.append(f"\n--- Page {page_number} ---\n{page_text}")

    return "\n".join(text_parts).strip()

