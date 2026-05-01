"""
Application configuration using Pydantic Settings.
All values are read from environment variables / .env file.
"""
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "production"] = "development"
    app_secret_key: str = "change-me-32-chars-minimum"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    # Database
    database_url: str = "postgresql+asyncpg://callflow:callflow_secret@db:5432/callflow"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # LLM
    default_llm_provider: Literal["openai", "deepseek"] = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # Retell AI
    retell_api_key: str = ""
    retell_agent_id: str = ""
    retell_webhook_secret: str = ""
    retell_from_number: str = ""

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    twilio_sms_webhook_url: str = ""

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8001
    chroma_collection: str = "event_knowledge"

    # JWT
    jwt_secret_key: str = "change-me-jwt-secret-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # Compliance
    call_window_start: int = 9
    call_window_end: int = 21
    default_timezone: str = "Asia/Kolkata"

    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # Monitoring
    sentry_dsn: str = ""
    log_level: str = "INFO"

    @field_validator("app_secret_key", "jwt_secret_key")
    @classmethod
    def _secret_min_length(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("Secret keys must be at least 16 characters")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
