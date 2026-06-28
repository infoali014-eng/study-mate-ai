import streamlit as st

from modules import ai_engine
from modules.auth import require_login
from modules.database import init_db

# Redefine flashcard functions to delegate directly to Supabase repository (Phase 4D)
def get_flashcards(subject_id, user_id):
    from modules.flashcard_repository import FlashcardRepository
    return FlashcardRepository.get_flashcards(user_id, subject_id)

def save_flashcard(subject_id, question, answer, topic, user_id):
    from modules.flashcard_repository import FlashcardRepository
    return FlashcardRepository.create_flashcard(user_id, subject_id, question, answer, topic=topic)

def update_flashcard_status(card_id, status, user_id):
    from modules.flashcard_repository import FlashcardRepository
    # Map Learned -> Quality 4 (Good), Weak -> Quality 1 (Incorrect)
    rating = 4 if status == "Learned" else 1
    return FlashcardRepository.review_flashcard(user_id, card_id, rating)

def delete_flashcards_by_subject(subject_id, user_id):
    from modules.flashcard_repository import FlashcardRepository
    return FlashcardRepository.delete_flashcards_by_subject(user_id, subject_id)

def update_weak_topic(subject_id, topic, weakness_score=1, notes="", user_id=None):
    from modules.supabase_client import get_supabase_admin_client
    from datetime import datetime
    client = get_supabase_admin_client()
    if not client:
        return
    try:
        clean_topic = topic.strip()
        existing = client.table("weak_topics").select("*").eq("owner_id", user_id).eq("subject_id", subject_id).eq("topic", clean_topic).execute()
        if existing.data:
            row = existing.data[0]
            attempts = int(row.get("attempts", 0)) + 1
            incorrect = int(row.get("incorrect", 0)) + (1 if weakness_score > 0 else 0)
            correct = int(row.get("correct", 0)) + (0 if weakness_score > 0 else 1)
            new_score = int(row.get("weakness_score", 0)) + weakness_score
            
            old_score = int(row.get("weakness_score", 0))
            trend = "Stable"
            if new_score < old_score:
                trend = "Improving"
            elif new_score > old_score:
                trend = "Declining"
                
            client.table("weak_topics").update({
                "weakness_score": max(0, new_score),
                "attempts": attempts,
                "correct": correct,
                "incorrect": incorrect,
                "trend": trend,
                "notes": notes.strip(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", row["id"]).execute()
        else:
            client.table("weak_topics").insert({
                "owner_id": user_id,
                "subject_id": subject_id,
                "topic": clean_topic,
                "weakness_score": max(0, weakness_score),
                "attempts": 1,
                "correct": 0 if weakness_score > 0 else 1,
                "incorrect": 1 if weakness_score > 0 else 0,
                "trend": "Stable",
                "source": "Flashcards",
                "notes": notes.strip(),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
    except Exception as e:
        print(f"Error updating weak topic: {e}")
from modules.library_repository import (
    get_subjects,
)
from modules.flashcard_generator import generate_flashcards
from modules.security import clean_text
from modules.ui import (
    apply_theme,
    page_header,
    render_ai_loading,
    render_empty_state,
    render_feature_card,
    section_title,
    sidebar_nav,
)


def get_provider_label():
    """Return the selected provider, even if Streamlit is holding an older module."""
    if hasattr(ai_engine, "get_selected_provider"):
        return ai_engine.get_selected_provider()
    return "Ollama"


st.set_page_config(page_title="Flashcards - StudyMate AI", layout="wide")
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

page_header(
    "Flashcards",
    "Generate flashcards from uploaded notes and review them one by one.",
    "Memory Studio",
)

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card("Auto cards", "Generate question and answer cards from uploaded notes.", "\U0001f0cf", "#ffb703", "#fff3c4")
with feature2:
    render_feature_card("Review mode", "Move through cards one by one with a clean study view.", "\U0001f9e0", "#8b5cf6", "#efe7ff")
with feature3:
    render_feature_card("Track weak cards", "Mark cards as Learned or Weak for revision planning.", "\U0001f4cc", "#14b8b4", "#d8fff6")

subjects = get_subjects(user_id=user_id)
if not subjects:
    render_empty_state(
        "No flashcard source yet.",
        "Create a subject and upload notes before generating flashcards.",
        "\U0001f0cf",
    )
    st.stop()

subject_options = {subject["name"]: subject for subject in subjects}
subject_names = list(subject_options.keys())
prefill_subject_id = st.session_state.pop("flashcard_prefill_subject_id", None)
default_subject_index = 0
if prefill_subject_id:
    for index, subject_name in enumerate(subject_names):
        if subject_options[subject_name]["id"] == prefill_subject_id:
            default_subject_index = index
            break
prefill_topic = st.session_state.pop("flashcard_prefill_topic", "")

section_title("Flashcard Generator", "zap")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        selected_name = st.selectbox("Choose subject", subject_names, index=default_subject_index)
        topic = st.text_input("Flashcard topic", value=prefill_topic, placeholder="Example: photosynthesis")
    with col2:
        card_count = st.number_input(
            "Number of flashcards",
            min_value=1,
            max_value=20,
            value=8,
            step=1,
        )
        st.info(f"AI provider: {get_provider_label()}. Change it from AI Settings.")

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
if "flashcard_pending_delete_set" not in st.session_state:
    st.session_state.flashcard_pending_delete_set = None

if generate_button:
    clean_topic = clean_text(topic, max_length=120)
    if not clean_topic:
        st.warning("Please enter a topic.")
    else:
        loading_slot = st.empty()
        with loading_slot:
            render_ai_loading("Turning your notes into flashcards")
        try:
            generated = generate_flashcards(
                subject_id=selected_subject["id"],
                topic=clean_topic,
                card_count=int(card_count),
                user_id=user_id,
            )
        finally:
            loading_slot.empty()

        if generated["error"]:
            st.error(generated["error"])
        elif not generated["flashcards"]:
            st.error("The selected AI provider did not return usable flashcards. Try a clearer topic.")
        else:
            saved_count = 0
            for card in generated["flashcards"]:
                save_flashcard(
                    subject_id=selected_subject["id"],
                    question=card["question"],
                    answer=card["answer"],
                    topic=clean_topic,
                    user_id=user_id,
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

saved_cards = get_flashcards(subject_id=selected_subject["id"], user_id=user_id)

section_title("Review Flashcards", "layers")

if not saved_cards:
    render_empty_state(
        "No saved flashcards yet.",
        "Generate flashcards for this subject, then review them here.",
        "\U0001f0cf",
    )
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

if st.button("Delete This Flashcard Set", use_container_width=True):
    st.session_state.flashcard_pending_delete_set = selected_subject["id"]

if st.session_state.flashcard_pending_delete_set == selected_subject["id"]:
    st.warning(
        "Are you sure you want to delete this flashcard set? "
        "All flashcards for this subject will be removed from your account."
    )
    confirm_delete, cancel_delete = st.columns(2)
    with confirm_delete:
        if st.button("Yes, delete flashcards", type="primary", use_container_width=True):
            if delete_flashcards_by_subject(selected_subject["id"], user_id=user_id):
                st.session_state.flashcard_pending_delete_set = None
                st.session_state.flashcard_review_index = 0
                st.session_state.show_flashcard_answer = False
                st.success("Flashcard set deleted successfully.")
                st.rerun()
            else:
                st.error("Could not delete this flashcard set.")
    with cancel_delete:
        if st.button("Cancel", use_container_width=True):
            st.session_state.flashcard_pending_delete_set = None
            st.rerun()

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
        update_flashcard_status(current_card["id"], "Learned", user_id=user_id)
        st.session_state.flashcard_review_index = (current_index + 1) % total_cards
        st.session_state.show_flashcard_answer = False
        st.rerun()

with mark_right:
    if st.button("Mark as Weak", use_container_width=True):
        update_flashcard_status(current_card["id"], "Weak", user_id=user_id)
        update_weak_topic(
            subject_id=selected_subject["id"],
            topic=current_card["topic"] or current_card["question"][:60],
            weakness_score=1,
            notes=f"Weak flashcard: {current_card['question']}",
            user_id=user_id,
        )
        st.session_state.flashcard_review_index = (current_index + 1) % total_cards
        st.session_state.show_flashcard_answer = False
        st.rerun()
