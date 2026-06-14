import html
from datetime import datetime

import streamlit as st

from modules import ai_engine
from modules.auth import get_current_user_display_name, require_login
from modules.database import get_documents_by_subject, get_subjects, init_db
from modules.security import validate_chat_question
from modules.ui import (
    apply_theme,
    page_header,
    render_empty_state,
    render_feature_card,
    section_title,
    sidebar_nav,
)
from modules.vector_store import VectorStoreError, query_subject_notes


ANSWER_STYLES = ["Simple English", "Roman Urdu", "Exam Style", "Viva Style"]
CHAT_MODES = [
    "General Chat",
    "Chat with Subject",
    "Chat with Specific Notes",
    "Chat with Multiple Notes",
    "Teach Me Mode",
]
TEACH_MATERIAL_OPTIONS = [
    "General Knowledge",
    "Whole Subject Notes",
    "Specific Note",
    "Multiple Notes",
]
LEARNING_LEVELS = [
    "Beginner",
    "Normal",
    "Exam Preparation",
    "Viva Preparation",
    "Last Night Revision",
]
LANGUAGE_STYLES = [
    "Simple English",
    "Roman Urdu",
    "Mixed English + Roman Urdu",
]
TEACHING_DEPTHS = ["Quick", "Balanced", "Deep Explanation"]
DEFAULT_TEACH_SUGGESTIONS = [
    "Explain again more simply",
    "Give me a real-life example",
    "Ask me a question",
    "Give exam-style answer",
    "Show a diagram",
]
MODE_BADGES = {
    "General Chat": "General AI",
    "Chat with Subject": "Subject-based",
    "Chat with Specific Notes": "Single note",
    "Chat with Multiple Notes": "Multiple notes",
    "Teach Me Mode": "Teach Me Mode",
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


def render_follow_up_suggestions(message_index, suggestions):
    """Render suggested tutor follow-ups as small buttons."""
    if not suggestions:
        return

    st.markdown("**Try next:**")
    cols = st.columns(min(3, len(suggestions)))
    for index, suggestion in enumerate(suggestions):
        with cols[index % len(cols)]:
            if st.button(
                suggestion,
                key=f"teach_suggestion_{message_index}_{index}",
                use_container_width=True,
            ):
                st.session_state.study_chat_pending_prompt = suggestion
                st.rerun()


def _chat_messages_key():
    """Return the active chat history key for the logged-in user."""
    return f"study_chat_messages_user_{st.session_state.get('user_id', 'guest')}"


def _chat_messages():
    """Return this user's active session chat history."""
    key = _chat_messages_key()
    if key not in st.session_state:
        st.session_state[key] = []
    st.session_state.study_chat_messages = st.session_state[key]
    return st.session_state[key]


def _set_chat_messages(messages):
    """Replace only this user's active session chat history."""
    key = _chat_messages_key()
    st.session_state[key] = messages
    st.session_state.study_chat_messages = st.session_state[key]


def _message_timestamp():
    """Return a simple timestamp for chat history records."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_chat_pair(question, answer_data, context):
    """Append one user message and one assistant response to session history."""
    messages = _chat_messages()
    timestamp = _message_timestamp()
    messages.append(
        {
            "role": "user",
            "content": question,
            "context": context,
            "created_at": timestamp,
        }
    )
    messages.append(
        {
            "role": "assistant",
            "content": answer_data["answer"],
            "sources": answer_data["sources"],
            "warning": answer_data["warning"],
            "source_count": answer_data["source_count"],
            "context": context,
            "suggestions": answer_data.get("suggestions", []),
            "created_at": _message_timestamp(),
        }
    )


def add_assistant_message(answer_data, context):
    """Append only an assistant response, used when regenerating."""
    _chat_messages().append(
        {
            "role": "assistant",
            "content": answer_data["answer"],
            "sources": answer_data["sources"],
            "warning": answer_data["warning"],
            "source_count": answer_data["source_count"],
            "context": context,
            "suggestions": answer_data.get("suggestions", []),
            "created_at": _message_timestamp(),
        }
    )


def _compact_chat_history(limit=6):
    """Return a compact recent chat history for tutor continuity."""
    recent_messages = st.session_state.get(_chat_messages_key(), [])[-limit:]
    lines = []
    for message in recent_messages:
        role = "Student" if message.get("role") == "user" else "Tutor"
        content = str(message.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content[:900]}")
    return "\n".join(lines)


def _demo_teach_response(
    topic,
    learning_level,
    language_style,
    teaching_depth,
    notes_context="",
    user_message="",
    first_lesson=False,
):
    """Return a useful teaching template when Demo Mode is selected."""
    source_note = (
        "I found relevant uploaded note chunks and I am using them as the lesson base."
        if notes_context
        else "I could not find this directly in your uploaded notes, so I'm teaching it using general academic knowledge."
    )

    if not first_lesson:
        return f"""
{source_note}

## Tutor Feedback
I read your message: **{user_message or 'your follow-up'}**.

### What you are doing well
- You are continuing the lesson instead of just memorizing.
- You are focusing on **{topic}**, which helps build concept clarity.

### Improved Explanation
Let's simplify **{topic}** again:

```text
Main idea -> Why it matters -> Example -> Practice
```

For **{learning_level}**, explain the topic in this order:

| Step | What to say |
|---|---|
| 1 | Define the topic in one simple line |
| 2 | Explain the purpose |
| 3 | Give one example |
| 4 | Mention one common mistake |

### Mini Example
If the topic feels hard, connect it to a small real-life example first, then
write the academic version.

### Quick Check
Now answer in one or two lines: what is the main purpose of **{topic}**?

### Next Suggestions
- Explain again more simply
- Give me a real-life example
- Ask me a question
- Give exam-style answer
- Test me like viva

Demo Mode is active, so this is a basic offline tutor response.
"""

    return f"""
{source_note}

## 1. Topic Roadmap
- Understand what **{topic}** means.
- Break it into simple parts.
- See one easy example.
- Practice with a quick check question.

## 2. Simple Meaning
{topic} is an important study concept. In **{language_style}**, start by asking:
what problem does this topic solve, and where do we use it?

## 3. Concept Breakdown
| Part | What to learn |
|---|---|
| Definition | Basic meaning |
| Steps | How it works |
| Example | How to apply it |
| Mistakes | What to avoid |

## 4. Visual Explanation
```text
Topic -> Meaning -> Steps -> Example -> Practice
```

## 5. Real-Life Example
Think of this topic like organizing a messy study desk: first identify the problem,
then arrange things step by step.

## 6. Academic / Exam Explanation
For **{learning_level}**, write a clear definition, explain the main points, and add
one relevant example.

## 7. Important Points
- Learn the definition.
- Understand the purpose.
- Practice examples.
- Avoid memorizing without meaning.

## 8. Common Mistakes
- Skipping the basic definition.
- Mixing similar concepts.
- Not practicing examples.

## 9. Quick Check Question
In your own words, what is the main purpose of **{topic}**?

## 10. Follow-up Suggestions
- Explain again more simply
- Give me a real-life example
- Ask me a question
- Give exam-style answer
- Show a diagram

Demo Mode is active, so this is a basic offline teaching template.
"""


def build_teach_me_prompt(
    user_name,
    topic,
    learning_level,
    language_style,
    teaching_depth,
    notes_context,
    chat_history,
    user_message,
    context_label,
    first_lesson=False,
):
    """Build the tutor prompt for Teach Me Mode."""
    notes_instruction = (
        f"Uploaded notes context is available ({context_label}). Use it first."
        if notes_context
        else (
            "No uploaded notes context is available. Clearly say: "
            "\"I could not find this directly in your uploaded notes, so I'm teaching it using general academic knowledge.\""
        )
    )
    depth_instruction = {
        "Quick": "Keep it concise but still useful.",
        "Balanced": "Use a medium-length explanation with examples and a quick check.",
        "Deep Explanation": "Give a detailed, step-by-step explanation with visuals, examples, mistakes, and practice.",
    }.get(teaching_depth, "Use a balanced explanation.")

    if first_lesson:
        response_structure = """
For the first lesson response, use exactly these sections:
1. Topic Roadmap
2. Simple Meaning
3. Concept Breakdown
4. Visual Explanation
5. Real-Life Example
6. Academic / Exam Explanation
7. Important Points
8. Common Mistakes
9. Quick Check Question
10. Follow-up Suggestions
Use clean Markdown headings, bullets, and tables. For math or logic topics,
use formulas, truth tables, ASCII diagrams, or step-by-step solving when useful.
"""
    else:
        response_structure = """
Continue the same lesson context. Detect whether the student is answering,
asking for an easier explanation, requesting an example, quiz, exam answer,
viva answer, next topic, or saying they do not understand. If they answered a
question, give feedback, mention what is correct/missing, improve the answer,
and ask the next question.
"""

    return f"""
You are {user_name}'s AI Study Tutor inside StudyMate AI. You teach like a
patient expert teacher. Your job is not only to answer, but to make the student
understand deeply. Use uploaded notes when available, but if notes do not cover
the topic, clearly say so and continue using general academic knowledge.
Explain step-by-step, use visuals, examples, tables, formulas, logical
breakdowns, and ask follow-up questions. Keep the explanation student-friendly,
exam-focused, and concept-based.

Student name: {user_name}
Topic: {topic}
Learning level: {learning_level}
Language style: {language_style}
Teaching depth: {teaching_depth}
Depth instruction: {depth_instruction}
Notes instruction: {notes_instruction}

Recent lesson history:
{chat_history or "No previous lesson messages yet."}

Uploaded notes context:
{notes_context or "No relevant note chunks selected."}

Student message:
{user_message}

{response_structure}

Always include a Quick Check question unless the student specifically asks for
only a concise exam/viva answer. End with 3-5 follow-up suggestions as bullets.
"""


def _teach_suggestions():
    """Return default Teach Me Mode follow-up suggestions."""
    return DEFAULT_TEACH_SUGGESTIONS


def generate_teach_me_answer(question, context, first_lesson=False):
    """Generate a Teach Me Mode tutor response with optional notes context."""
    sources = []
    warning = ""
    material_source = context.get("material_source", "General Knowledge")
    should_retrieve = (
        material_source != "General Knowledge"
        and context.get("subject_id") is not None
    )

    if should_retrieve:
        try:
            sources = query_subject_notes(
                subject_id=context["subject_id"],
                question=f"{context.get('topic', '')} {question}",
                limit=7 if context.get("teaching_depth") == "Deep Explanation" else 5,
                document_ids=context.get("document_ids", []),
                user_id=st.session_state.get("user_id"),
            )
        except VectorStoreError as exc:
            warning = str(exc)

    notes_context = "\n\n".join(
        f"Source {index} ({source.get('metadata', {}).get('file_name', 'Uploaded note')}): {source['text']}"
        for index, source in enumerate(sources, start=1)
    )

    if should_retrieve and not sources and not warning:
        warning = (
            "I could not find this directly in your uploaded notes, "
            "so I'm teaching it using general academic knowledge."
        )

    provider = get_provider_label()
    if provider == "Demo Mode":
        answer = _demo_teach_response(
            context.get("topic", "this topic"),
            context.get("learning_level", "Normal"),
            context.get("language_style", "Simple English"),
            context.get("teaching_depth", "Balanced"),
            notes_context=notes_context,
            user_message=question,
            first_lesson=first_lesson,
        )
    else:
        prompt = build_teach_me_prompt(
            user_name=get_current_user_display_name(),
            topic=context.get("topic", "this topic"),
            learning_level=context.get("learning_level", "Normal"),
            language_style=context.get("language_style", "Simple English"),
            teaching_depth=context.get("teaching_depth", "Balanced"),
            notes_context=notes_context,
            chat_history=_compact_chat_history(),
            user_message=question,
            context_label=context.get("source_label", context.get("label", "Teach Me Mode")),
            first_lesson=first_lesson,
        )
        try:
            answer = ai_engine.ask_ai(prompt)
        except Exception as exc:
            if hasattr(ai_engine, "safe_ai_error_message"):
                answer = ai_engine.safe_ai_error_message(exc)
            else:
                answer = "The selected AI provider could not complete the lesson."

    return {
        "answer": answer,
        "sources": sources,
        "warning": warning,
        "source_count": len(sources),
        "suggestions": _teach_suggestions(),
    }


def generate_chat_answer(question, answer_style, chat_mode, context):
    """
    Generate a chatbot response with a compatibility fallback.

    Streamlit Cloud can occasionally keep an older imported module in memory
    after a deploy. This wrapper prevents a hard crash if ai_engine is stale.
    """
    if chat_mode == "Teach Me Mode":
        return generate_teach_me_answer(
            question=question,
            context=context,
            first_lesson=context.get("first_lesson", False),
        )

    if hasattr(ai_engine, "generate_study_chat_response"):
        return ai_engine.generate_study_chat_response(
            question=question,
            answer_style=answer_style,
            chat_mode=chat_mode,
            subject_id=context["subject_id"],
            document_ids=context["document_ids"],
            context_label=context["label"],
            user_id=st.session_state.get("user_id"),
        )

    if chat_mode != "General Chat" and context["subject_id"] is not None:
        return ai_engine.chat_with_notes(
            subject_id=context["subject_id"],
            question=question,
            answer_style=answer_style,
            user_id=st.session_state.get("user_id"),
        )

    prompt = f"""
You are {get_current_user_display_name()}'s AI Study Assistant.
Answer this student question clearly and in a study-friendly way.
Answer style: {answer_style}

Question:
{question}
"""
    try:
        answer = ai_engine.ask_ai(prompt)
    except Exception as exc:
        if hasattr(ai_engine, "safe_ai_error_message"):
            answer = ai_engine.safe_ai_error_message(exc)
        else:
            answer = "The selected AI provider could not complete the request."

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

    if chat_mode == "Teach Me Mode":
        return dict(st.session_state.get("study_chat_teach_context", {}))

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
user_id = require_login()
init_db()
apply_theme()
sidebar_nav()

page_header(
    "Chat With Notes",
    "Ask from your notes, selected documents, or general AI knowledge.",
    f"{get_current_user_display_name()}'s Study Chatbot",
)

feature1, feature2, feature3 = st.columns(3)
with feature1:
    render_feature_card("Flexible context", "Ask generally, by subject, or from selected notes.", "\U0001f50d", "#14b8b4", "#d8fff6")
with feature2:
    render_feature_card("Real chat flow", "Messages stay in a clean session conversation.", "\U0001f4ac", "#2f7df6", "#e3efff")
with feature3:
    render_feature_card("Exam-ready answers", "Get explanations, examples, key points, and revision tips.", "\U0001f4dd", "#ffb703", "#fff3c4")

_chat_messages()
if "study_chat_last_question" not in st.session_state:
    st.session_state.study_chat_last_question = ""
if "study_chat_last_request" not in st.session_state:
    st.session_state.study_chat_last_request = None
if "study_chat_teach_context" not in st.session_state:
    st.session_state.study_chat_teach_context = {}
if "study_chat_pending_prompt" not in st.session_state:
    st.session_state.study_chat_pending_prompt = ""

subjects = get_subjects(user_id=user_id)
prefill_subject_id = st.session_state.pop("chat_prefill_subject_id", None)
prefill_document_id = st.session_state.pop("chat_prefill_document_id", None)
prefill_question = st.session_state.pop("chat_prefill_question", "")

section_title("Chat Settings", "\u2699\ufe0f")
with st.container(border=True):
    top_col1, top_col2, top_col3 = st.columns([1.2, 1.2, 1])

    with top_col1:
        default_mode_index = 0
        if prefill_document_id:
            st.session_state.study_chat_mode_selector = "Chat with Specific Notes"
        elif prefill_subject_id:
            st.session_state.study_chat_mode_selector = "Chat with Subject"
        elif st.session_state.get("study_chat_mode_selector") not in CHAT_MODES:
            st.session_state.study_chat_mode_selector = CHAT_MODES[default_mode_index]
        chat_mode = st.selectbox(
            "Chat mode",
            CHAT_MODES,
            index=default_mode_index,
            key="study_chat_mode_selector",
        )

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

    if chat_mode not in {"General Chat", "Teach Me Mode"}:
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
            subject_documents = list(
                get_documents_by_subject(selected_subject["id"], user_id=user_id)
            )

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
            _set_chat_messages([])
            st.session_state.study_chat_last_question = ""
            st.session_state.study_chat_last_request = None
            st.session_state.study_chat_teach_context = {}
            st.session_state.study_chat_pending_prompt = ""
            st.rerun()
    with action_col2:
        if st.button("Regenerate Last Answer", use_container_width=True):
            if st.session_state.study_chat_last_question:
                st.session_state.study_chat_regenerate = True
                st.rerun()
            else:
                st.info("Ask a question first, then regenerate.")

if chat_mode == "Teach Me Mode":
    section_title("Tutor Setup", "\U0001f9d1\u200d\U0001f3eb")
    with st.container(border=True):
        tutor_col1, tutor_col2 = st.columns(2)
        with tutor_col1:
            teach_material = st.selectbox("Material selector", TEACH_MATERIAL_OPTIONS)
        with tutor_col2:
            teach_subject = None
            teach_subject_documents = []
            if teach_material == "General Knowledge":
                st.selectbox("Subject (optional)", ["No subject selected"], disabled=True)
            elif not subjects:
                st.selectbox("Subject", ["Create a subject first"], disabled=True)
                st.warning("Create a subject or choose General Knowledge.")
            else:
                teach_subject_name = st.selectbox(
                    "Subject",
                    [subject["name"] for subject in subjects],
                    key="teach_subject_selector",
                )
                teach_subject = next(
                    subject for subject in subjects if subject["name"] == teach_subject_name
                )
                teach_subject_documents = list(
                    get_documents_by_subject(teach_subject["id"], user_id=user_id)
                )

        teach_selected_documents = []
        if teach_material in {"Specific Note", "Multiple Notes"} and teach_subject:
            if not teach_subject_documents:
                st.warning("No uploaded documents found for this subject yet.")
            else:
                teach_document_options = {
                    f"{document['file_name']} ({document['chunk_count']} chunks)": document
                    for document in teach_subject_documents
                }
                if teach_material == "Specific Note":
                    teach_label = st.selectbox(
                        "Specific note",
                        list(teach_document_options.keys()),
                        key="teach_specific_note",
                    )
                    teach_selected_documents = [teach_document_options[teach_label]]
                else:
                    teach_labels = st.multiselect(
                        "Multiple notes",
                        list(teach_document_options.keys()),
                        default=list(teach_document_options.keys())[:2],
                        key="teach_multiple_notes",
                    )
                    teach_selected_documents = [
                        teach_document_options[label] for label in teach_labels
                    ]

        topic = st.text_input(
            "Topic",
            placeholder="Example: Database Normalization, K-map, Polymorphism, Probability",
            key="teach_topic",
        )
        level_col, language_col, depth_col = st.columns(3)
        with level_col:
            learning_level = st.selectbox("Learning level", LEARNING_LEVELS)
        with language_col:
            language_style = st.selectbox("Language style", LANGUAGE_STYLES)
        with depth_col:
            teaching_depth = st.selectbox("Teaching depth", TEACHING_DEPTHS, index=1)

        source_label = teach_material
        if teach_material == "Whole Subject Notes" and teach_subject:
            source_label = f"Whole Subject Notes: {teach_subject['name']}"
        elif teach_material == "Specific Note" and teach_selected_documents:
            source_label = f"Specific Note: {teach_selected_documents[0]['file_name']}"
        elif teach_material == "Multiple Notes" and teach_selected_documents:
            source_label = f"Multiple Notes: {len(teach_selected_documents)} selected"

        st.markdown(
            f"""
            <span class='status-pill'>Teach Me Mode</span>
            <span class='status-pill'>Topic: {html.escape(topic.strip() or 'Not started')}</span>
            <span class='status-pill'>Level: {html.escape(learning_level)}</span>
            <span class='status-pill'>Language: {html.escape(language_style)}</span>
            <span class='status-pill'>Source: {html.escape(source_label)}</span>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Start Lesson",
            type="primary",
            key="start_teach_lesson",
            use_container_width=True,
        ):
            clean_topic = topic.strip()
            if not clean_topic:
                st.warning("Enter a topic first.")
                st.stop()
            if teach_material != "General Knowledge" and not teach_subject:
                st.warning("Select a subject or choose General Knowledge.")
                st.stop()
            if teach_material == "Specific Note" and not teach_selected_documents:
                st.warning("Select one uploaded note first.")
                st.stop()
            if teach_material == "Multiple Notes" and not teach_selected_documents:
                st.warning("Select at least one uploaded note first.")
                st.stop()

            teach_context = {
                "subject_id": teach_subject["id"] if teach_subject else None,
                "document_ids": [document["id"] for document in teach_selected_documents],
                "label": f"Teach Me: {clean_topic}",
                "badge": "Teach Me Mode",
                "topic": clean_topic,
                "material_source": teach_material,
                "learning_level": learning_level,
                "language_style": language_style,
                "teaching_depth": teaching_depth,
                "source_label": source_label,
                "first_lesson": True,
            }
            request_context = dict(teach_context)
            active_context = dict(teach_context)
            active_context["first_lesson"] = False
            st.session_state.study_chat_teach_context = active_context
            start_prompt = f"Start teaching me {clean_topic}."
            st.session_state.study_chat_last_question = start_prompt
            st.session_state.study_chat_last_request = {
                "question": start_prompt,
                "answer_style": language_style,
                "chat_mode": chat_mode,
                "context": request_context,
            }
            with st.spinner("StudyMate Tutor is preparing your lesson..."):
                answer_data = generate_chat_answer(
                    question=start_prompt,
                    answer_style=language_style,
                    chat_mode=chat_mode,
                    context=request_context,
                )
            add_chat_pair(start_prompt, answer_data, active_context)
            st.rerun()

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
messages = _chat_messages()
if not messages:
    render_empty_state(
        "Ask anything about your notes, subjects, or studies.",
        "Use General Chat or choose a subject/note above, then type at the bottom.",
        "\U0001f4ad",
    )

