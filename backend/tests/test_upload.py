from pathlib import Path

from fastapi.testclient import TestClient

from errors import AppError
from main import app
from services.audio_probe import AudioProbeResult

client = TestClient(app)


def _ok_probe() -> AudioProbeResult:
    return AudioProbeResult(
        format_name="matroska,webm",
        codec_name="opus",
        duration_seconds=3.2,
        duration_source="packets",
    )


def test_upload_success_returns_audio_id(monkeypatch, tmp_path):
    monkeypatch.setattr("config.settings.audio_storage_dir", tmp_path)
    monkeypatch.setattr(
        "api.upload.validate_uploaded_audio",
        lambda path: _ok_probe(),
    )

    response = client.post(
        "/upload",
        files={"file": ("sample.webm", b"fake-webm-bytes", "audio/webm")},
    )

    assert response.status_code == 200
    body = response.json()
    audio_id = body["data"]["audio_id"]
    assert audio_id.startswith("rec_")
    assert "/" not in audio_id
    assert "\\" not in audio_id
    assert (tmp_path / f"{audio_id}.webm").exists()
    assert (tmp_path / f"{audio_id}.json").exists()


def test_upload_missing_file_returns_422():
    response = client.post("/upload")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert body["error"]["stage"] == "upload"


def test_upload_empty_file_returns_422():
    response = client.post(
        "/upload",
        files={"file": ("empty.webm", b"", "audio/webm")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_upload_file_too_large_returns_413(monkeypatch, tmp_path):
    monkeypatch.setattr("config.settings.audio_storage_dir", tmp_path)
    monkeypatch.setattr("config.settings.max_audio_bytes", 16)

    response = client.post(
        "/upload",
        files={"file": ("big.webm", b"x" * 17, "audio/webm")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_upload_unsupported_format_returns_415(monkeypatch, tmp_path):
    monkeypatch.setattr("config.settings.audio_storage_dir", tmp_path)

    def reject(_path: Path) -> AudioProbeResult:
        raise AppError(
            415,
            "UNSUPPORTED_MEDIA_TYPE",
            "当前录音格式不受支持，请使用可录制 WebM/Opus 的浏览器。",
            "upload",
        )

    monkeypatch.setattr("api.upload.validate_uploaded_audio", reject)

    response = client.post(
        "/upload",
        files={"file": ("note.mp3", b"not-webm", "audio/mpeg")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert list(tmp_path.iterdir()) == []


def test_upload_invalid_duration_returns_422(monkeypatch, tmp_path):
    monkeypatch.setattr("config.settings.audio_storage_dir", tmp_path)

    def reject(_path: Path) -> AudioProbeResult:
        raise AppError(
            422,
            "INVALID_AUDIO_DURATION",
            "录音时长需在1到60秒之间，请重新录制。",
            "upload",
        )

    monkeypatch.setattr("api.upload.validate_uploaded_audio", reject)

    response = client.post(
        "/upload",
        files={"file": ("short.webm", b"fake-webm-bytes", "audio/webm")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_AUDIO_DURATION"
    assert list(tmp_path.iterdir()) == []
