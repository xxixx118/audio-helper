import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.health import router as health_router
from config import settings

app = FastAPI(title="语音约碰面地点", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    return response


app.include_router(health_router)
