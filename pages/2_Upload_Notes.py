from datetime import datetime
from pathlib import Path

import streamlit as st

from modules.auth import require_login
from modules.database import init_db
from modules.library_repository import get_subjects, save_uploaded_document_metadata
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
    render_feature_card("Many file types", "Upload PDFs, images, Word, PowerPoint, Excel, TXT, Markdown, CSV, and JSON.", "\U0001f4c4", "#14b8b4", "#d8fff6")
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

subject_options = {}
for s in subjects:
    if s["group_name"]:
        display_name = f"👥 [{s['group_name']}] {s['name']}"
    else:
        display_name = s['name']
    subject_options[display_name] = s

section_title("Upload Workspace", "upload-cloud")
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
        type=["pdf", "png", "jpg", "jpeg", "webp", "docx", "pptx", "ppt", "xlsx", "txt", "md", "csv", "json"],
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
        file_type = Path(safe_name).suffix.replace(".", "").upper() or "PDF"

        progress = st.progress(0, text="Uploading file to Supabase Storage...")
        from modules.file_repository import upload_file, process_document_pipeline, get_file, update_metadata
        
        file_uuid = upload_file(
            owner_id=user_id,
            subject_id=selected_subject["id"],
            file_name=safe_name,
            file_data=uploaded_file.getvalue(),
            mime_type=uploaded_file.type
        )
        
        if not file_uuid:
            progress.empty()
            st.error("Failed to upload file to Supabase storage. Check file size limits or connection status.")
            st.stop()

        # Update description in metadata
        update_metadata(file_uuid, user_id, {"description": clean_description})

        progress.progress(40, text="Processing document and running OCR if needed...")
        success = process_document_pipeline(file_uuid, user_id)
        
        if not success:
            progress.empty()
            st.error("Document processing failed. You can delete and retry.")
            st.stop()

        # Fetch finalized file info
        file_info = get_file(file_uuid, user_id) or {}
        chunk_count = file_info.get("chunk_count", 0)

        progress.progress(100, text="Upload complete.")
        render_success_state(
            "Upload complete",
            f"{safe_name} has been processed under {selected_subject['name']} and is ready for AI features."
        )
        
        if chunk_count > 0:
            st.success(f"Generated {chunk_count} searchable chunks and stored embeddings in Supabase.")
        else:
            st.warning("File uploaded, but no readable text could be extracted.")
