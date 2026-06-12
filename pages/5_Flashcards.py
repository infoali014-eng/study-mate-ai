import os

import streamlit as st

from modules.ai_engine import OLLAMA_MODEL
from modules.database import (
    get_flashcards,
    get_subjects,
    init_db,
    save_flashcard,
    update_flashcard_status,
    update_weak_topic,
)
from modules.flashcard_generator import generate_flashcards


st.set_page_config(page_title="Flashcards - StudyMate AI", layout="wide")
init_db()

st.sidebar.title("StudyMate AI")
st.sidebar.page_link("pages/1_Dashboard.py", label="Dashboard")
st.sidebar.page_link("pages/2_Upload_Notes.py", label="Upload Notes")
st.sidebar.page_link("pages/3_Chat_With_Notes.py", label="Chat With Notes")
st.sidebar.page_link("pages/4_Quiz_Mode.py", label="Quiz Mode")
st.sidebar.page_link("pages/5_Flashcards.py", label="Flashcards")
st.sidebar.page_link("pages/6_Revision_Planner.py", label="Revision Planner")

st.title("Flashcards")
st.caption("Generate flashcards from uploaded notes and review them one by one.")

subjects = get_subjects()
if not subjects:
    st.warning("Create a subject and upload notes first.")
    st.stop()

subject_options = {subject["name"]: subject for subject in subjects}

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        selected_name = st.selectbox("Choose subject", list(subject_options.keys()))
        topic = st.text_input("Flashcard topic", placeholder="Example: photosynthesis")
    with col2:
        card_count = st.number_input(
            "Number of flashcards",
            min_value=1,
            max_value=20,
            value=8,
            step=1,
        )
        model = st.text_input("Ollama model", value=os.getenv("OLLAMA_MODEL", OLLAMA_MODEL))

    generate_button = st.button(
        "Generate and Save Flashcards",
        type="primary",
        use_container_width=True,
    )

selected_subject = subject_options[selected_name]

if "flashcard_review_index" not in st.session_state:
    st.session_state.flashcard_review_index = 0
if "show_flashcard_answer" not in st.session_state:
    st.session_state.show_flashcard_answer = False

if generate_button:
    if not topic.strip():
        st.warning("Please enter a topic.")
    else:
        with st.spinner("Searching uploaded notes and generating flashcards with Ollama..."):
            generated = generate_flashcards(
                subject_id=selected_subject["id"],
                topic=topic,
                card_count=int(card_count),
                model=model,
            )

        if generated["error"]:
            st.error(generated["error"])
        elif not generated["flashcards"]:
            st.error("Ollama did not return usable flashcards. Try a clearer topic.")
        else:
            saved_count = 0
            for card in generated["flashcards"]:
                save_flashcard(
                    subject_id=selected_subject["id"],
                    question=card["question"],
                    answer=card["answer"],
                    topic=topic,
                )
                saved_count += 1

            st.session_state.flashcard_review_index = 0
            st.session_state.show_flashcard_answer = False
            st.success(f"Generated and saved {saved_count} flashcards.")

            if generated["sources"]:
                with st.expander("Source chunks used to generate these flashcards"):
                    for index, source in enumerate(generated["sources"], start=1):
                        metadata = source["metadata"]
                        file_name = metadata.get("file_name", "Uploaded PDF")
                        st.markdown(f"**Source {index}: {file_name}**")
                        st.write(source["text"])

saved_cards = get_flashcards(subject_id=selected_subject["id"])

st.subheader("Review Flashcards")

if not saved_cards:
    st.info("No saved flashcards for this subject yet. Generate some first.")
    st.stop()

total_cards = len(saved_cards)
st.session_state.flashcard_review_index %= total_cards
current_index = st.session_state.flashcard_review_index
current_card = saved_cards[current_index]

learned_count = sum(1 for card in saved_cards if card["status"] == "Learned")
weak_count = sum(1 for card in saved_cards if card["status"] == "Weak")
new_count = total_cards - learned_count - weak_count

metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Total", total_cards)
metric2.metric("New", new_count)
metric3.metric("Learned", learned_count)
metric4.metric("Weak", weak_count)

st.progress((current_index + 1) / total_cards)

with st.container(border=True):
    st.caption(
        f"Card {current_index + 1} of {total_cards} | "
        f"Topic: {current_card['topic'] or 'General'} | "
        f"Status: {current_card['status']}"
    )
    st.markdown(f"### {current_card['question']}")

    if st.session_state.show_flashcard_answer:
        st.divider()
        st.markdown("**Answer**")
        st.write(current_card["answer"])
    else:
        st.info("Think of the answer first, then reveal it.")

left, middle, right = st.columns(3)

with left:
    if st.button("Previous", use_container_width=True):
        st.session_state.flashcard_review_index = (current_index - 1) % total_cards
        st.session_state.show_flashcard_answer = False
        st.rerun()

with middle:
    if st.button("Show Answer", use_container_width=True):
        st.session_state.show_flashcard_answer = True
        st.rerun()

with right:
    if st.button("Next", use_container_width=True):
        st.session_state.flashcard_review_index = (current_index + 1) % total_cards
        st.session_state.show_flashcard_answer = False
        st.rerun()

mark_left, mark_right = st.columns(2)

with mark_left:
    if st.button("Mark as Learned", type="primary", use_container_width=True):
        update_flashcard_status(current_card["id"], "Learned")
        st.session_state.flashcard_review_index = (current_index + 1) % total_cards
        st.session_state.show_flashcard_answer = False
        st.rerun()

with mark_right:
    if st.button("Mark as Weak", use_container_width=True):
        update_flashcard_status(current_card["id"], "Weak")
        update_weak_topic(
            subject_id=selected_subject["id"],
            topic=current_card["topic"] or current_card["question"][:60],
            weakness_score=1,
            notes=f"Weak flashcard: {current_card['question']}",
        )
        st.session_state.flashcard_review_index = (current_index + 1) % total_cards
        st.session_state.show_flashcard_answer = False
        st.rerun()