for message_index, message in enumerate(messages):
    avatar = "\U0001f468\u200d\U0001f393" if message["role"] == "user" else "\U0001f916"
    with st.chat_message(message["role"], avatar=avatar):
        message_context = message.get("context", {})
        if message_context:
            st.caption(f"{message_context.get('badge', 'Chat')} | {message_context.get('label', '')}")
        if message.get("created_at"):
            st.caption(message["created_at"])

        if message.get("warning"):
            st.warning(message["warning"])

        st.markdown(message["content"])

        if message["role"] == "assistant":
            source_count = message.get("source_count", 0)
            if source_count:
                st.caption(f"Using {source_count} relevant note chunks")
            render_sources(message.get("sources", []))
            if message_context.get("badge") == "Teach Me Mode":
                render_follow_up_suggestions(
                    message_index,
                    message.get("suggestions", []),
                )

if st.session_state.get("study_chat_regenerate"):
    st.session_state.study_chat_regenerate = False
    messages = _chat_messages()
    if messages and messages[-1]["role"] == "assistant":
        messages.pop()

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

pending_prompt = st.session_state.pop("study_chat_pending_prompt", "")
typed_prompt = st.chat_input("Ask StudyMate anything... Follow-up questions are welcome.")
prompt = pending_prompt or typed_prompt

