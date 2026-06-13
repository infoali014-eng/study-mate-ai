import streamlit as st

from modules import ai_engine
from modules.database import get_subjects, init_db
from modules.ui import (
    apply_theme,
    page_header,
    render_empty_state,
    render_feature_card,
    section_title,
    sidebar_nav,
)


ANSWER_STYLES = ["Simple English", "Roman Urdu", "Exam Style", "Viva Style"]


def get_provider_label():
    """Return the selected provider, even if Streamlit is holding an older module."""
    if hasattr(ai_engine, "get_selected_provider"):
        return ai_engine.get_selected_provider()
    return "Ollama"


st.set_page_config(page_title="Chat With Notes - StudyMate AI", layout="wide")
init_db()
apply_theme()
sidebar_nav()

page_header(
    "Chat With Notes",
    "Ask questions from your own uploaded PDFs and choose the answer style.",
    "Notes Assistant",
)

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card("Find context", "Search ChromaDB chunks before asking the selected AI provider.", "\U0001f50d", "#14b8b4", "#d8fff6")
with feature2:
    render_feature_card("Choose tone", "Use Simple English, Roman Urdu, Exam, or Viva style.", "\U0001f3a8", "#ffb703", "#fff3c4")
with feature3:
    render_feature_card("Show sources", "Review exact note chunks used below every answer.", "\U0001f4cc", "#8b5cf6", "#efe7ff")

subjects = get_subjects()
if not subjects:
    render_empty_state(
        "Nothing to chat with yet.",
        "Create a subject and upload PDF notes before asking questions.",
        "\U0001f4ac",
    )
    st.stop()

subject_options = {subject["name"]: subject for subject in subjects}
subject_names = list(subject_options.keys())
prefill_subject_id = st.session_state.pop("chat_prefill_subject_id", None)
default_subject_index = 0
if prefill_subject_id:
    for index, subject_name in enumerate(subject_names):
        if subject_options[subject_name]["id"] == prefill_subject_id:
            default_subject_index = index
            break

section_title("Ask Your Notes", "\U0001f4ac")
with st.container(border=True):
    selected_name = st.selectbox("Choose subject", subject_names, index=default_subject_index)
    selected_subject = subject_options[selected_name]
    prefill_question = st.session_state.pop("chat_prefill_question", "")

    col1, col2 = st.columns([2, 1])
    with col1:
        question = st.text_area(
            "Type your question",
            placeholder="Example: Explain photosynthesis from my notes.",
            value=prefill_question,
            height=120,
        )
    with col2:
        st.info(f"AI provider: {get_provider_label()}. Change it from AI Settings.")
        answer_style = st.radio("Answer style", ANSWER_STYLES, horizontal=False)

    ask_button = st.button("Ask StudyMate", type="primary", use_container_width=True)

if "chat_results" not in st.session_state:
    st.session_state.chat_results = []

if ask_button:
    if not question.strip():
        st.warning("Please type a question first.")
    else:
        with st.spinner("Searching ChromaDB and asking the selected AI provider..."):
            result = ai_engine.chat_with_notes(
                subject_id=selected_subject["id"],
                question=question,
                answer_style=answer_style,
            )

        st.session_state.chat_results.insert(
            0,
            {
                "subject": selected_subject["name"],
                "question": question,
                "answer": result["answer"],
                "sources": result["sources"],
                "answer_style": answer_style,
            },
        )

section_title("Conversation", "\u2728")
if not st.session_state.chat_results:
    render_empty_state(
        "No questions asked yet.",
        "Ask your first question and StudyMate will answer from your uploaded notes.",
        "\U0001f4ad",
    )

for chat in st.session_state.chat_results:
    with st.container(border=True):
        st.caption(f"{chat['subject']} | {chat['answer_style']}")
        st.markdown(f"**Question:** {chat['question']}")
        st.markdown("**Answer:**")
        st.markdown(chat["answer"])

        if chat["sources"]:
            st.markdown("**Source chunks:**")
            for index, source in enumerate(chat["sources"], start=1):
                metadata = source["metadata"]
                file_name = metadata.get("file_name", "Uploaded PDF")
                chunk_index = metadata.get("chunk_index", index - 1)

                with st.expander(f"Source {index}: {file_name} | Chunk {chunk_index}"):
                    st.write(source["text"])
        else:
            st.info("No source chunks were found for this answer.")
