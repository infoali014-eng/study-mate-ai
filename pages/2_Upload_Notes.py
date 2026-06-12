import re
from datetime import datetime
from pathlib import Path

import streamlit as st

from modules.database import get_subjects, init_db, save_uploaded_document_metadata
from modules.pdf_reader import extract_text_from_pdf
from modules.text_splitter import split_text
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

st.sidebar.title("StudyMate AI")
st.sidebar.page_link("pages/1_Dashboard.py", label="Dashboard")
st.sidebar.page_link("pages/2_Upload_Notes.py", label="Upload Notes")
st.sidebar.page_link("pages/3_Chat_With_Notes.py", label="Chat With Notes")
st.sidebar.page_link("pages/4_Quiz_Mode.py", label="Quiz Mode")
st.sidebar.page_link("pages/5_Flashcards.py", label="Flashcards")
st.sidebar.page_link("pages/6_Revision_Planner.py", label="Revision Planner")

st.title("Upload Notes")
st.caption("Upload PDFs, extract text, and store searchable chunks locally.")

subjects = get_subjects()
if not subjects:
    st.warning("Create a subject from the Dashboard before uploading notes.")
    st.stop()

subject_options = {subject["name"]: subject for subject in subjects}
selected_name = st.selectbox("Choose subject", list(subject_options.keys()))
selected_subject = subject_options[selected_name]

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file:
    st.write(f"Selected file: `{uploaded_file.name}`")

    if st.button("Process PDF", type="primary", use_container_width=True):
        # Keep uploaded PDFs and extracted text organized by subject.
        subject_folder = UPLOAD_DIR / safe_folder_name(selected_subject["name"])
        text_subject_folder = EXTRACTED_TEXT_DIR / safe_folder_name(
            selected_subject["name"]
        )
        subject_folder.mkdir(parents=True, exist_ok=True)
        text_subject_folder.mkdir(parents=True, exist_ok=True)

        pdf_path = build_unique_file_path(subject_folder, uploaded_file.name)
        text_path = text_subject_folder / pdf_path.with_suffix(".txt").name

        progress = st.progress(0, text="Saving uploaded PDF...")
        pdf_path.write_bytes(uploaded_file.getbuffer())

        progress.progress(25, text="Extracting text with PyMuPDF...")
        extracted_text = extract_text_from_pdf(pdf_path)

        if not extracted_text:
            progress.empty()
            st.error("No readable text was found in this PDF.")
            st.stop()

        text_path.write_text(extracted_text, encoding="utf-8")

        progress.progress(50, text="Splitting text into chunks...")
        chunks = split_text(extracted_text)

        progress.progress(70, text="Saving document metadata in SQLite...")
        document_id = save_uploaded_document_metadata(
            subject_id=selected_subject["id"],
            file_name=uploaded_file.name,
            file_path=str(pdf_path),
            extracted_text_path=str(text_path),
            chunk_count=len(chunks),
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
