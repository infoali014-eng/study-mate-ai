from datetime import datetime
from pathlib import Path

import streamlit as st

from modules.auth import require_login
from modules.database import get_subjects, init_db, save_uploaded_document_metadata
from modules.document_processor import ocr_status, process_uploaded_file
from modules.security import validate_description, validate_upload
from modules.text_splitter import MAX_CHUNKS_PER_DOCUMENT, split_text
from modules.ui import (
    apply_theme,
    page_header,
    render_empty_state,
    render_file_badge,
    render_feature_card,
    render_success_state,
    section_title,
    sidebar_nav,
)
from modules.vector_store import VectorStoreError, add_text_chunks


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
EXTRACTED_TEXT_DIR = BASE_DIR / "data" / "extracted_text"


def build_unique_file_path(folder, file_name):
    """Create a PDF path that will not overwrite an older upload."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return folder / f"{timestamp}_{file_name}"


st.set_page_config(page_title="Upload Notes - StudyMate AI", layout="wide")
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

page_header(
    "Upload Notes",
    "Turn PDFs, images, DOCX, PPTX, TXT, and Markdown into searchable study material.",
    "Knowledge Builder",
)

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card("Many file types", "Upload PDFs, images, Word, PowerPoint, TXT, and Markdown.", "\U0001f4c4", "#14b8b4", "#d8fff6")
with feature2:
    render_feature_card("Smart extraction", "Extract selectable text, Office text, and OCR when available.", "\U0001f9e9", "#ff637d", "#ffe3e9")
with feature3:
    render_feature_card("Local memory", "Save vectors subject-wise in ChromaDB for offline AI search.", "\U0001f4be", "#8b5cf6", "#efe7ff")

subjects = get_subjects(user_id=user_id)
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
    st.info(f"OCR status: {ocr_status()}. Image/scanned notes may be limited if OCR is unavailable.")
    uploaded_file = st.file_uploader(
        "Upload study material",
        type=["pdf", "png", "jpg", "jpeg", "webp", "docx", "pptx", "txt", "md"],
    )

if uploaded_file:
    file_size_mb = uploaded_file.size / (1024 * 1024)
    selected_type = Path(uploaded_file.name).suffix.replace(".", "").upper()
    with st.container(border=True):
        st.markdown("**Selected material**")
        badge_col, info_col = st.columns([1, 4])
        with badge_col:
            render_file_badge(selected_type or "FILE")
        with info_col:
            st.markdown(f"**{uploaded_file.name}**")
            st.caption(f"{file_size_mb:.2f} MB ready for processing")

    if file_size_mb > 25:
        st.info(
            "Large document detected. StudyMate will save the original file, limit slow OCR, "
            "and index a capped set of chunks so the upload can finish reliably."
        )

    if st.button("Process Document", type="primary", use_container_width=True):
        safe_name, validation_error = validate_upload(uploaded_file)
        if validation_error:
            st.error(validation_error)
            st.stop()

        clean_description = validate_description(document_description)
        subject_folder = UPLOAD_DIR / str(user_id) / str(selected_subject["id"])
        text_subject_folder = EXTRACTED_TEXT_DIR / str(user_id) / str(selected_subject["id"])
        subject_folder.mkdir(parents=True, exist_ok=True)
        text_subject_folder.mkdir(parents=True, exist_ok=True)

        file_path = build_unique_file_path(subject_folder, safe_name)
        text_path = text_subject_folder / file_path.with_suffix(".txt").name
        file_type = Path(safe_name).suffix.replace(".", "").upper() or "PDF"

        progress = st.progress(0, text="Saving uploaded document...")
        file_path.write_bytes(uploaded_file.getbuffer())

        progress.progress(25, text="Extracting readable text...")
        process_result = process_uploaded_file(file_path, file_type)
        extracted_text = process_result["text"]
        warning_message = " ".join(process_result.get("warnings", []))

        text_path.write_text(extracted_text, encoding="utf-8")

        progress.progress(50, text="Splitting text into chunks...")
        chunks = split_text(extracted_text)
        warnings = list(process_result.get("warnings", []))
        if len(chunks) >= MAX_CHUNKS_PER_DOCUMENT:
            warnings.append(
                "This is a long document. To keep upload fast, StudyMate indexed the first "
                f"{MAX_CHUNKS_PER_DOCUMENT} searchable chunks. The original file and extracted "
                "text preview are still saved."
            )
        warning_message = " ".join(warnings)

        progress.progress(70, text="Saving document metadata in SQLite...")
        document_id = save_uploaded_document_metadata(
            subject_id=selected_subject["id"],
            file_name=safe_name,
            file_path=str(file_path),
            file_type=file_type,
            extracted_text_path=str(text_path),
            chunk_count=len(chunks),
            description=clean_description,
            extraction_method=process_result.get("method", ""),
            extraction_status=process_result.get("status", ""),
            warning_message=warning_message,
            page_count=process_result.get("page_count", 0),
            user_id=user_id,
        )

        if not document_id:
            progress.empty()
            st.error("Access denied. This subject does not belong to your account.")
            st.stop()

        progress.progress(85, text="Saving chunks into ChromaDB...")
        saved_count = 0
        if chunks:
            try:
                saved_count = add_text_chunks(
                    subject_id=selected_subject["id"],
                    subject_name=selected_subject["name"],
                    document_id=document_id,
                    file_name=safe_name,
                    chunks=chunks,
                    user_id=user_id,
                    file_type=file_type,
                    extraction_method=process_result.get("method", ""),
                )
            except VectorStoreError as exc:
                saved_count = 0
                st.warning("Search storage is unavailable right now. The document was still saved.")
                st.info(
                    "The document metadata and extracted text were saved, but searchable "
                    "chat/quiz/flashcard features need ChromaDB to be available."
                )

        progress.progress(100, text="Upload complete.")
        render_success_state(
            "Upload complete",
            f"{safe_name} is saved under {selected_subject['name']} and ready for StudyMate.",
        )
        if chunks:
            st.success(f"Saved {saved_count} searchable chunks into ChromaDB.")
        else:
            st.warning(
                "File uploaded, but no readable text was extracted. You can still preview it, "
                "but AI chat may not use its content."
            )
        for warning in warnings:
            st.warning(warning)

        with st.expander("Preview extracted text"):
            st.write(extracted_text[:3000] if extracted_text else "No extracted text available.")
