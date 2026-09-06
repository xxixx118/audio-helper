from fastapi import APIRouter, Request

from schemas import AsrData, AsrRequest, AsrResponse
from services.asr import recognize_audio
from services.audio_storage import load_audio_record

router = APIRouter()


@router.post(
    "/asr",
    response_model=AsrResponse,
    responses={
        404: {"description": "录音不存在或已过期"},
        413: {"description": "编码后体积超限"},
        422: {"description": "请求不完整或识别为空"},
        502: {"description": "识别服务异常"},
        504: {"description": "识别超时"},
    },
)
def create_asr(request: Request, body: AsrRequest) -> AsrResponse:
    record = load_audio_record(body.audio_id, stage="asr")
    text = recognize_audio(record["content"], record["mime_type"])
    return AsrResponse(
        request_id=request.state.request_id,
        data=AsrData(text=text),
    )
