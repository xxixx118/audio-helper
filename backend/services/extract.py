import json
import logging
from time import perf_counter

import httpx
from pydantic import ValidationError

from config import BACKEND_DIR, settings
from errors import AppError
from schemas import ExtractData, ExtractModelOutput

logger = logging.getLogger(__name__)

EXTRACT_STAGE = "extract"
PROMPT_PATH = BACKEND_DIR / "prompts" / "extract.txt"
VAGUE_ADDRESSES = {"我家", "家里", "家", "公司", "单位", "公司里"}
CATEGORY_ALIASES = {
    "喝咖啡": "咖啡店",
    "咖啡": "咖啡店",
    "咖啡馆": "咖啡店",
}
CITY_SUFFIXES = ("特别行政区", "自治区", "地区", "省", "市")


def _raise_model_invalid() -> None:
    raise AppError(
        502,
        "MODEL_OUTPUT_INVALID",
        "信息提取结果异常，请稍后重试。",
        EXTRACT_STAGE,
    )


def _raise_upstream(message: str = "信息提取服务异常，请稍后重试。") -> None:
    raise AppError(502, "EXTRACT_UPSTREAM_ERROR", message, EXTRACT_STAGE)


def load_extract_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def normalize_city(value: str | None) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    for suffix in CITY_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
            break
    return text or None


def normalize_category(value: str | None) -> str:
    text = _normalize_text(value)
    if text is None:
        return "咖啡店"
    return CATEGORY_ALIASES.get(text, text)


def _is_vague_address(value: str | None) -> bool:
    text = _normalize_text(value)
    return text in VAGUE_ADDRESSES if text else False


def parse_model_output(raw_content: str) -> ExtractModelOutput:
    text = (raw_content or "").strip()
    if not text:
        _raise_model_invalid()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        _raise_model_invalid()
    try:
        return ExtractModelOutput.model_validate(payload)
    except ValidationError:
        _raise_model_invalid()
        raise


def evaluate_extract(model: ExtractModelOutput) -> ExtractData:
    if model.party_count != 2:
        raise AppError(
            422,
            "PARTY_COUNT_INVALID",
            "第一版只支持两个人约碰面，请重新说明两个人的位置。",
            EXTRACT_STAGE,
        )

    city_a = _normalize_text(model.city_a)
    city_b = _normalize_text(model.city_b)
    address_a = _normalize_text(model.address_a)
    address_b = _normalize_text(model.address_b)

    if (
        city_a is None
        or city_b is None
        or address_a is None
        or address_b is None
        or _is_vague_address(address_a)
        or _is_vague_address(address_b)
    ):
        raise AppError(
            422,
            "ADDRESS_INCOMPLETE",
            "地点说得不够清楚，请说出两个人的具体地点。",
            EXTRACT_STAGE,
        )

    if normalize_city(city_a) != normalize_city(city_b):
        raise AppError(
            422,
            "CROSS_CITY",
            "第一版只支持同一座城市内碰面，请重新表达。",
            EXTRACT_STAGE,
        )

    return ExtractData(
        city_a=city_a,
        address_a=address_a,
        city_b=city_b,
        address_b=address_b,
        category=normalize_category(model.category),
    )


def _extract_content(payload: object) -> tuple[str, str | None]:
    if not isinstance(payload, dict):
        _raise_model_invalid()
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        _raise_model_invalid()
    finish_reason = choices[0].get("finish_reason")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        _raise_model_invalid()
    content = message.get("content")
    if content is None:
        content = ""
    if not isinstance(content, str):
        _raise_model_invalid()
    return content, finish_reason if isinstance(finish_reason, str) else None


def extract_meetup(text: str, city: str) -> ExtractData:
    if not settings.deepseek_api_key:
        _raise_upstream("信息提取服务未配置密钥，请在后端 .env 填写 DEEPSEEK_API_KEY。")

    user_prompt = f"页面选定城市：{city}\n用户原话：{text}"
    request_body = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": load_extract_prompt()},
            {"role": "user", "content": user_prompt},
        ],
        "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "max_tokens": settings.extract_max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    timeout = httpx.Timeout(
        settings.extract_timeout_seconds,
        connect=settings.extract_connect_timeout_seconds,
    )

    started = perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, json=request_body)
    except httpx.TimeoutException as exc:
        logger.warning(
            "extract timeout elapsed_ms=%s",
            int((perf_counter() - started) * 1000),
        )
        raise AppError(
            504,
            "EXTRACT_TIMEOUT",
            "信息提取超时，请稍后重试。",
            EXTRACT_STAGE,
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("extract upstream connection error")
        raise AppError(
            502,
            "EXTRACT_UPSTREAM_ERROR",
            "信息提取服务异常，请稍后重试。",
            EXTRACT_STAGE,
        ) from exc

    logger.info(
        "extract upstream status=%s elapsed_ms=%s",
        response.status_code,
        int((perf_counter() - started) * 1000),
    )
    if response.status_code >= 400:
        _raise_upstream()

    try:
        payload = response.json()
    except ValueError:
        _raise_model_invalid()

    raw_content, finish_reason = _extract_content(payload)
    if finish_reason == "length" or not raw_content.strip():
        _raise_model_invalid()

    model_output = parse_model_output(raw_content)
    return evaluate_extract(model_output)
