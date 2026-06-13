import html
from pathlib import Path

import streamlit as st

from modules import ai_engine
from modules.database import (
    delete_document,
    get_all_documents,
    get_document_by_id,
    get_documents_by_subject,
    get_subject_document_counts,
    get_subjects,
    init_db,
)
from modules.file_preview import (
    file_exists,
    get_file_download_button,
    preview_pdf,
    preview_text_file,
)
from modules.ui import (
    apply_theme,
    page_header,
    render_empty_state,
    render_feature_card,
    render_stat_card,
    section_title,
    sidebar_nav,
)
from modules.vector_store import VectorStoreError, delete_document_vectors


def ask_selected_ai(prompt):
    """Use the selected AI provider, with a fallback for older loaded modules."""
    if hasattr(ai_engine, "ask_ai"):
        return ai_engine.ask_ai(prompt)
    return ai_engine.ask_ollama(prompt)


st.set_page_config(page_title="Study Library - StudyMate AI", layout="wide")
init_db()
apply_theme()
sidebar_nav()

page_header(
    "Study Library",
    "Browse every uploaded note, organized subject-wise for Ali Shair.",
    "Subject Materials",
)

if "library_selected_subject" not in st.session_state:
    st.session_state.library_selected_subject = None
if "library_selected_document" not in st.session_state:
    st.session_state.library_selected_document = None
if "library_pending_delete" not in st.session_state:
    st.session_state.library_pending_delete = None
if "library_summary" not in st.session_state:
    st.session_state.library_summary = {}
if "library_success" not in st.session_state:
    st.session_state.library_success = ""

if st.session_state.library_success:
    st.success(st.session_state.library_success)
    st.session_state.library_success = ""

subjects = get_subjects()
documents = get_all_documents()
subject_counts = get_subject_document_counts()

top1, top2, top3 = st.columns(3)
with top1:
    render_stat_card("Subjects", len(subjects), "Organized study areas", "\U0001f4da", "#14b8b4", "#d8fff6")
with top2:
    render_stat_card("Documents", len(documents), "Uploaded materials", "\U0001f5c3\ufe0f", "#2f7df6", "#e3efff")
with top3:
    render_stat_card("Library", "Local", "SQLite + ChromaDB", "\U0001f4be", "#8b5cf6", "#efe7ff")

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card("Subject-wise", "Open a subject and see only its notes.", "\U0001f4d8", "#14b8b4", "#d8fff6")
with feature2:
    render_feature_card("Quick actions", "Jump into chat, quiz, or flashcards.", "\u26a1", "#ffb703", "#fff3c4")
with feature3:
    render_feature_card("Safe cleanup", "Delete one document without touching other subjects.", "\U0001f5d1\ufe0f", "#ff637d", "#ffe3e9")

subject_names = ["All subjects"] + [subject["name"] for subject in subjects]
subject_by_name = {subject["name"]: subject for subject in subjects}

if not documents:
    section_title("Subjects", "\U0001f4da")
    if not subject_counts:
        render_empty_state(
            "No subjects yet.",
            "Create a subject first, then upload notes to build your library.",
            "\U0001f4da",
        )
    else:
        subject_cols = st.columns(3)
        for index, subject in enumerate(subject_counts):
            with subject_cols[index % 3]:
                with st.container(border=True):
                    st.markdown(f"### {subject['name']}")
                    st.write(subject["description"] or "No description added yet.")
                    st.markdown(
                        f"<span class='library-chip'>{subject['document_count']} documents</span>",
                        unsafe_allow_html=True,
                    )

    render_empty_state(
        "No study material uploaded yet.",
        "Upload notes to build your personal study library.",
        "\U0001f5c3\ufe0f",
    )
    st.stop()

section_title("Search and Filter", "\U0001f50d")
with st.container(border=True):
    search_text = st.text_input(
        "Search by document name",
        placeholder="Example: chapter 1, lab manual, SQL notes",
    )
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        selected_filter_subject = st.selectbox("Filter by subject", subject_names)
    with filter_col2:
        file_types = sorted({(doc["file_type"] or "PDF").upper() for doc in documents})
        selected_file_type = st.selectbox("Filter by file type", ["All types"] + file_types)

filtered_documents = documents
if search_text.strip():
    filtered_documents = [
        doc for doc in filtered_documents
        if search_text.lower().strip() in doc["file_name"].lower()
    ]

if selected_filter_subject != "All subjects":
    subject_id = subject_by_name[selected_filter_subject]["id"]
    filtered_documents = [
        doc for doc in filtered_documents
        if doc["subject_id"] == subject_id
    ]

if selected_file_type != "All types":
    filtered_documents = [
        doc for doc in filtered_documents
        if (doc["file_type"] or "PDF").upper() == selected_file_type
    ]