if prompt:
    clean_prompt, prompt_error = validate_chat_question(prompt)
    if prompt_error:
        st.warning(prompt_error)
        st.stop()

    if chat_mode == "Teach Me Mode":
        context = dict(st.session_state.get("study_chat_teach_context", {}))
        if not context:
            st.warning("Start a lesson first by entering a topic in Teach Me Mode.")
            st.stop()
        context["first_lesson"] = False
    elif chat_mode != "General Chat" and not selected_subject:
        st.warning("Select a subject first, or switch to General Chat.")
        st.stop()

    if chat_mode == "Chat with Specific Notes" and not selected_documents:
        st.warning("Select one uploaded note first, or switch to General Chat.")
        st.stop()

    if chat_mode == "Chat with Multiple Notes" and not selected_documents:
        st.warning("Select at least one uploaded note first, or switch to General Chat.")
        st.stop()

    st.session_state.study_chat_last_question = clean_prompt
    st.session_state.study_chat_last_request = {
        "question": clean_prompt,
        "answer_style": answer_style,
        "chat_mode": chat_mode,
        "context": context,
    }
    with st.spinner("StudyMate is thinking..."):
        answer_data = generate_chat_answer(
            question=clean_prompt,
            answer_style=answer_style,
            chat_mode=chat_mode,
            context=context,
        )

    add_chat_pair(clean_prompt, answer_data, context)
    st.rerun()
