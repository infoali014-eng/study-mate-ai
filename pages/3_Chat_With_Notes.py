import os

import streamlit as st

from modules.ai_engine import OLLAMA_MODEL, chat_with_notes
from modules.database import get_subjects, init_db


ANSWER_STYLES = ["Simple English", "Roman Urdu", "Exam Style", "Viva Style"]


st.set_page_config(page_title="Chat With Notes - StudyMate AI", layout="wide")
init_db()

st.sidebar.title("StudyMate AI")
st.sidebar.page_link("pages/1_Dashboard.py", label="Dashboard")
st.sidebar.page_link("pages/2_Upload_Notes.py", label="Upload Notes")
st.sidebar.page_link("pages/3_Chat_With_Notes.py", label="Chat With Notes")
st.sidebar.page_link("pages/4_Quiz_Mode.py", label="Quiz Mode")
st.sidebar.page_link("pages/5_Flashcards.py", label="Flashcards")
st.sidebar.page_link("pages/6_Revision_Planner.py", label="Revision Planner")

st.title("Chat With Notes")
st.caption("Ask questions using your uploaded PDFs as the knowledge source.")

subjects = get_subjects()
if not subjects:
    st.warning("Create a subject and upload notes before chatting.")
    st.stop()

subject_options = {subject["name"]: subject for subject in subjects}
selected_name = st.selectbox("Choose subject", list(subject_options.keys()))
selected_subject = subject_options[selected_name]

col1, col2 = st.columns([2, 1])
with col1:
    question = st.text_area(
        "Type your question",
        placeholder="Example: Explain photosynthesis from my notes.",
        height=120,
    )
with col2:
    model = st.text_input("Ollama model", value=os.getenv("OLLAMA_MODEL", OLLAMA_MODEL))
    answer_style = st.radio(
        "Answer style",
        ANSWER_STYLES,
        horizontal=False,
    )

ask_button = st.button("Ask StudyMate", type="primary", use_container_width=True)

if "chat_results" not in st.session_state:
    st.session_state.chat_results = []

if ask_button:
    if not question.strip():
        st.warning("Please type a question first.")
    else:
        with st.spinner("Searching ChromaDB and asking Ollama..."):
            result = chat_with_notes(
                subject_id=selected_subject["id"],
                question=question,
                model=model,
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
