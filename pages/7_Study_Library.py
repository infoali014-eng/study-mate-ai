import html
from pathlib import Path

import streamlit as st

from modules import ai_engine
from modules.auth import require_login
from modules.database import (
    delete_document,
    get_all_documents,
    get_document_by_id,
    get_document_summary,
    get_subjects,
    init_db,
    save_document_summary,
)
from modules.file_preview import (
    file_exists,
    get_file_download_button,
    preview_extracted_text,
    preview_image,
    preview_pdf,
    preview_text_file,
)
from modules.security import is_path_inside
from modules.ui import (
    apply_theme,
    file_type_visual,
    render_ai_loading,
    render_ai_markdown,
    render_empty_state,
    render_subject_card,
    section_title,
    sidebar_nav,
)
from modules.vector_store import delete_document_vectors


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
def ask_selected_ai(prompt):
    """Use the selected AI provider, with a fallback for older loaded modules."""
    if hasattr(ai_engine, "ask_ai"):
        return ai_engine.ask_ai(prompt)
    return ai_engine.ask_ollama(prompt)


def read_extracted_text(document):
    """Return extracted text for a document when it is available."""
    text_path = document["extracted_text_path"]
    user_id = st.session_state.get("user_id")
    allowed_root = DATA_DIR / "extracted_text"
    from modules.database import document_belongs_to_user
    if text_path and document_belongs_to_user(document["id"], user_id) and is_path_inside(allowed_root, text_path) and Path(text_path).exists():
        return Path(text_path).read_text(encoding="utf-8", errors="ignore")
    return ""


def open_document(document):
    """Show a selected document in the preview/details area."""
    st.session_state.library_selected_document = document["id"]
    st.session_state.library_pending_delete = None
    st.rerun()


def chat_with_document(document):
    """Send the selected document context to Chat With Notes."""
    if not get_document_by_id(document["id"], user_id=st.session_state.get("user_id")):
        st.error("Access denied. This document does not belong to your account.")
        return
    st.session_state.chat_prefill_subject_id = document["subject_id"]
    st.session_state.chat_prefill_document_id = document["id"]
    st.session_state.chat_prefill_question = f"Explain {document['file_name']}"
    st.switch_page("pages/3_Chat_With_Notes.py")


def set_summary_document(document):
    """Open details and request a summary for this document."""
    st.session_state.library_selected_document = document["id"]
    st.session_state.library_auto_summary = document["id"]
    st.session_state.library_pending_delete = None
    st.rerun()


def request_delete(document):
    """Start the safe delete flow for one document."""
    st.session_state.library_pending_delete = document["id"]
    st.session_state.library_auto_summary = None
    st.rerun()


def confirm_delete_document(document):
    """Delete one document after ownership has already been checked."""
    vector_cleanup_failed = False
    try:
        delete_document_vectors(document["id"], user_id=st.session_state.get("user_id"))
    except Exception:
        vector_cleanup_failed = True

    deleted = delete_document(document["id"], user_id=st.session_state.get("user_id"))
    if not deleted:
        st.error("Document was not found or was already deleted.")
        return

    st.session_state.library_pending_delete = None
    if st.session_state.library_selected_document == document["id"]:
        st.session_state.library_selected_document = None
    if st.session_state.library_auto_summary == document["id"]:
        st.session_state.library_auto_summary = None
    st.session_state.library_summary.pop(document["id"], None)
    st.session_state.library_success = "Document deleted successfully."
    if vector_cleanup_failed:
        st.session_state.library_success += " Some old search chunks may remain, but this document is removed."
    st.rerun()


def clear_filters():
    """Reset all Study Library filters safely via Streamlit callback."""
    st.session_state.library_search = ""
    st.session_state.library_subject_filter = "All"
    st.session_state.library_file_type_filter = "All types"


def set_subject_filter(subject_name):
    """Update the subject filter safely from a chip button callback."""
    st.session_state.library_subject_filter = subject_name


