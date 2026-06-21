import json
import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import jwt
from fastapi import FastAPI, HTTPException, Depends, Header, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from modules.database import (
    init_db,
    create_user,
    get_user_by_email,
    verify_user_login,
    get_subjects,
    add_subject as db_add_subject,
    delete_subject,
    get_documents_by_subject,
    save_uploaded_document_metadata,
    get_chat_sessions,
    get_chat_messages,
    save_chat_message,
    save_study_session,
    get_study_sessions,
    get_branding_settings,
    save_user_api_key,
    get_user_api_key_status,
    set_user_setting,
)
from modules import ai_engine
from modules.security import validate_email, validate_password, validate_full_name, sanitize_filename
from modules.text_splitter import split_text
from modules.vector_store import add_text_chunks, delete_subject_vectors
from modules.document_processor import process_uploaded_file, ocr_status
from modules.flashcard_generator import generate_flashcards
from modules.quiz_generator import generate_quiz, check_quiz_answers
from modules.planner import generate_revision_plan

# Initialize SQLite database
init_db()

app = FastAPI(title="StudyMate AI API")

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = os.getenv("JWT_SECRET", "studymate_premium_super_secret_key_1337")
JWT_ALGORITHM = "HS256"

# File upload directories matching existing configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
EXTRACTED_TEXT_DIR = PROJECT_ROOT / "data" / "extracted_text"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_TEXT_DIR.mkdir(parents=True, exist_ok=True)


# Dependency: Authentication helper
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication token is missing or invalid")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {
            "id": int(user_id),
            "email": payload.get("email"),
            "role": payload.get("role", "student"),
            "name": payload.get("name", "")
        }
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token has expired or is invalid")


# Models for Request Bodies
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class SubjectCreate(BaseModel):
    name: str
    description: str = ""

class RenameSessionRequest(BaseModel):
    title: str

class ChatRequest(BaseModel):
    question: str
    chat_mode: str = "General Chat"
    subject_id: Optional[int] = None
    document_ids: Optional[List[int]] = None
    answer_style: str = "Simple English"
    session_id: Optional[int] = None

class QuizGenerateRequest(BaseModel):
    subject_id: int
    topic: str
    question_type: str = "MCQ"
    difficulty: str = "Easy"
    question_count: int = 5

class QuizCheckRequest(BaseModel):
    questions: List[dict]
    user_answers: dict

class FlashcardGenerateRequest(BaseModel):
    subject_id: int
    topic: str
    card_count: int = 8

class PlanGenerateRequest(BaseModel):
    subject_name: str
    subject_id: int
    exam_date: str # YYYY-MM-DD
    preparation_level: int
    confidence_level: int
    weak_topics: List[str]

class PomodoroSaveRequest(BaseModel):
    subject_id: Optional[int] = None
    duration_minutes: int
    session_type: str = "Focus"
    notes: str = ""

class AISettingsSave(BaseModel):
    provider: str
    gemini_api_key: Optional[str] = None


# --- Authentication Endpoints ---

@app.post("/api/auth/signup")
def signup(req: SignupRequest):
    clean_name, name_error = validate_full_name(req.name)
    clean_email, email_error = validate_email(req.email)
    password_error = validate_password(req.password)

    if name_error or email_error or password_error:
        raise HTTPException(status_code=400, detail=name_error or email_error or password_error)

    if get_user_by_email(clean_email):
        raise HTTPException(status_code=400, detail="Account with this email already exists")

    from passlib.hash import pbkdf2_sha256
    password_hash = pbkdf2_sha256.hash(req.password)

    user_id = create_user(
        name=clean_name,
        email=clean_email,
        password_hash=password_hash,
        auth_provider="email",
    )
    if not user_id:
        raise HTTPException(status_code=500, detail="Could not create user account")

    user = get_user_by_email(clean_email)
    token = jwt.encode({
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "name": user["name"],
        "exp": datetime.utcnow() + timedelta(days=7)
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}}


@app.post("/api/auth/login")
def login(req: LoginRequest):
    clean_email, email_error = validate_email(req.email)
    if email_error or not req.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    from passlib.hash import pbkdf2_sha256
    def verify_pw(password, password_hash):
        try:
            return pbkdf2_sha256.verify(password, password_hash or "")
        except Exception:
            return False

    user = verify_user_login(clean_email, req.password, verify_pw)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = jwt.encode({
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "name": user["name"],
        "exp": datetime.utcnow() + timedelta(days=7)
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}}


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
    return {"user": user}


