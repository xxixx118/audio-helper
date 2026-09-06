import base64
import logging
from time import perf_counter

import httpx

from config import settings
from errors import AppError

logger = logging.getLogger(__name__)

ASR_STAGE = "asr"


def _raise_upstream(message: str = "语音识别服务异常，请稍后重试。") -> None:
    raise AppError(502, "ASR_UPSTREAM_ERROR", message, ASR_STAGE)


def _extract_text(payload: object) -> str:
    if not isinstance(payload, dict):
        _raise_upstream()
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        _raise_upstream()
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        _raise_upstream()
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "".join(parts).strip()
    _raise_upstream()
    return ""


def recognize_audio(content: bytes, mime_type: str) -> str:
    if not settings.bailian_api_key:
        _raise_upstream("语音识别服务未配置密钥，请在后端 .env 填写 BAILIAN_API_KEY。")

    encoded = base64.b64encode(content).decode("ascii")
    if len(encoded) > settings.max_asr_base64_bytes:
        raise AppError(
            413,
            "FILE_TOO_LARGE",
            "编码后的录音超过识别服务限制，请缩短录音后重试。",
            ASR_STAGE,
        )

    data_uri = f"data:{mime_type or 'audio/webm'};base64,{encoded}"
    payload = {
        "model": settings.bailian_asr_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": data_uri},
                    }
                ],
            }
        ],
        "asr_options": {"language": "zh"},
    }
    headers = {
        "Authorization": f"Bearer {settings.bailian_api_key}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(
        settings.asr_timeout_seconds,
        connect=settings.asr_connect_timeout_seconds,
    )

    started = perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                settings.bailian_asr_url,
                headers=headers,
                json=payload,
            )
    except httpx.TimeoutException as exc:
        logger.warning(
            "asr timeout elapsed_ms=%s",
            int((perf_counter() - started) * 1000),
        )
        raise AppError(504, "ASR_TIMEOUT", "语音识别超时，请稍后重试。", ASR_STAGE) from exc
    except httpx.HTTPError as exc:
        logger.warning("asr upstream connection error")
        raise AppError(
            502,
            "ASR_UPSTREAM_ERROR",
            "语音识别服务异常，请稍后重试。",
            ASR_STAGE,
        ) from exc

    elapsed_ms = int((perf_counter() - started) * 1000)
    logger.info("asr upstream status=%s elapsed_ms=%s", response.status_code, elapsed_ms)

    if response.status_code >= 400:
        _raise_upstream()

    try:
        body = response.json()
    except ValueError:
        _raise_upstream()

    text = _extract_text(body)
    if not text:
        raise AppError(422, "ASR_EMPTY_TEXT", "没有听清你的话，请重新说一次。", ASR_STAGE)
    return text
