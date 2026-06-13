import streamlit as st

from modules import ai_engine
from modules.database import get_documents_by_subject, get_subjects, init_db
from modules.ui import (
    apply_theme,
    page_header,
    render_empty_state,
    render_feature_card,
    section_title,
    sidebar_nav,
)


ANSWER_STYLES = ["Simple English", "Roman Urdu", "Exam Style", "Viva Style"]
CHAT_MODES = [
    "General Chat",
    "Chat with Subject",
    "Chat with Specific Notes",
    "Chat with Multiple Notes",
]
MODE_BADGES = {
    "General Chat": "General AI",
    "Chat with Subject": "Subject-based",
    "Chat with Specific Notes": "Single note",
    "Chat with Multiple Notes": "Multiple notes",
}


def get_provider_label():
    """Return the selected provider, even if Streamlit is holding an older module."""
    if hasattr(ai_engine, "get_selected_provider"):
        return ai_engine.get_selected_provider()
    return "Ollama"


def get_subject_index(subjects, subject_id):
    """Find a subject's selectbox index from its id."""
    if not subject_id:
        return 0

    for index, subject in enumerate(subjects):
        if subject["id"] == subject_id:
            return index

    return 0


def source_title(source, index):
    """Build a readable source title from vector metadata."""
    metadata = source.get("metadata", {})
    file_name = metadata.get("file_name", "Uploaded note")
    subject_name = metadata.get("subject_name", "Subject")
    chunk_index = metadata.get("chunk_index", index - 1)
    return f"Source {index}: {file_name} | {subject_name} | Chunk {chunk_index}"


def render_sources(sources):
    """Render sources below an assistant message."""
    if not sources:
        return

    with st.expander(f"Sources used ({len(sources)} relevant note chunks)", expanded=False):
        for index, source in enumerate(sources, start=1):
            st.markdown(f"**{source_title(source, index)}**")
            st.write(source.get("text", "")[:1200])
            st.divider()


def add_chat_pair(question, answer_data, context):
    """Append one user message and one assistant response to session history."""
    st.session_state.study_chat_messages.append(
        {
            "role": "user",
            "content": question,
            "context": context,
        }
    )
    st.session_state.study_chat_messages.append(
        {
            "role": "assistant",
            "content": answer_data["answer"],
            "sources": answer_data["sources"],
            "warning": answer_data["warning"],
            "source_count": answer_data["source_count"],
            "context": context,
        }
    )


def add_assistant_message(answer_data, context):
    """Append only an assistant response, used when regenerating."""
    st.session_state.study_chat_messages.append(
        {
            "role": "assistant",
            "content": answer_data["answer"],
            "sources": answer_data["sources"],
            "warning": answer_data["warning"],
            "source_count": answer_data["source_count"],
            "context": context,
        }
    )


def generate_chat_answer(question, answer_style, chat_mode, context):
    """
    Generate a chatbot response with a compatibility fallback.

    Streamlit Cloud can occasionally keep an older imported module in memory
    after a deploy. This wrapper prevents a hard crash if ai_engine is stale.
    """
    if hasattr(ai_engine, "generate_study_chat_response"):
        return ai_engine.generate_study_chat_response(
            question=question,
            answer_style=answer_style,
            chat_mode=chat_mode,
            subject_id=context["subject_id"],
            document_ids=context["document_ids"],
            context_label=context["label"],
        )

    if chat_mode != "General Chat" and context["subject_id"] is not None:
        return ai_engine.chat_with_notes(
            subject_id=context["subject_id"],
            question=question,
            answer_style=answer_style,
        )

    prompt = f"""
You are Ali Shair's AI Study Assistant.
Answer this student question clearly and in a study-friendly way.
Answer style: {answer_style}

Question:
{question}
"""
    try:
        answer = ai_engine.ask_ai(prompt)
    except Exception as exc:
        answer = str(exc)

    return {
        "answer": answer,
        "sources": [],
        "warning": "",
        "source_count": 0,
    }