# --- Subjects Endpoints ---

@app.get("/api/subjects")
def list_subjects(user: dict = Depends(get_current_user)):
    subjects = get_subjects(user_id=user["id"])
    return [dict(sub) for sub in subjects]


@app.post("/api/subjects")
def add_subject(req: SubjectCreate, user: dict = Depends(get_current_user)):
    from modules.security import validate_subject_name, validate_description
    clean_name, error = validate_subject_name(req.name)
    if error:
        raise HTTPException(status_code=400, detail=error)
    clean_desc = validate_description(req.description)

    subject_id = db_add_subject(name=clean_name, description=clean_desc, user_id=user["id"])
    if not subject_id:
        raise HTTPException(status_code=500, detail="Failed to create subject")
    return {"id": subject_id, "name": clean_name, "description": clean_desc}


@app.delete("/api/subjects/{subject_id}")
def remove_subject(subject_id: int, user: dict = Depends(get_current_user)):
    try:
        delete_subject_vectors(subject_id, user_id=user["id"])
    except Exception:
        pass
    
    success = delete_subject(subject_id, user_id=user["id"])
    if not success:
        raise HTTPException(status_code=400, detail="Subject not found or access denied")
    return {"success": True}


# --- Documents Endpoints ---

@app.get("/api/documents/{subject_id}")
def list_documents(subject_id: int, user: dict = Depends(get_current_user)):
    docs = get_documents_by_subject(subject_id, user_id=user["id"])
    return [dict(doc) for doc in docs]


@app.post("/api/documents/upload")
def upload_document(
    subject_id: int = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    safe_name, error = sanitize_filename(file.filename)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # Resolve directories
    subject_folder = UPLOAD_DIR / str(user["id"]) / str(subject_id)
    text_subject_folder = EXTRACTED_TEXT_DIR / str(user["id"]) / str(subject_id)
    subject_folder.mkdir(parents=True, exist_ok=True)
    text_subject_folder.mkdir(parents=True, exist_ok=True)

    # Unique path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = subject_folder / f"{timestamp}_{safe_name}"
    text_path = text_subject_folder / f"{timestamp}_{Path(safe_name).stem}.txt"
    file_type = Path(safe_name).suffix.replace(".", "").upper() or "PDF"

    # Save original file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Process file and extract text
    process_result = process_uploaded_file(file_path, file_type)
    extracted_text = process_result["text"]
    text_path.write_text(extracted_text, encoding="utf-8")

    # Split and index text chunks
    chunks = split_text(extracted_text)
    warnings = list(process_result.get("warnings", []))
    warning_message = " ".join(warnings)

    # Save document metadata in DB
    document_id = save_uploaded_document_metadata(
        subject_id=subject_id,
        file_name=safe_name,
        file_path=str(file_path),
        file_type=file_type,
        extracted_text_path=str(text_path),
        chunk_count=len(chunks),
        description=description,
        extraction_method=process_result.get("method", ""),
        extraction_status=process_result.get("status", ""),
        warning_message=warning_message,
        page_count=process_result.get("page_count", 0),
        user_id=user["id"],
    )

    if not document_id:
        # Cleanup file if failed
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=403, detail="Access denied to this subject")

    # Add text chunks to ChromaDB
    saved_chunks = 0
    if chunks:
        try:
            # Look up subject info to fetch name
            subjects = get_subjects(user_id=user["id"])
            subject_name = next((sub["name"] for sub in subjects if sub["id"] == subject_id), "Subject")
            saved_chunks = add_text_chunks(
                subject_id=subject_id,
                subject_name=subject_name,
                document_id=document_id,
                file_name=safe_name,
                chunks=chunks,
                user_id=user["id"],
                file_type=file_type,
                extraction_method=process_result.get("method", ""),
            )
        except Exception:
            pass

    return {
        "id": document_id,
        "file_name": safe_name,
        "chunk_count": len(chunks),
        "saved_chunks": saved_chunks,
        "warning": warning_message,
        "status": process_result.get("status", "")
    }


