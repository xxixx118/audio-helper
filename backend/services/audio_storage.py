import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import settings
from errors import AppError

AUDIO_ID_PATTERN = re.compile(r"^rec_[0-9a-f]{32}$")


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


def _raise_audio_not_found(stage: str) -> None:
    raise AppError(
        404,
        "AUDIO_NOT_FOUND",
        "录音已过期或不存在，请重新录音。",
        stage,
    )


def load_audio_record(audio_id: str, *, stage: str = "asr") -> dict:
    if not AUDIO_ID_PATTERN.fullmatch(audio_id or ""):
        _raise_audio_not_found(stage)

    meta_path = audio_meta_path(audio_id)
    file_path = audio_file_path(audio_id)
    if not meta_path.exists() or not file_path.exists():
        _raise_audio_not_found(stage)

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        created_at = datetime.fromisoformat(str(meta["created_at"]))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        _raise_audio_not_found(stage)

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    ttl = timedelta(hours=settings.audio_ttl_hours)
    if utc_now() - created_at > ttl:
        _raise_audio_not_found(stage)

    content = file_path.read_bytes()
    if not content:
        _raise_audio_not_found(stage)

    return {
        "audio_id": audio_id,
        "content": content,
        "mime_type": str(meta.get("mime_type") or "audio/webm"),
        "created_at": created_at,
        "meta": meta,
    }
