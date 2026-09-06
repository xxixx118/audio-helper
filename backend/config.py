from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    backend_host: str = "0.0.0.0"
    backend_port: int = 8003
    cors_allow_origins: list[str] = ["http://localhost:5175"]

    bailian_api_key: str = ""
    bailian_workspace_id: str = ""
    bailian_asr_model: str = "qwen3-asr-flash"
    bailian_asr_url: str = (
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    )
    bailian_tts_model: str = "qwen3-tts-flash"
    bailian_tts_url: str = (
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    )
    bailian_tts_voice: str = "Cherry"
    bailian_tts_language: str = "Chinese"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"

    amap_api_key: str = ""
    amap_geo_url: str = "https://restapi.amap.com/v3/geocode/geo"
    amap_around_url: str = "https://restapi.amap.com/v3/place/around"


settings = Settings()
