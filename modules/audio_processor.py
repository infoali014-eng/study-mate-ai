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
MIN_AUDIO_BYTES = int(os.getenv("STUDYMATE_MIN_AUDIO_BYTES", "1024"))
MIN_AUDIO_SECONDS = float(os.getenv("STUDYMATE_MIN_AUDIO_SECONDS", "1.0"))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHAT_UPLOAD_DIR = PROJECT_ROOT / "data" / "chat_uploads"
GEMINI_AUDIO_PROMPT = (
    "Transcribe this audio clearly. Return only the spoken words. "
    "If speech is unclear, return the best possible transcription."
)
UNSUPPORTED_AUDIO_MESSAGE = "This audio format is not supported. Try WAV, MP3, M4A, OGG, or WEBM."


def _transcription_result(
    success,
    transcript="",
    method="unavailable",
    error="",
    warnings=None,
    technical_error="",
    status=None,
):
    """Return a consistent, UI-safe transcription response."""
    return {
        "success": bool(success),
        "transcript": (transcript or "").strip(),
        "method": method,
        "error": error,
        "warnings": warnings or [],
        "technical_error": technical_error,
        "status": status or {},
    }


def _guess_audio_mime(file_path, fallback="audio/wav"):
    """Guess a stable audio mime type for Gemini inline data."""
    guessed = mimetypes.guess_type(str(file_path))[0]
    if guessed:
        return guessed

    extension = Path(file_path).suffix.lower()
    extension_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
    }
    return extension_map.get(extension, fallback)


def validate_audio_file(file_name, file_size):
    """Validate a chat audio upload before saving or transcribing it."""
    original_name = file_name or "voice_recording.wav"
    extension = Path(original_name).suffix.replace(".", "").upper()
    if extension not in AUDIO_TYPES:
        return "", UNSUPPORTED_AUDIO_MESSAGE

    safe_name, error = sanitize_filename(original_name)
    if error:
        return "", error

    size = int(file_size or 0)
    if size <= 0:
        return "", "No audio was recorded. Please record again and allow microphone permission."

    if size < MIN_AUDIO_BYTES:
        return "", "Recording is too short. Please speak for at least 2-3 seconds."

    if size > MAX_AUDIO_BYTES:
        return "", "Audio file is too large. Please upload a shorter recording."

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
    file_size = file_path.stat().st_size
    if file_size <= 0:
        return None, "No audio was recorded. Please record again and allow microphone permission."

    return {
        "file_name": safe_name,
        "file_path": str(file_path),
        "file_type": suffix.replace(".", "").upper(),
        "mime_type": getattr(uploaded_file, "type", "") or _guess_audio_mime(safe_name),
        "file_size": file_size,
    }, ""


def get_audio_duration(file_path):
    """Return audio duration in seconds when optional libraries can read it."""
    try:
        from pydub import AudioSegment

        return round(len(AudioSegment.from_file(file_path)) / 1000, 1)
    except Exception:
        return None


def inspect_audio_file(file_path, file_type=""):
    """Collect safe diagnostics for the UI without exposing local paths."""
    path = Path(file_path)
    status = {
        "audio_received": False,
        "file_type": (file_type or path.suffix.replace(".", "")).upper(),
        "file_size": 0,
        "duration": None,
        "mime_type": _guess_audio_mime(path),
    }

    if not path.exists() or not path.is_file():
        return status, "Audio file was not found. Please record or upload it again."

    status["audio_received"] = True
    status["file_size"] = path.stat().st_size
    status["duration"] = get_audio_duration(path)

    if status["file_size"] <= 0:
        return status, "No audio was recorded. Please record again and allow microphone permission."
    if status["file_size"] < MIN_AUDIO_BYTES:
        return status, "Recording is too short. Please speak for at least 2-3 seconds."
    if status["file_size"] > MAX_AUDIO_BYTES:
        return status, "Audio file is too large. Please upload a shorter recording."
    if status["duration"] is not None and status["duration"] < MIN_AUDIO_SECONDS:
        return status, "Recording is too short. Please speak for at least 2-3 seconds."

    return status, ""


def convert_audio_to_wav(file_path):
    """Convert browser-created audio, such as WEBM, to WAV when pydub/ffmpeg is available."""
    source = Path(file_path)
    if source.suffix.lower() == ".wav":
        return str(source), ""

    converted_path = source.with_suffix(".converted.wav")
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(source)
        audio.export(converted_path, format="wav")
        return str(converted_path), ""
    except Exception as exc:
        return (
            str(source),
            "Audio conversion is not available on this server. Try uploading a WAV or MP3 file.",
        )


def transcribe_with_local_whisper(file_path):
    """Try optional local Whisper packages without making them required."""
    try:
        from faster_whisper import WhisperModel

        model_name = os.getenv("STUDYMATE_WHISPER_MODEL", "base")
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(file_path))
        transcript = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        if transcript:
            return _transcription_result(True, transcript, method="local_whisper")
        return _transcription_result(
            False,
            method="local_whisper",
            error="No speech was detected. Please try again with clearer audio.",
        )
    except Exception as exc:
        first_error = str(exc)[:180]

    try:
        import whisper

        model_name = os.getenv("STUDYMATE_WHISPER_MODEL", "base")
        model = whisper.load_model(model_name)
        result = model.transcribe(str(file_path))
        transcript = (result.get("text") or "").strip()
        if transcript:
            return _transcription_result(True, transcript, method="local_whisper")
        return _transcription_result(
            False,
            method="local_whisper",
            error="No speech was detected. Please try again with clearer audio.",
        )
    except Exception as exc:
        technical = first_error or str(exc)[:180]
        return _transcription_result(
            False,
            method="unavailable",
            error="Local speech-to-text is not installed on this deployment.",
            technical_error=technical,
        )


