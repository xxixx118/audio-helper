from fastapi import APIRouter, File, Request, UploadFile

from config import settings
from errors import AppError
from schemas import UploadData, UploadResponse
from services.audio_probe import validate_uploaded_audio
from services.audio_storage import (
    audio_file_path,
    delete_audio,
    new_audio_id,
    save_audio_bytes,
    save_audio_metadata,
)

router = APIRouter()


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={
        413: {"description": "文件过大"},
        415: {"description": "格式不支持"},
        422: {"description": "缺少文件或时长不合规"},
    },
)
async def upload_audio(
    request: Request,
    file: UploadFile = File(...),
) -> UploadResponse:
    content = await file.read()
    if not content:
        raise AppError(
            422,
            "INVALID_REQUEST",
            "请先录一段语音再提交。",
            "upload",
        )
    if len(content) > settings.max_audio_bytes:
        raise AppError(
            413,
            "FILE_TOO_LARGE",
            "录音文件不能超过5MB，请缩短录音后重试。",
            "upload",
        )

    audio_id = new_audio_id()
    save_audio_bytes(audio_id, content)
    try:
        probe = validate_uploaded_audio(audio_file_path(audio_id))
        save_audio_metadata(
            audio_id,
            size=len(content),
            duration_seconds=probe.duration_seconds,
            mime_type="audio/webm",
            duration_source=probe.duration_source,
        )
    except Exception:
        delete_audio(audio_id)
        raise

    return UploadResponse(
        request_id=request.state.request_id,
        data=UploadData(audio_id=audio_id),
    )
