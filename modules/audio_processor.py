import base64
import mimetypes
import os
import uuid
from pathlib import Path

import requests

from modules.security import is_path_inside, sanitize_filename


AUDIO_TYPES = {"MP3", "WAV", "M4A", "OGG", "WEBM"}
MAX_AUDIO_MB = int(os.getenv("STUDYMATE_MAX_AUDIO_MB", "10"))
MAX_AUDIO_BYTES = MAX_AUDIO_MB * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHAT_UPLOAD_DIR = PROJECT_ROOT / "data" / "chat_uploads"
GEMINI_AUDIO_PROMPT = (
    "Transcribe this student audio clearly. If the audio is unclear, return the "
    "readable parts and mention that some parts were unclear. Return only the transcript."
)


def validate_audio_file(file_name, file_size):
    """Validate a chat audio upload before saving or transcribing it."""
    safe_name, error = sanitize_filename(file_name)
    if error:
        return "", error

    file_type = Path(safe_name).suffix.replace(".", "").upper()
    if file_type not in AUDIO_TYPES:
        return "", "This audio format is not supported."

    if int(file_size or 0) > MAX_AUDIO_BYTES:
        return "", f"Audio file too large. Please upload audio under {MAX_AUDIO_MB} MB."

    return safe_name, ""


def save_audio_file(user_id, chat_session_id, uploaded_file):
    """Save an uploaded/recorded audio file under the current user's chat folder."""
    if not user_id or not chat_session_id or not uploaded_file:
        return None, "Audio file is missing."

    safe_name, error = validate_audio_file(
        getattr(uploaded_file, "name", "voice_recording.wav"),
        getattr(uploaded_file, "size", 0) or 0,
    )
    if error:
        return None, error

    upload_root = CHAT_UPLOAD_DIR / str(user_id) / str(chat_session_id) / "audio"
    upload_root.mkdir(parents=True, exist_ok=True)
    suffix = Path(safe_name).suffix.lower()
    unique_name = f"{Path(safe_name).stem}_{uuid.uuid4().hex[:8]}{suffix}"
    file_path = upload_root / unique_name
    if not is_path_inside(upload_root, file_path):
        return None, "Audio file path was rejected for safety."

    file_path.write_bytes(uploaded_file.getvalue())
    return {
        "file_name": safe_name,
        "file_path": str(file_path),
        "file_type": suffix.replace(".", "").upper(),
        "mime_type": getattr(uploaded_file, "type", "") or mimetypes.guess_type(safe_name)[0] or "",
        "file_size": int(getattr(uploaded_file, "size", 0) or file_path.stat().st_size),
    }, ""


def get_audio_duration(file_path):
    """Return audio duration in seconds when optional libraries can read it."""
    try:
        from pydub import AudioSegment

        return round(len(AudioSegment.from_file(file_path)) / 1000, 1)
    except Exception:
        return None


def transcribe_with_local_whisper(file_path):
    """Try optional local Whisper packages without making them required."""
    try:
        from faster_whisper import WhisperModel

        model_name = os.getenv("STUDYMATE_WHISPER_MODEL", "base")
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(file_path))
        transcript = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        return {
            "transcript": transcript.strip(),
            "method": "whisper",
            "warnings": [] if transcript.strip() else ["Could not transcribe this audio. Please try a clearer recording."],
        }
    except Exception:
        pass

    try:
        import whisper

        model_name = os.getenv("STUDYMATE_WHISPER_MODEL", "base")
        model = whisper.load_model(model_name)
        result = model.transcribe(str(file_path))
        transcript = (result.get("text") or "").strip()
        return {
            "transcript": transcript,
            "method": "whisper",
            "warnings": [] if transcript else ["Could not transcribe this audio. Please try a clearer recording."],
        }
    except Exception:
        return {
            "transcript": "",
            "method": "unavailable",
            "warnings": ["Local speech-to-text is not installed on this deployment."],
        }


def transcribe_with_gemini_audio(file_path, api_key=None, model=None):
    """Transcribe audio with Gemini using the current user's API key."""
    if not api_key:
        return {
            "transcript": "",
            "method": "unavailable",
            "warnings": ["Gemini API key is missing for audio transcription."],
        }

    path = Path(file_path)
    mime_type = mimetypes.guess_type(str(path))[0] or "audio/wav"
    try:
        audio_bytes = path.read_bytes()
    except OSError:
        return {
            "transcript": "",
            "method": "unavailable",
            "warnings": ["Could not read this audio file safely."],
        }

    selected_model = model or os.getenv("GEMINI_AUDIO_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": GEMINI_AUDIO_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(audio_bytes).decode("ascii"),
                        }
                    },
                ]
            }
        ]
    }

    try:
        response = requests.post(url, params={"key": api_key}, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        transcript = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return {
            "transcript": transcript,
            "method": "gemini_audio",
            "warnings": [] if transcript else ["Could not transcribe this audio. Please try a clearer recording."],
        }
    except Exception:
        return {
            "transcript": "",
            "method": "unavailable",
            "warnings": ["Gemini audio transcription could not complete. Try a clearer recording or local transcription."],
        }


def transcribe_audio(file_path, provider="auto", api_key=None, model=None):
    """Transcribe audio using Gemini or optional local Whisper, with safe fallbacks."""
    clean_provider = (provider or "auto").lower()
    warnings = []

    if clean_provider in {"auto", "gemini", "gemini_audio"}:
        gemini_result = transcribe_with_gemini_audio(file_path, api_key=api_key, model=model)
        if gemini_result.get("transcript"):
            return gemini_result
        warnings.extend(gemini_result.get("warnings", []))

    if clean_provider in {"auto", "local", "whisper", "local_whisper"}:
        local_result = transcribe_with_local_whisper(file_path)
        if local_result.get("transcript"):
            return local_result
        warnings.extend(local_result.get("warnings", []))

    return {
        "transcript": "",
        "method": "unavailable",
        "warnings": warnings or ["Voice transcription is not available in Demo Mode."],
    }
