import re
from pathlib import Path


ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".docx", ".pptx"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def clean_text(value, max_length=200):
    """Trim user text and cap its length for safer storage and prompts."""
    text = (value or "").strip()
    return text[:max_length]


def validate_full_name(name):
    """Return a cleaned full name or a friendly validation error."""
    cleaned = clean_text(name, max_length=80)
    if not cleaned:
        return "", "Please enter your full name."
    if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,79}", cleaned):
        return "", "Use letters, spaces, dots, apostrophes, or hyphens in your name."
    return cleaned, ""


def normalize_email(email):
    """Normalize email addresses before saving or comparing them."""
    return clean_text(email, max_length=120).lower()


def validate_email(email):
    """Return a normalized email or a friendly validation error."""
    cleaned = normalize_email(email)
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned):
        return "", "Please enter a valid email address."
    return cleaned, ""


def validate_password(password):
    """Validate password strength for student accounts."""
    if len(password or "") < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", password):
        return "Password must include at least 1 letter."
    if not re.search(r"\d", password):
        return "Password must include at least 1 number."
    return ""


def validate_subject_name(name):
    """Validate and clean a subject name."""
    cleaned = clean_text(name, max_length=80)
    if not cleaned:
        return "", "Please enter a subject name."
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._()&+-]{0,79}", cleaned):
        return "", "Subject name contains unsupported characters."
    return cleaned, ""


def validate_description(description, max_length=600):
    """Clean optional descriptions without making them required."""
    return clean_text(description, max_length=max_length)


def validate_chat_question(question, max_length=1200):
    """Validate chat questions before sending them to AI providers."""
    cleaned = clean_text(question, max_length=max_length)
    if not cleaned:
        return "", "Please type a question first."
    if len((question or "").strip()) > max_length:
        return "", f"Please keep your question under {max_length} characters."
    return cleaned, ""


def sanitize_filename(file_name):
    """Create a safe upload filename and reject path traversal attempts."""
    original = (file_name or "").strip()
    if not original:
        return "", "File name is missing."

    if "/" in original or "\\" in original or ".." in original:
        return "", "File name is not safe. Please rename the file and upload again."

    path = Path(original)
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        return "", "Only PDF, TXT, DOCX, and PPTX files are allowed."

    safe_stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", path.stem).strip(" ._")
    if not safe_stem:
        safe_stem = "study_notes"

    return f"{safe_stem[:90]}{suffix}", ""


def validate_upload(uploaded_file):
    """Validate Streamlit uploaded files before saving them."""
    safe_name, error = sanitize_filename(uploaded_file.name if uploaded_file else "")
    if error:
        return "", error

    size = getattr(uploaded_file, "size", 0) or 0
    if size > MAX_UPLOAD_BYTES:
        return "", "This file is too large. Please upload a file under 25 MB."

    return safe_name, ""


def is_path_inside(parent, child):
    """Return True only when child resolves inside parent."""
    try:
        parent_path = Path(parent).resolve()
        child_path = Path(child).resolve()
    except OSError:
        return False

    return child_path == parent_path or parent_path in child_path.parents