section_title("Subjects", "\U0001f4da")
subject_cols = st.columns(3)
for index, subject in enumerate(subject_counts):
    with subject_cols[index % 3]:
        with st.container(border=True):
            st.markdown(f"### {subject['name']}")
            st.write(subject["description"] or "No description added yet.")
            st.markdown(
                f"<span class='library-chip'>{subject['document_count']} documents</span>",
                unsafe_allow_html=True,
            )
            if st.button(
                "Open Subject",
                key=f"open_subject_{subject['id']}",
                use_container_width=True,
            ):
                st.session_state.library_selected_subject = subject["id"]
                st.session_state.library_selected_document = None
                st.rerun()

selected_subject_id = st.session_state.library_selected_subject
if selected_subject_id:
    selected_subject_docs = get_documents_by_subject(selected_subject_id)
    selected_subject_name = next(
        (subject["name"] for subject in subjects if subject["id"] == selected_subject_id),
        "Selected Subject",
    )
    section_title(f"{selected_subject_name} Materials", "\U0001f5c3\ufe0f")
else:
    selected_subject_docs = filtered_documents
    section_title("All Materials", "\U0001f5c3\ufe0f")

material_docs = selected_subject_docs if selected_subject_id else filtered_documents

if not material_docs:
    render_empty_state(
        "No matching material found.",
        "Try a different search, subject, or file type filter.",
        "\U0001f50d",
    )
