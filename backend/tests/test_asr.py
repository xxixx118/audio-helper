import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

from config import settings
from main import app
from services.audio_storage import new_audio_id, save_audio_bytes, save_audio_metadata

client = TestClient(app)


def _store_audio(tmp_path: Path, *, created_at: datetime | None = None) -> str:
    settings.audio_storage_dir = tmp_path
    audio_id = new_audio_id()
    save_audio_bytes(audio_id, b"fake-webm-bytes")
    save_audio_metadata(
        audio_id,
        size=16,
        duration_seconds=3.2,
        mime_type="audio/webm",
        duration_source="packets",
    )
    if created_at is not None:
        meta_path = tmp_path / f"{audio_id}.json"
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        payload["created_at"] = created_at.isoformat()
        meta_path.write_text(json.dumps(payload), encoding="utf-8")
    return audio_id


def test_asr_missing_field_returns_422():
    response = client.post("/asr", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert body["error"]["stage"] == "asr"


def test_asr_unknown_id_returns_404(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)
    response = client.post("/asr", json={"audio_id": "rec_" + "a" * 32})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AUDIO_NOT_FOUND"


def test_asr_expired_id_returns_404(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)
    expired = datetime.now(timezone.utc) - timedelta(hours=25)
    audio_id = _store_audio(tmp_path, created_at=expired)
    response = client.post("/asr", json={"audio_id": audio_id})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AUDIO_NOT_FOUND"


@respx.mock
def test_asr_success_returns_upstream_text(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)
    monkeypatch.setattr(settings, "bailian_api_key", "test-key")
    audio_id = _store_audio(tmp_path)
    respx.post(settings.bailian_asr_url).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "我在杭州东站。"}}]},
        )
    )

    response = client.post("/asr", json={"audio_id": audio_id})
    assert response.status_code == 200
    assert response.json()["data"]["text"] == "我在杭州东站。"
    assert "test-key" not in response.text


@respx.mock
def test_asr_empty_text_returns_422(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)
    monkeypatch.setattr(settings, "bailian_api_key", "test-key")
    audio_id = _store_audio(tmp_path)
    respx.post(settings.bailian_asr_url).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "   "}}]},
        )
    )

    response = client.post("/asr", json={"audio_id": audio_id})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ASR_EMPTY_TEXT"


@respx.mock
def test_asr_upstream_error_returns_502(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)
    monkeypatch.setattr(settings, "bailian_api_key", "test-key")
    audio_id = _store_audio(tmp_path)
    respx.post(settings.bailian_asr_url).mock(return_value=httpx.Response(500, json={}))

    response = client.post("/asr", json={"audio_id": audio_id})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ASR_UPSTREAM_ERROR"


@respx.mock
def test_asr_timeout_returns_504(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)
    monkeypatch.setattr(settings, "bailian_api_key", "test-key")
    audio_id = _store_audio(tmp_path)
    respx.post(settings.bailian_asr_url).mock(side_effect=httpx.ReadTimeout("slow"))

    response = client.post("/asr", json={"audio_id": audio_id})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "ASR_TIMEOUT"


def test_asr_missing_key_returns_502(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)
    monkeypatch.setattr(settings, "bailian_api_key", "")
    audio_id = _store_audio(tmp_path)

    response = client.post("/asr", json={"audio_id": audio_id})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ASR_UPSTREAM_ERROR"