# --- Chat Endpoints ---

@app.get("/api/chat/sessions")
def list_chat_sessions(subject_id: Optional[int] = None, user: dict = Depends(get_current_user)):
    sessions = get_chat_sessions(user_id=user["id"], subject_id=subject_id)
    return [dict(session) for session in sessions]


@app.get("/api/chat/messages/{session_id}")
def list_chat_messages(session_id: int, user: dict = Depends(get_current_user)):
    messages = get_chat_messages(user_id=user["id"], session_id=session_id)
    return [dict(msg) for msg in messages]


@app.delete("/api/chat/sessions/{session_id}")
def remove_chat_session(session_id: int, user: dict = Depends(get_current_user)):
    from modules.database import delete_chat_session
    success = delete_chat_session(user["id"], session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not delete chat session")
    return {"success": True}


@app.put("/api/chat/sessions/{session_id}")
def rename_chat_session(session_id: int, req: RenameSessionRequest, user: dict = Depends(get_current_user)):
    from modules.database import update_chat_session_title
    success = update_chat_session_title(user["id"], session_id, req.title)
    if not success:
        raise HTTPException(status_code=400, detail="Could not rename chat session")
    return {"success": True}


@app.post("/api/chat")
def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    session_id = req.session_id
    # If no session ID was sent, we create a temporary active session for this request
    if not session_id:
        from modules.database import create_chat_session
        session_id = create_chat_session(
            user_id=user["id"],
            subject_id=req.subject_id,
            title="Chat Session",
            chat_mode=req.chat_mode
        )

    # Save user message in DB
    save_chat_message(
        user_id=user["id"],
        session_id=session_id,
        role="user",
        content=req.question,
    )

    # Prepare historical context (recent 10 messages)
    history_messages = get_chat_messages(user_id=user["id"], session_id=session_id)
    history_lines = []
    for msg in history_messages[-10:-1]:  # exclude the last user message just added
        role_label = "Student" if msg["role"] == "user" else "Assistant"
        history_lines.append(f"{role_label}: {msg['content']}")
    chat_history = "\n".join(history_lines)

    # Fetch user memory profile
    from modules.ai_engine import format_user_memory_profile
    user_memory = format_user_memory_profile(user["id"])
    provider = "Gemini"

    # Call AI response builder
    answer_data = ai_engine.generate_study_chat_response(
        question=req.question,
        answer_style=req.answer_style,
        chat_mode=req.chat_mode,
        subject_id=req.subject_id,
        document_ids=req.document_ids,
        context_label=req.chat_mode,
        user_id=user["id"],
        chat_history=chat_history,
        user_memory=user_memory,
        provider=provider,
    )

    # Save assistant message in DB
    save_chat_message(
        user_id=user["id"],
        session_id=session_id,
        role="assistant",
        content=answer_data["answer"],
        metadata={
            "mode": req.chat_mode,
            "subject_id": req.subject_id,
            "provider": provider,
            "math_visualizations": answer_data.get("math_visualizations", []),
        },
        sources_json=json.dumps(answer_data.get("sources", [])),
        warning=answer_data.get("warning", ""),
        source_count=answer_data.get("source_count", 0),
    )

    return {
        "session_id": session_id,
        "answer": answer_data["answer"],
        "sources": answer_data.get("sources", []),
        "warning": answer_data.get("warning", ""),
        "math_visualizations": answer_data.get("math_visualizations", []),
    }


# --- Study Tools Endpoints ---

@app.post("/api/quiz/generate")
def quiz_generate(req: QuizGenerateRequest, user: dict = Depends(get_current_user)):
    # Check if subject belongs to user
    from modules.database import subject_belongs_to_user
    if not subject_belongs_to_user(req.subject_id, user["id"]):
        raise HTTPException(status_code=403, detail="Access denied to this subject")

    quiz_data = generate_quiz(
        subject_id=req.subject_id,
        topic=req.topic,
        question_type=req.question_type,
        difficulty=req.difficulty,
        question_count=req.question_count,
        user_id=user["id"],
    )
    if quiz_data.get("error"):
        raise HTTPException(status_code=400, detail=quiz_data["error"])
    return quiz_data


@app.post("/api/quiz/check")
def quiz_check(req: QuizCheckRequest, user: dict = Depends(get_current_user)):
    # Convert string key dict to integer key dict for Python verification
    parsed_answers = {int(k): v for k, v in req.user_answers.items()}
    feedback_data = check_quiz_answers(req.questions, parsed_answers)
    if feedback_data.get("error"):
        raise HTTPException(status_code=400, detail=feedback_data["error"])
    return feedback_data


@app.post("/api/flashcards/generate")
def flashcards_generate(req: FlashcardGenerateRequest, user: dict = Depends(get_current_user)):
    from modules.database import subject_belongs_to_user
    if not subject_belongs_to_user(req.subject_id, user["id"]):
        raise HTTPException(status_code=403, detail="Access denied to this subject")

    cards_data = generate_flashcards(
        subject_id=req.subject_id,
        topic=req.topic,
        card_count=req.card_count,
        user_id=user["id"],
    )
    if cards_data.get("error"):
        raise HTTPException(status_code=400, detail=cards_data["error"])

    # Automatically save generated cards to database
    for card in cards_data.get("flashcards", []):
        from modules.database import save_flashcard
        save_flashcard(
            subject_id=req.subject_id,
            question=card["question"],
            answer=card["answer"],
            topic=req.topic,
            user_id=user["id"],
        )

    return cards_data


@app.post("/api/planner/generate")
def planner_generate(req: PlanGenerateRequest, user: dict = Depends(get_current_user)):
    from modules.database import subject_belongs_to_user
    if not subject_belongs_to_user(req.subject_id, user["id"]):
        raise HTTPException(status_code=403, detail="Access denied to this subject")

    # Format exam_date string to datetime object
    try:
        exam_date_obj = datetime.strptime(req.exam_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    plan_text = generate_revision_plan(
        subject_name=req.subject_name,
        exam_date=exam_date_obj,
        preparation_level=req.preparation_level,
        confidence_level=req.confidence_level,
        weak_topics=req.weak_topics,
    )

    # Save revision plan to DB
    from modules.database import save_revision_plan
    plan_id = save_revision_plan(
        subject_id=req.subject_id,
        exam_date=exam_date_obj,
        preparation_level=req.preparation_level,
        confidence_level=req.confidence_level,
        weak_topics=req.weak_topics,
        plan_text=plan_text,
        user_id=user["id"],
    )

    return {"id": plan_id, "plan_text": plan_text}


# --- Pomodoro Endpoints ---

@app.post("/api/pomodoro/save")
def pomodoro_save(req: PomodoroSaveRequest, user: dict = Depends(get_current_user)):
    session_id = save_study_session(
        user_id=user["id"],
        subject_id=req.subject_id,
        duration_minutes=req.duration_minutes,
        session_type=req.session_type,
        notes=req.notes,
    )
    if not session_id:
        raise HTTPException(status_code=500, detail="Could not save Pomodoro session")
    return {"id": session_id, "success": True}


@app.get("/api/pomodoro/sessions")
def pomodoro_list(user: dict = Depends(get_current_user)):
    sessions = get_study_sessions(user_id=user["id"], limit=15)
    return [dict(session) for session in sessions]


# --- AI Settings Endpoints ---

@app.get("/api/settings/ai")
def get_ai_settings(user: dict = Depends(get_current_user)):
    gemini_status = get_user_api_key_status(user["id"], "gemini")
    
    return {
        "provider": "Gemini",
        "gemini_configured": bool(gemini_status and gemini_status.get("key_suffix")),
        "gemini_suffix": gemini_status.get("key_suffix", "") if gemini_status else "",
    }


@app.get("/api/settings/ocr")
def get_ocr_status():
    return {"status": ocr_status()}


@app.post("/api/settings/ai")
def save_ai_settings(req: AISettingsSave, user: dict = Depends(get_current_user)):
    provider = "Gemini"
    set_user_setting(user["id"], "ai_provider", provider)

    # Blank password fields mean "keep the existing saved key".
    if req.gemini_api_key and req.gemini_api_key.strip():
        save_user_api_key(user["id"], "gemini", req.gemini_api_key.strip())

    return {"success": True, "provider": provider}


# --- Static Files / Single Port Mounting ---
# Static files mounting will be added here once Vite frontend is compiled
dist_path = PROJECT_ROOT / "frontend" / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="static")
