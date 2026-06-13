import re
from datetime import datetime
from pathlib import Path

import streamlit as st

from modules.database import get_subjects, init_db, save_uploaded_document_metadata
from modules.pdf_reader import extract_text_from_pdf
from modules.text_splitter import split_text
from modules.ui import (
    apply_theme,
    page_header,
    render_empty_state,
    render_feature_card,
    section_title,
    sidebar_nav,
)
from modules.vector_store import add_text_chunks


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
EXTRACTED_TEXT_DIR = BASE_DIR / "data" / "extracted_text"


def safe_folder_name(name):
    """Turn a subject name into a safe folder name."""
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip())
    return safe.strip("_") or "subject"


def safe_file_name(file_name):
    """Keep uploaded file names safe for local storage."""
    path = Path(file_name)
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", path.stem).strip("_")
    safe_suffix = path.suffix.lower() or ".pdf"
    return f"{safe_stem or 'notes'}{safe_suffix}"


def build_unique_file_path(folder, file_name):
    """Create a PDF path that will not overwrite an older upload."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return folder / f"{timestamp}_{safe_file_name(file_name)}"


st.set_page_config(page_title="Upload Notes - StudyMate AI", layout="wide")
init_db()
apply_theme()
sidebar_nav()

page_header(
    "Upload Notes",
    "Turn PDF notes into searchable chunks for chat, quizzes, and flashcards.",
    "Knowledge Builder",
)

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card("PDF to text", "Extract readable text from uploaded notes with PyMuPDF.", "\U0001f4c4", "#14b8b4", "#d8fff6")
with feature2:
    render_feature_card("Smart chunks", "Split long notes into searchable study-sized pieces.", "\U0001f9e9", "#ff637d", "#ffe3e9")
with feature3:
    render_feature_card("Local memory", "Save vectors subject-wise in ChromaDB for offline AI search.", "\U0001f4be", "#8b5cf6", "#efe7ff")

subjects = get_subjects()
if not subjects:
    render_empty_state(
        "No subjects available.",
        "Create a subject from the Dashboard before uploading notes.",
        "\U0001f4da",
    )
    st.stop()

subject_options = {subject["name"]: subject for subject in subjects}
section_title("Upload Workspace", "\u2601\ufe0f")
with st.container(border=True):
    selected_name = st.selectbox("Choose subject", list(subject_options.keys()))
    selected_subject = subject_options[selected_name]
    document_description = st.text_area(
        "Document description",
        placeholder="Optional: Chapter name, lecture number, lab manual, or exam notes.",
        height=90,
    )
    uploaded_file = st.file_uploader("Upload a PDF or TXT file", type=["pdf", "txt"])

if uploaded_file:
    st.write(f"Selected file: `{uploaded_file.name}`")

    if st.button("Process Document", type="primary", use_container_width=True):
        subject_folder = UPLOAD_DIR / safe_folder_name(selected_subject["name"])
        text_subject_folder = EXTRACTED_TEXT_DIR / safe_folder_name(selected_subject["name"])
        subject_folder.mkdir(parents=True, exist_ok=True)
        text_subject_folder.mkdir(parents=True, exist_ok=True)

        file_path = build_unique_file_path(subject_folder, uploaded_file.name)
        text_path = text_subject_folder / file_path.with_suffix(".txt").name
        file_type = Path(uploaded_file.name).suffix.replace(".", "").upper() or "PDF"

        progress = st.progress(0, text="Saving uploaded document...")
        file_path.write_bytes(uploaded_file.getbuffer())

        progress.progress(25, text="Extracting readable text...")
        if file_type == "PDF":
            extracted_text = extract_text_from_pdf(file_path)
        elif file_type == "TXT":
            extracted_text = file_path.read_text(encoding="utf-8", errors="ignore")
        else:
            extracted_text = ""

        if not extracted_text:
            progress.empty()
            st.error("No readable text was found in this document.")
            st.stop()

        text_path.write_text(extracted_text, encoding="utf-8")

        progress.progress(50, text="Splitting text into chunks...")
        chunks = split_text(extracted_text)

        progress.progress(70, text="Saving document metadata in SQLite...")
        document_id = save_uploaded_document_metadata(
            subject_id=selected_subject["id"],
            file_name=uploaded_file.name,
            file_path=str(file_path),
            file_type=file_type,
            extracted_text_path=str(text_path),
            chunk_count=len(chunks),
            description=document_description,
        )

        progress.progress(85, text="Saving chunks into ChromaDB...")
        saved_count = add_text_chunks(
            subject_id=selected_subject["id"],
            subject_name=selected_subject["name"],
            document_id=document_id,
            file_name=uploaded_file.name,
            chunks=chunks,
        )

        progress.progress(100, text="Upload complete.")
        st.success(
            f"Uploaded `{uploaded_file.name}` for {selected_subject['name']} "
            f"and saved {saved_count} chunks into ChromaDB."
        )
        st.info(f"SQLite document id: {document_id}")

        with st.expander("Preview extracted text"):
            st.write(extracted_text[:3000])
