from fastapi import APIRouter, Request

from schemas import ExtractRequest, ExtractResponse
from services.extract import extract_meetup

router = APIRouter()


@router.post(
    "/extract",
    response_model=ExtractResponse,
    responses={
        422: {"description": "请求不完整或业务信息不完整"},
        502: {"description": "模型输出异常或上游错误"},
        504: {"description": "提取超时"},
    },
)
def create_extract(request: Request, body: ExtractRequest) -> ExtractResponse:
    data = extract_meetup(body.text, body.city)
    return ExtractResponse(request_id=request.state.request_id, data=data)