def build_context(chat_mode, selected_subject, selected_documents):
    """Create the retrieval settings used by the AI engine."""
    subject_id = selected_subject["id"] if selected_subject else None
    document_ids = [document["id"] for document in selected_documents]

    if chat_mode == "General Chat":
        return {
            "subject_id": None,
            "document_ids": [],
            "label": "General Chat",
            "badge": MODE_BADGES[chat_mode],
        }

    if chat_mode == "Chat with Subject":
        if not selected_subject:
            return {
                "subject_id": None,
                "document_ids": [],
                "label": "No subject selected",
                "badge": MODE_BADGES[chat_mode],
            }

        return {
            "subject_id": subject_id,
            "document_ids": [],
            "label": f"Subject: {selected_subject['name']}",
            "badge": MODE_BADGES[chat_mode],
        }

    if chat_mode == "Chat with Specific Notes":
        if not selected_subject:
            return {
                "subject_id": None,
                "document_ids": [],
                "label": "No subject selected",
                "badge": MODE_BADGES[chat_mode],
            }

        document_name = selected_documents[0]["file_name"] if selected_documents else "Selected note"
        return {
            "subject_id": subject_id,
            "document_ids": document_ids,
            "label": f"Note: {document_name}",
            "badge": MODE_BADGES[chat_mode],
        }

    if not selected_subject:
        return {
            "subject_id": None,
            "document_ids": [],
            "label": "No subject selected",
            "badge": MODE_BADGES[chat_mode],
        }

    return {
        "subject_id": subject_id,
        "document_ids": document_ids,
        "label": f"{len(document_ids)} selected notes",
        "badge": MODE_BADGES[chat_mode],
    }


st.set_page_config(page_title="Chat With Notes - StudyMate AI", layout="wide")
init_db()
apply_theme()
sidebar_nav()

page_header(
    "Chat With Notes",
    "Ask from your notes, selected documents, or general AI knowledge.",
    "Ali's Study Chatbot",
)

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card("Flexible context", "Ask generally, by subject, or from selected notes.", "\U0001f50d", "#14b8b4", "#d8fff6")
with feature2:
    render_feature_card("Real chat flow", "Messages stay in a clean session conversation.", "\U0001f4ac", "#2f7df6", "#e3efff")
with feature3:
    render_feature_card("Exam-ready answers", "Get explanations, examples, key points, and revision tips.", "\U0001f4dd", "#ffb703", "#fff3c4")

if "study_chat_messages" not in st.session_state:
    st.session_state.study_chat_messages = []
if "study_chat_last_question" not in st.session_state:
    st.session_state.study_chat_last_question = ""
if "study_chat_last_request" not in st.session_state:
    st.session_state.study_chat_last_request = None

subjects = get_subjects()
prefill_subject_id = st.session_state.pop("chat_prefill_subject_id", None)
prefill_document_id = st.session_state.pop("chat_prefill_document_id", None)
prefill_question = st.session_state.pop("chat_prefill_question", "")

section_title("Chat Settings", "\u2699\ufe0f")
with st.container(border=True):
    top_col1, top_col2, top_col3 = st.columns([1.2, 1.2, 1])

    with top_col1:
        default_mode_index = 0
        if prefill_document_id:
            default_mode_index = CHAT_MODES.index("Chat with Specific Notes")
        elif prefill_subject_id:
            default_mode_index = CHAT_MODES.index("Chat with Subject")
        chat_mode = st.selectbox("Chat mode", CHAT_MODES, index=default_mode_index)

    with top_col2:
        answer_style = st.selectbox("Answer style", ANSWER_STYLES)

    with top_col3:
        st.markdown(
            f"<span class='status-pill'>{MODE_BADGES[chat_mode]}</span>",
            unsafe_allow_html=True,
        )
        st.caption(f"AI provider: {get_provider_label()}")

    selected_subject = None
    selected_documents = []
    subject_documents = []

    if chat_mode != "General Chat":
        if not subjects:
            st.warning("Create a subject or switch to General Chat.")
        else:
            subject_names = [subject["name"] for subject in subjects]
            subject_index = get_subject_index(subjects, prefill_subject_id)
            selected_subject_name = st.selectbox(
                "Subject",
                subject_names,
                index=subject_index,
            )
            selected_subject = next(
                subject for subject in subjects if subject["name"] == selected_subject_name
            )
            subject_documents = list(get_documents_by_subject(selected_subject["id"]))

            if chat_mode in {"Chat with Specific Notes", "Chat with Multiple Notes"}:
                if not subject_documents:
                    st.warning("No uploaded documents found for this subject yet.")
                else:
                    document_options = {
                        f"{document['file_name']} ({document['chunk_count']} chunks)": document
                        for document in subject_documents
                    }

                    if chat_mode == "Chat with Specific Notes":
                        labels = list(document_options.keys())
                        default_doc_index = 0
                        if prefill_document_id:
                            for index, label in enumerate(labels):
                                if document_options[label]["id"] == prefill_document_id:
                                    default_doc_index = index
                                    break

                        selected_label = st.selectbox(
                            "Selected note",
                            labels,
                            index=default_doc_index,
                        )
                        selected_documents = [document_options[selected_label]]
                    else:
                        selected_labels = st.multiselect(
                            "Selected notes",
                            list(document_options.keys()),
                            default=list(document_options.keys())[:2],
                        )
                        selected_documents = [
                            document_options[label] for label in selected_labels
                        ]

    action_col1, action_col2 = st.columns([1, 1])
    with action_col1:
        if st.button("New Chat", use_container_width=True):
            st.session_state.study_chat_messages = []
            st.session_state.study_chat_last_question = ""
            st.session_state.study_chat_last_request = None
            st.rerun()
    with action_col2:
        if st.button("Regenerate Last Answer", use_container_width=True):
            if st.session_state.study_chat_last_question:
                st.session_state.study_chat_regenerate = True
                st.rerun()
            else:
                st.info("Ask a question first, then regenerate.")