else:
    material_cols = st.columns(3)
    for index, doc in enumerate(material_docs):
        with material_cols[index % 3]:
            st.markdown(
                f"""
                <div class="material-card">
                    <div class="material-title" title="{html.escape(doc['file_name'])}">
                        {html.escape(doc['file_name'])}
                    </div>
                    <p class="material-description">{html.escape(doc['description'] or 'No description added.')}</p>
                    <div class="library-meta">
                        <span class="library-chip">Subject: {html.escape(doc['subject_name'])}</span>
                        <span class="library-chip">Type: {html.escape((doc['file_type'] or 'PDF').upper())}</span>
                        <span class="library-chip">Chunks: {doc['chunk_count']}</span>
                    </div>
                    <p class="material-date">Uploaded: {html.escape(doc['uploaded_at'])}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            action_cols = st.columns(3)
            with action_cols[0]:
                if st.button("Read Notes", key=f"details_{doc['id']}", use_container_width=True):
                    st.session_state.library_selected_document = doc["id"]
                    st.rerun()
            with action_cols[1]:
                if st.button("Chat", key=f"chat_{doc['id']}", use_container_width=True):
                    st.session_state.chat_prefill_subject_id = doc["subject_id"]
                    st.session_state.chat_prefill_document_id = doc["id"]
                    st.session_state.chat_prefill_question = f"Explain {doc['file_name']}"
                    st.switch_page("pages/3_Chat_With_Notes.py")
            with action_cols[2]:
                if st.button("Summary", key=f"summary_{doc['id']}", use_container_width=True):
                    st.session_state.library_selected_document = doc["id"]
                    st.session_state.library_summary.pop(doc["id"], None)
                    st.rerun()

            action_cols_2 = st.columns(3)
            with action_cols_2[0]:
                if st.button("Quiz", key=f"quiz_{doc['id']}", use_container_width=True):
                    st.session_state.quiz_prefill_subject_id = doc["subject_id"]
                    st.session_state.quiz_prefill_topic = Path(doc["file_name"]).stem
                    st.switch_page("pages/4_Quiz_Mode.py")
            with action_cols_2[1]:
                if st.button("Flashcards", key=f"flash_doc_{doc['id']}", use_container_width=True):
                    st.session_state.flashcard_prefill_subject_id = doc["subject_id"]
                    st.session_state.flashcard_prefill_topic = Path(doc["file_name"]).stem
                    st.switch_page("pages/5_Flashcards.py")
            with action_cols_2[2]:
                if st.button("Delete", key=f"delete_doc_{doc['id']}", use_container_width=True):
                    st.session_state.library_pending_delete = doc["id"]
                    st.session_state.library_selected_document = doc["id"]
                    st.rerun()

selected_document_id = st.session_state.library_selected_document
if selected_document_id:
    document = get_document_by_id(selected_document_id)
    if document:
        section_title("Document Details", "\U0001f4c4")
        with st.container(border=True):
            if st.button("Back to Study Library", use_container_width=True):
                st.session_state.library_selected_document = None
                st.session_state.library_pending_delete = None
                st.rerun()

            st.markdown(f"### {document['file_name']}")
            st.write(f"**Subject:** {document['subject_name']}")
            st.write(f"**Upload date:** {document['uploaded_at']}")
            st.write(f"**File type:** {(document['file_type'] or 'PDF').upper()}")
            st.write(f"**Text chunks:** {document['chunk_count']}")
            st.write(f"**Description:** {document['description'] or 'No description added.'}")

            extracted_text = ""
            text_path = document["extracted_text_path"]
            if text_path and Path(text_path).exists():
                extracted_text = Path(text_path).read_text(encoding="utf-8", errors="ignore")

            section_title("Open / Preview Document", "\U0001f441\ufe0f")
            original_path = document["file_path"]
            file_type = (document["file_type"] or Path(document["file_name"]).suffix.replace(".", "") or "PDF").upper()

            if not file_exists(original_path):
                st.error("Original file not found. Please re-upload this document.")
            else:
                if file_type == "PDF":
                    st.info("PDF preview is embedded below. If your browser blocks it, use the download button.")
                    preview_pdf(original_path)
                elif file_type == "TXT":
                    preview_text_file(original_path)
                elif file_type in ["DOCX", "DOC", "PPTX", "PPT"]:
                    st.info(
                        "Preview is not available for this file type, but you can open or download the file."
                    )
                    if extracted_text:
                        with st.expander("Extracted text preview", expanded=True):
                            st.write(extracted_text[:3000])
                else:
                    st.info(
                        "Preview is not available for this file type, but you can open or download the file."
                    )

                get_file_download_button(original_path)

            with st.expander("Extracted text preview", expanded=False):
                st.write(extracted_text[:3000] if extracted_text else "No extracted text preview found.")

            detail_actions = st.columns(4)
            with detail_actions[0]:
                if st.button("Ask questions", key=f"detail_chat_{document['id']}", use_container_width=True):
                    st.session_state.chat_prefill_subject_id = document["subject_id"]
                    st.session_state.chat_prefill_document_id = document["id"]
                    st.session_state.chat_prefill_question = f"Explain {document['file_name']}"
                    st.switch_page("pages/3_Chat_With_Notes.py")
            with detail_actions[1]:
                if st.button("Generate summary", key=f"detail_summary_{document['id']}", use_container_width=True):
                    if not extracted_text:
                        st.warning("No extracted text is available for summary generation.")
                    else:
                        with st.spinner("Generating summary with the selected AI provider..."):
                            prompt = (
                                "Summarize these study notes for a student. Keep it clear, "
                                "organized, and exam-focused.\n\n"
                                f"NOTES:\n{extracted_text[:6000]}"
                            )
                            try:
                                st.session_state.library_summary[document["id"]] = ask_selected_ai(prompt)
                            except Exception as exc:
                                st.error(f"Could not generate summary. Technical detail: {exc}")
            with detail_actions[2]:
                if st.button("Generate MCQs", key=f"detail_quiz_{document['id']}", use_container_width=True):
                    st.session_state.quiz_prefill_subject_id = document["subject_id"]
                    st.session_state.quiz_prefill_topic = Path(document["file_name"]).stem
                    st.switch_page("pages/4_Quiz_Mode.py")
            with detail_actions[3]:
                if st.button("Generate flashcards", key=f"detail_flash_{document['id']}", use_container_width=True):
                    st.session_state.flashcard_prefill_subject_id = document["subject_id"]
                    st.session_state.flashcard_prefill_topic = Path(document["file_name"]).stem
                    st.switch_page("pages/5_Flashcards.py")
            if st.button("Delete document", key=f"detail_delete_{document['id']}", use_container_width=True):
                st.session_state.library_pending_delete = document["id"]
                st.rerun()

            if document["id"] in st.session_state.library_summary:
                st.markdown("**Generated Summary**")
                st.write(st.session_state.library_summary[document["id"]])

if st.session_state.library_pending_delete:
    pending_doc = get_document_by_id(st.session_state.library_pending_delete)
    if pending_doc:
        st.warning(
            f"Are you sure you want to delete `{pending_doc['file_name']}`? "
            "Only this document record, local files, and related vector chunks will be removed."
        )
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("Yes, delete document", type="primary", use_container_width=True):
                try:
                    try:
                        delete_document_vectors(pending_doc["id"])
                    except VectorStoreError as exc:
                        st.warning(str(exc))

                    deleted = delete_document(pending_doc["id"])
                    if deleted:
                        st.session_state.library_pending_delete = None
                        st.session_state.library_selected_document = None
                        st.session_state.library_success = "Document deleted successfully."
                        st.rerun()
                    else:
                        st.error("Document was not found or was already deleted.")
                except Exception as exc:
                    st.error(f"Could not delete this document. Technical detail: {exc}")
        with cancel_col:
            if st.button("Cancel delete", use_container_width=True):
                st.session_state.library_pending_delete = None
                st.rerun()
