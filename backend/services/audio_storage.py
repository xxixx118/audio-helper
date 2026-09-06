import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_audio_id() -> str:
    return f"rec_{uuid.uuid4().hex}"


def audio_dir() -> Path:
    path = settings.audio_storage_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def audio_file_path(audio_id: str) -> Path:
    return audio_dir() / f"{audio_id}.webm"


def audio_meta_path(audio_id: str) -> Path:
    return audio_dir() / f"{audio_id}.json"


def save_audio_bytes(audio_id: str, content: bytes) -> Path:
    path = audio_file_path(audio_id)
    path.write_bytes(content)
    return path


def save_audio_metadata(
    audio_id: str,
    *,
    size: int,
    duration_seconds: float,
    mime_type: str,
    duration_source: str,
) -> Path:
    created_at = utc_now()
    payload = {
        "audio_id": audio_id,
        "created_at": created_at.isoformat(),
        "expires_in_hours": settings.audio_ttl_hours,
        "size": size,
        "duration_seconds": duration_seconds,
        "mime_type": mime_type,
        "duration_source": duration_source,
    }
    path = audio_meta_path(audio_id)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def delete_audio(audio_id: str) -> None:
    for path in (audio_file_path(audio_id), audio_meta_path(audio_id)):
        if path.exists():
            path.unlink()