def material_row(document):
    """Render one clean material list row."""
    file_type = (document["file_type"] or "PDF").upper()
    file_visual = file_type_visual(file_type)
    file_icon = file_visual["icon"]
    description = document["description"] or "No description added."
    extraction_status = document["extraction_status"] or (
        "Text extracted" if int(document["chunk_count"] or 0) else "Text not found"
    )
    extraction_method = document["extraction_method"] or "unknown"

    with st.container(border=True):
        info_col, action_col = st.columns([6, 3])

        with info_col:
            st.markdown(
                f"""
                <div class="material-row-info">
                    <div class="material-file-line">
                        <span class="material-file-icon" style="background:{file_visual['soft']}; color:{file_visual['accent']};">{file_icon}</span>
                        <span class="material-file-name" title="{html.escape(document['file_name'])}">
                            {html.escape(document['file_name'])}
                        </span>
                    </div>
                    <div class="material-row-meta">
                        Subject: {html.escape(document['subject_name'])}
                        <span>|</span> Type: {html.escape(file_type)}
                        <span>|</span> Chunks: {int(document['chunk_count'] or 0)}
                        <span>|</span> Status: {html.escape(extraction_status)}
                        <span>|</span> Uploaded: {html.escape(document['uploaded_at'])}
                    </div>
                    <div class="material-row-description" title="{html.escape(description)}">
                        {html.escape(description)} Method: {html.escape(extraction_method)}.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with action_col:
            action1, action2, action3, action4 = st.columns(4)
            with action1:
                if st.button("Read", key=f"read_{document['id']}", use_container_width=True):
                    open_document(document)
            with action2:
                if st.button("Chat", key=f"chat_{document['id']}", use_container_width=True):
                    chat_with_document(document)
            with action3:
                if st.button("Summary", key=f"summary_{document['id']}", use_container_width=True):
                    set_summary_document(document)
            with action4:
                with st.popover("More"):
                    if st.button("Generate Quiz", key=f"quiz_{document['id']}", use_container_width=True):
                        st.session_state.quiz_prefill_subject_id = document["subject_id"]
                        st.session_state.quiz_prefill_topic = Path(document["file_name"]).stem
                        st.switch_page("pages/4_Quiz_Mode.py")

                    if st.button("Flashcards", key=f"flash_{document['id']}", use_container_width=True):
                        st.session_state.flashcard_prefill_subject_id = document["subject_id"]
                        st.session_state.flashcard_prefill_topic = Path(document["file_name"]).stem
                        st.switch_page("pages/5_Flashcards.py")

                    if st.button("Delete", key=f"delete_{document['id']}", use_container_width=True):
                        request_delete(document)

        if st.session_state.library_pending_delete == document["id"]:
            st.warning(
                "Are you sure you want to delete this document? Only this document, "
                "its extracted text, and related search chunks will be removed."
            )
            confirm_col, cancel_col = st.columns(2)
            with confirm_col:
                if st.button(
                    "Yes, delete document",
                    key=f"confirm_delete_{document['id']}",
                    type="primary",
                    use_container_width=True,
                ):
                    confirm_delete_document(document)
            with cancel_col:
                if st.button(
                    "Cancel",
                    key=f"cancel_delete_{document['id']}",
                    use_container_width=True,
                ):
                    st.session_state.library_pending_delete = None
                    st.rerun()


def render_document_details(document):
    """Render the read/preview panel for one selected document."""
    extracted_text = read_extracted_text(document)
    saved_summary = get_document_summary(document["id"], user_id=st.session_state.get("user_id"))

    section_title("Read / Preview", "\U0001f441\ufe0f")
    with st.container(border=True):
        top_left, top_right = st.columns([4, 1])
        with top_left:
            st.markdown(f"### {document['file_name']}")
            st.caption(
                f"{document['subject_name']} | {(document['file_type'] or 'PDF').upper()} | "
                f"{document['chunk_count']} chunks | "
                f"Status: {document['extraction_status'] or 'Unknown'} | "
                f"Method: {document['extraction_method'] or 'unknown'} | "
                f"Uploaded: {document['uploaded_at']}"
            )
        with top_right:
            if st.button("Close Preview", use_container_width=True):
                st.session_state.library_selected_document = None
                st.session_state.library_auto_summary = None
                st.session_state.library_pending_delete = None
                st.rerun()

        if document["description"]:
            st.write(document["description"])
        if document["warning_message"]:
            st.warning(document["warning_message"])

        original_path = document["file_path"]
        file_type = (document["file_type"] or Path(document["file_name"]).suffix.replace(".", "") or "PDF").upper()
        allowed_root = DATA_DIR / "uploads"
        from modules.database import document_belongs_to_user
        if not document_belongs_to_user(document["id"], st.session_state.get("user_id")):
            st.error("Access denied. This file does not belong to your account or your study groups.")
        elif not is_path_inside(allowed_root, original_path):
            st.error("Access denied. Invalid file path.")
        elif not file_exists(original_path):
            st.error("Original file not found. Please re-upload this document.")
        else:
            if file_type == "PDF":
                st.info("PDF preview is embedded below. If your browser blocks it, use the download button.")
                preview_pdf(original_path)
                with st.expander("Extracted text preview", expanded=False):
                    preview_extracted_text(extracted_text)
            elif file_type in {"PNG", "JPG", "JPEG", "WEBP"}:
                preview_image(original_path)
                st.markdown("**Extracted OCR text**")
                preview_extracted_text(extracted_text)
            elif file_type in {"TXT", "MD", "CSV", "JSON"}:
                preview_text_file(original_path)
            elif file_type in {"DOCX", "PPTX", "XLSX"}:
                st.info("Preview uses extracted text. Download the original file for full formatting.")
                preview_extracted_text(extracted_text)
            else:
                st.info("Preview is not available for this file type, but you can open or download the file.")

            get_file_download_button(original_path)

        detail_actions = st.columns(4)
        with detail_actions[0]:
            if st.button("Chat With This", key=f"detail_chat_{document['id']}", use_container_width=True):
                chat_with_document(document)
        with detail_actions[1]:
            if st.button("Generate Summary", key=f"detail_summary_{document['id']}", use_container_width=True):
                st.session_state.library_auto_summary = document["id"]
                st.rerun()
        with detail_actions[2]:
            if st.button("Generate Quiz", key=f"detail_quiz_{document['id']}", use_container_width=True):
                st.session_state.quiz_prefill_subject_id = document["subject_id"]
                st.session_state.quiz_prefill_topic = Path(document["file_name"]).stem
                st.switch_page("pages/4_Quiz_Mode.py")
        with detail_actions[3]:
            if st.button("Flashcards", key=f"detail_flash_{document['id']}", use_container_width=True):
                st.session_state.flashcard_prefill_subject_id = document["subject_id"]
                st.session_state.flashcard_prefill_topic = Path(document["file_name"]).stem
                st.switch_page("pages/5_Flashcards.py")

        if st.session_state.library_auto_summary == document["id"]:
            if not extracted_text:
                st.warning("No extracted text is available for summary generation.")
            elif saved_summary and document["id"] not in st.session_state.library_summary:
                st.session_state.library_summary[document["id"]] = saved_summary["summary_text"]
            elif document["id"] not in st.session_state.library_summary:
                loading_slot = st.empty()
                with loading_slot:
                    render_ai_loading("Summarizing this document")
                prompt = (
                    f"{ai_engine.build_study_assistant_system_prompt()}\n\n"
                    "Summarize these study notes for the signed-in student. Keep it clear, "
                    "organized, and exam-focused.\n\n"
                    f"NOTES:\n{extracted_text[:6000]}"
                )
                try:
                    summary_text = ask_selected_ai(prompt)
                    st.session_state.library_summary[document["id"]] = summary_text
                    save_document_summary(
                        document_id=document["id"],
                        subject_id=document["subject_id"],
                        summary_text=summary_text,
                        user_id=st.session_state.get("user_id"),
                        provider=ai_engine.get_selected_provider()
                        if hasattr(ai_engine, "get_selected_provider")
                        else "",
                        model=ai_engine.get_session_ai_settings().get("gemini_model", "")
                        if hasattr(ai_engine, "get_session_ai_settings")
                        else "",
                    )
                except Exception:
                    st.error("Could not generate summary with the selected AI provider.")
                finally:
                    loading_slot.empty()

        if saved_summary and document["id"] not in st.session_state.library_summary:
            st.session_state.library_summary[document["id"]] = saved_summary["summary_text"]

        if document["id"] in st.session_state.library_summary:
            st.markdown("**Saved Summary**")
            render_ai_markdown(st.session_state.library_summary[document["id"]])

        with st.expander("Extracted text preview", expanded=False):
            st.write(extracted_text[:3000] if extracted_text else "No extracted text preview found.")


def apply_filters(documents, selected_subject, selected_file_type, search_text):
    """Apply search, subject, and file type filters together."""
    filtered = list(documents)

    if search_text.strip():
        query = search_text.lower().strip()
        filtered = [document for document in filtered if query in document["file_name"].lower()]

    if selected_subject != "All":
        filtered = [document for document in filtered if document["subject_name"] == selected_subject]

    if selected_file_type != "All types":
        filtered = [
            document for document in filtered
            if (document["file_type"] or "PDF").upper() == selected_file_type
        ]

    return filtered


st.set_page_config(page_title="Study Library - StudyMate AI", layout="wide")
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

if "library_selected_document" not in st.session_state:
    st.session_state.library_selected_document = None
if "library_pending_delete" not in st.session_state:
    st.session_state.library_pending_delete = None
if "library_summary" not in st.session_state:
    st.session_state.library_summary = {}
if "library_success" not in st.session_state:
    st.session_state.library_success = ""
if "library_auto_summary" not in st.session_state:
    st.session_state.library_auto_summary = None
if "library_subject_filter" not in st.session_state:
    st.session_state.library_subject_filter = "All"
if "library_file_type_filter" not in st.session_state:
    st.session_state.library_file_type_filter = "All types"
if "library_search" not in st.session_state:
    st.session_state.library_search = ""

st.markdown(
    """
    <div class="library-header">
        <h1>Study Library</h1>
        <p>Browse, read, and manage your uploaded notes subject-wise.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.library_success:
    st.success(st.session_state.library_success)
    st.session_state.library_success = ""

subjects = get_subjects(user_id=user_id)
documents = get_all_documents(user_id=user_id)

subject_names = ["All"] + list(dict.fromkeys(subject["name"] for subject in subjects))
file_types = ["All types"] + sorted({(document["file_type"] or "PDF").upper() for document in documents})

if subjects:
    section_title("Subject Overview", "\U0001f4da")
    overview_cols = st.columns(min(3, len(subjects)))
    for index, subject in enumerate(subjects[:6]):
        document_count = sum(
            1 for document in documents if int(document["subject_id"]) == int(subject["id"])
        )
        with overview_cols[index % len(overview_cols)]:
            render_subject_card(subject, document_count=document_count)

if st.session_state.library_subject_filter not in subject_names:
    st.session_state.library_subject_filter = "All"
if st.session_state.library_file_type_filter not in file_types:
    st.session_state.library_file_type_filter = "All types"

with st.container(border=True):
    st.markdown("<div class='filter-card-title'>Find material</div>", unsafe_allow_html=True)
    search_col, subject_col, type_col, clear_col = st.columns([2.6, 1.4, 1.2, 0.9])
    with search_col:
        search_text = st.text_input(
            "Search by document name",
            placeholder="Search by document name",
            key="library_search",
        )
    with subject_col:
        selected_subject = st.selectbox(
            "Subject",
            subject_names,
            key="library_subject_filter",
        )
    with type_col:
        selected_file_type = st.selectbox(
            "File type",
            file_types,
            key="library_file_type_filter",
        )
    with clear_col:
        st.write("")
        st.button("Clear", use_container_width=True, on_click=clear_filters)

section_title("Subject Filters", "\U0001f4da")
chip_count = max(1, min(6, len(subject_names)))
chip_cols = st.columns(chip_count)
for index, subject_name in enumerate(subject_names):
    with chip_cols[index % chip_count]:
        is_active = st.session_state.library_subject_filter == subject_name
        label = subject_name if subject_name == "All" else subject_name[:18]
        button_label = f"{'* ' if is_active else ''}{label}"
        st.button(
            button_label,
            key=f"subject_chip_{subject_name}",
            use_container_width=True,
            on_click=set_subject_filter,
            args=(subject_name,),
        )

filtered_documents = apply_filters(
    documents=documents,
    selected_subject=st.session_state.library_subject_filter,
    selected_file_type=st.session_state.library_file_type_filter,
    search_text=st.session_state.library_search,
)

section_title("Materials", "\U0001f5c3\ufe0f")
st.caption(f"Showing {len(filtered_documents)} of {len(documents)} uploaded materials")

if not documents:
    render_empty_state(
        "No study material uploaded yet.",
        "Upload notes to build your personal study library.",
        "\U0001f5c3\ufe0f",
    )
    if st.button("Upload Notes", type="primary"):
        st.switch_page("pages/2_Upload_Notes.py")
else:
    if not filtered_documents:
        render_empty_state(
            "No matching material found.",
            "Try clearing filters or searching with another file name.",
            "\U0001f50d",
        )
    else:
        for document in filtered_documents:
            material_row(document)

selected_document_id = st.session_state.library_selected_document
if selected_document_id:
    selected_document = get_document_by_id(selected_document_id, user_id=user_id)
    if selected_document:
        render_document_details(selected_document)
    else:
        st.error("Access denied. This document does not belong to your account.")
        st.session_state.library_selected_document = None

if st.session_state.library_pending_delete and not any(
    document["id"] == st.session_state.library_pending_delete
    for document in filtered_documents
):
    pending_doc = get_document_by_id(st.session_state.library_pending_delete, user_id=user_id)
    if pending_doc:
        st.warning(
            f"Are you sure you want to delete `{pending_doc['file_name']}`? "
            "Only this document record, local files, and related vector chunks will be removed."
        )
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("Yes, delete document", type="primary", use_container_width=True):
                try:
                    confirm_delete_document(pending_doc)
                except Exception:
                    st.error("Could not delete this document. Please try again.")
        with cancel_col:
            if st.button("Cancel delete", use_container_width=True):
                st.session_state.library_pending_delete = None
                st.rerun()