def _extract_gemini_text(data):
    """Read transcript text from Gemini response variants."""
    try:
        parts = data.get("candidates", [])[0].get("content", {}).get("parts", [])
        text_parts = [part.get("text", "") for part in parts if part.get("text")]
        return "\n".join(text_parts).strip()
    except (IndexError, AttributeError, TypeError):
        return ""


def transcribe_with_gemini_audio(file_path, api_key, mime_type=None, model=None):
    """Transcribe audio with Gemini using the current user's API key."""
    if not api_key:
        return _transcription_result(
            False,
            method="unavailable",
            error="Voice transcription needs Gemini API key or local transcription support.",
        )

    path = Path(file_path)
    if not path.exists():
        return _transcription_result(
            False,
            method="gemini_audio",
            error="Audio file was not found. Please record or upload it again.",
        )

    try:
        audio_bytes = path.read_bytes()
    except OSError as exc:
        return _transcription_result(
            False,
            method="gemini_audio",
            error="Could not read this audio file safely.",
            technical_error=str(exc)[:180],
        )

    if not audio_bytes:
        return _transcription_result(
            False,
            method="gemini_audio",
            error="No audio was recorded. Please record again and allow microphone permission.",
        )

    selected_model = model or os.getenv("GEMINI_AUDIO_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": GEMINI_AUDIO_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type or _guess_audio_mime(path),
                            "data": base64.b64encode(audio_bytes).decode("ascii"),
                        }
                    },
                ]
            }
        ]
    }

    try:
        response = requests.post(url, params={"key": api_key}, json=payload, timeout=180)
        if response.status_code >= 400:
            return _transcription_result(
                False,
                method="gemini_audio",
                error="Gemini audio transcription could not complete. Check your API key, quota, or try again.",
                technical_error=f"HTTP {response.status_code}",
            )

        data = response.json()
        transcript = _extract_gemini_text(data)
        if transcript:
            return _transcription_result(True, transcript, method="gemini_audio")
        return _transcription_result(
            False,
            method="gemini_audio",
            error="No speech was detected. Please try again with clearer audio.",
        )
    except requests.RequestException as exc:
        return _transcription_result(
            False,
            method="gemini_audio",
            error="Gemini audio transcription could not complete. Check your network connection and try again.",
            technical_error=str(exc)[:180],
        )
    except (ValueError, KeyError, TypeError) as exc:
        return _transcription_result(
            False,
            method="gemini_audio",
            error="Gemini returned an unreadable transcription response. Please try again.",
            technical_error=str(exc)[:180],
        )


def transcribe_audio(file_path, provider="auto", api_key=None, model=None):
    """Transcribe audio using Gemini or optional local Whisper, with safe fallbacks."""
    clean_provider = (provider or "auto").lower()
    path = Path(file_path)
    status, status_error = inspect_audio_file(path)
    if status_error:
        return _transcription_result(False, method="unavailable", error=status_error, status=status)

    warnings = []
    candidates = [(str(path), status.get("mime_type"))]
    if path.suffix.lower() in {".webm", ".ogg", ".m4a"}:
        converted_path, conversion_warning = convert_audio_to_wav(path)
        if conversion_warning:
            warnings.append(conversion_warning)
        elif converted_path != str(path):
            candidates.insert(0, (converted_path, "audio/wav"))

    if clean_provider in {"auto", "gemini", "gemini_audio"} and api_key:
        for candidate_path, mime_type in candidates:
            gemini_result = transcribe_with_gemini_audio(
                candidate_path,
                api_key=api_key,
                mime_type=mime_type,
                model=model,
            )
            gemini_result["status"] = status
            if warnings:
                gemini_result["warnings"] = list(dict.fromkeys(warnings + gemini_result.get("warnings", [])))
            if gemini_result.get("success"):
                return gemini_result
            warnings.extend(gemini_result.get("warnings", []))
            last_error = gemini_result.get("error", "")
    else:
        last_error = "Voice transcription needs Gemini API key or local transcription support."

    if clean_provider in {"auto", "local", "whisper", "local_whisper"}:
        local_result = transcribe_with_local_whisper(candidates[0][0])
        local_result["status"] = status
        if warnings:
            local_result["warnings"] = list(dict.fromkeys(warnings + local_result.get("warnings", [])))
        if local_result.get("success"):
            return local_result
        warnings.extend(local_result.get("warnings", []))
        last_error = local_result.get("error") or last_error

    if not api_key and clean_provider in {"auto", "gemini", "gemini_audio"}:
        last_error = "Voice transcription needs Gemini API key or local transcription support."

    return _transcription_result(
        False,
        method="unavailable",
        error=last_error or "No speech was detected. Please try again with clearer audio.",
        warnings=list(dict.fromkeys(warnings)),
        status=status,
    )