context = build_context(chat_mode, selected_subject, selected_documents)

if prefill_question:
    st.info(f"Suggested question from Study Library: {prefill_question}")
    if st.button("Ask Suggested Question", type="primary", use_container_width=True):
        st.session_state.study_chat_last_question = prefill_question
        st.session_state.study_chat_last_request = {
            "question": prefill_question,
            "answer_style": answer_style,
            "chat_mode": chat_mode,
            "context": context,
        }
        with st.spinner("StudyMate is thinking..."):
            answer_data = generate_chat_answer(
                question=prefill_question,
                answer_style=answer_style,
                chat_mode=chat_mode,
                context=context,
            )
        add_chat_pair(prefill_question, answer_data, context)
        st.rerun()

section_title("Conversation", "\U0001f4ac")
if not st.session_state.study_chat_messages:
    render_empty_state(
        "Ask anything about your notes, subjects, or studies.",
        "Use General Chat or choose a subject/note above, then type at the bottom.",
        "\U0001f4ad",
    )

for message in st.session_state.study_chat_messages:
    avatar = "\U0001f468\u200d\U0001f393" if message["role"] == "user" else "\U0001f916"
    with st.chat_message(message["role"], avatar=avatar):
        message_context = message.get("context", {})
        if message_context:
            st.caption(f"{message_context.get('badge', 'Chat')} | {message_context.get('label', '')}")

        if message.get("warning"):
            st.warning(message["warning"])

        st.markdown(message["content"])

        if message["role"] == "assistant":
            source_count = message.get("source_count", 0)
            if source_count:
                st.caption(f"Using {source_count} relevant note chunks")
            render_sources(message.get("sources", []))

if st.session_state.get("study_chat_regenerate"):
    st.session_state.study_chat_regenerate = False
    if st.session_state.study_chat_messages and st.session_state.study_chat_messages[-1]["role"] == "assistant":
        st.session_state.study_chat_messages.pop()

    last_request = st.session_state.study_chat_last_request
    if last_request:
        with st.spinner("Regenerating answer..."):
            answer_data = generate_chat_answer(
                question=last_request["question"],
                answer_style=last_request["answer_style"],
                chat_mode=last_request["chat_mode"],
                context=last_request["context"],
            )
        add_assistant_message(answer_data, last_request["context"])
    st.rerun()

prompt = st.chat_input("Ask StudyMate anything... Follow-up questions are welcome.")

if prompt:
    if chat_mode != "General Chat" and not selected_subject:
        st.warning("Select a subject first, or switch to General Chat.")
        st.stop()

    if chat_mode == "Chat with Specific Notes" and not selected_documents:
        st.warning("Select one uploaded note first, or switch to General Chat.")
        st.stop()

    if chat_mode == "Chat with Multiple Notes" and not selected_documents:
        st.warning("Select at least one uploaded note first, or switch to General Chat.")
        st.stop()

    st.session_state.study_chat_last_question = prompt
    st.session_state.study_chat_last_request = {
        "question": prompt,
        "answer_style": answer_style,
        "chat_mode": chat_mode,
        "context": context,
    }
    with st.spinner("StudyMate is thinking..."):
        answer_data = generate_chat_answer(
            question=prompt,
            answer_style=answer_style,
            chat_mode=chat_mode,
            context=context,
        )

    add_chat_pair(prompt, answer_data, context)
    st.rerun()
