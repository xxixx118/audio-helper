from pydantic import BaseModel, Field


class HealthData(BaseModel):
    status: str = Field(examples=["ok"])


class HealthResponse(BaseModel):
    request_id: str
    data: HealthData


class UploadData(BaseModel):
    audio_id: str


class UploadResponse(BaseModel):
    request_id: str
    data: UploadData


class AsrRequest(BaseModel):
    audio_id: str = Field(min_length=1, examples=["rec_7c3a2b91e4f04b1a9d0e2c18b4f6a011"])


class AsrData(BaseModel):
    text: str


class AsrResponse(BaseModel):
    request_id: str
    data: AsrData


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1, examples=["我在杭州东站，朋友在西湖龙翔桥地铁站，帮我们找个中间的咖啡店。"])
    city: str = Field(min_length=1, examples=["杭州"])


class ExtractModelOutput(BaseModel):
    city_a: str | None = None
    address_a: str | None = None
    city_b: str | None = None
    address_b: str | None = None
    category: str | None = None
    party_count: int | None = None
    incomplete_reason: str | None = None


class ExtractData(BaseModel):
    city_a: str
    address_a: str
    city_b: str
    address_b: str
    category: str


class ExtractResponse(BaseModel):
    request_id: str
    data: ExtractData


class ErrorDetail(BaseModel):
    code: str
    message: str
    stage: str


class ErrorResponse(BaseModel):
    request_id: str
    error: ErrorDetail
