import httpx
import respx
from fastapi.testclient import TestClient

from config import settings
from main import app

client = TestClient(app)
EXTRACT_URL = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"


def _model_response(content: object, finish_reason: str = "stop") -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"finish_reason": finish_reason, "message": {"content": content}}]},
    )


def test_extract_missing_field_returns_422():
    response = client.post("/extract", json={"text": "我在杭州东站"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert body["error"]["stage"] == "extract"


@respx.mock
def test_extract_success_returns_five_fields(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    respx.post(EXTRACT_URL).mock(
        return_value=_model_response(
            '{"city_a":"杭州","address_a":"杭州东站","city_b":"杭州","address_b":"西湖龙翔桥地铁站","category":"咖啡店","party_count":2,"incomplete_reason":null}'
        )
    )
    response = client.post(
        "/extract",
        json={
            "text": "我在杭州东站，朋友在西湖龙翔桥地铁站，帮我们找个中间的咖啡店。",
            "city": "杭州",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"] == {
        "city_a": "杭州",
        "address_a": "杭州东站",
        "city_b": "杭州",
        "address_b": "西湖龙翔桥地铁站",
        "category": "咖啡店",
    }
    assert "party_count" not in response.json()["data"]
    assert "test-key" not in response.text


@respx.mock
def test_extract_missing_address_returns_422(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    respx.post(EXTRACT_URL).mock(
        return_value=_model_response(
            '{"city_a":"杭州","address_a":"杭州东站","city_b":null,"address_b":null,"category":"咖啡店","party_count":null,"incomplete_reason":"missing_address"}'
        )
    )
    response = client.post(
        "/extract",
        json={"text": "我在杭州东站，帮我找一家咖啡店。", "city": "杭州"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ADDRESS_INCOMPLETE"


@respx.mock
def test_extract_party_count_returns_422(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    respx.post(EXTRACT_URL).mock(
        return_value=_model_response(
            '{"city_a":"杭州","address_a":"杭州东站","city_b":"杭州","address_b":"龙翔桥","category":"咖啡店","party_count":3,"incomplete_reason":"party_count_mismatch"}'
        )
    )
    response = client.post(
        "/extract",
        json={
            "text": "我和两个朋友，一个在杭州东站，一个在龙翔桥，一个在河坊街。",
            "city": "杭州",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PARTY_COUNT_INVALID"


@respx.mock
def test_extract_cross_city_returns_422(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    respx.post(EXTRACT_URL).mock(
        return_value=_model_response(
            '{"city_a":"杭州","address_a":"杭州东站","city_b":"上海","address_b":"人民广场","category":"咖啡店","party_count":2,"incomplete_reason":"cross_city"}'
        )
    )
    response = client.post(
        "/extract",
        json={"text": "我在杭州东站，朋友在上海人民广场。", "city": "杭州"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CROSS_CITY"


@respx.mock
def test_extract_vague_home_returns_422(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    respx.post(EXTRACT_URL).mock(
        return_value=_model_response(
            '{"city_a":"杭州","address_a":null,"city_b":"杭州","address_b":null,"category":"咖啡店","party_count":2,"incomplete_reason":"address_too_vague"}'
        )
    )
    response = client.post(
        "/extract",
        json={"text": "我在我家，朋友在公司，找个地方喝咖啡。", "city": "杭州"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ADDRESS_INCOMPLETE"


@respx.mock
def test_extract_invalid_json_returns_502(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    respx.post(EXTRACT_URL).mock(return_value=_model_response("不是json"))
    response = client.post(
        "/extract",
        json={"text": "我在杭州东站，朋友在龙翔桥。", "city": "杭州"},
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "MODEL_OUTPUT_INVALID"
    assert "没说清楚" not in response.json()["error"]["message"]


@respx.mock
def test_extract_empty_content_returns_502(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    respx.post(EXTRACT_URL).mock(return_value=_model_response(""))
    response = client.post(
        "/extract",
        json={"text": "我在杭州东站，朋友在龙翔桥。", "city": "杭州"},
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "MODEL_OUTPUT_INVALID"


@respx.mock
def test_extract_timeout_returns_504(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    respx.post(EXTRACT_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    response = client.post(
        "/extract",
        json={"text": "我在杭州东站，朋友在龙翔桥。", "city": "杭州"},
    )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "EXTRACT_TIMEOUT"
