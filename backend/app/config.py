from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "AutoApplyAI"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "change-me"
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: List[str] = ["http://localhost:5173"]

    # Database
    database_url: str = "postgresql+asyncpg://autoapplyai:autoapplyai_secret@db:5432/autoapplyai"
    database_url_sync: str = "postgresql://autoapplyai:autoapplyai_secret@db:5432/autoapplyai"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # JWT
    jwt_secret_key: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # AI
    openai_api_key: str = ""
    openai_model: str = "gpt-4"

    # Files
    upload_dir: str = "/app/uploads"
    max_resume_size_mb: int = 10

    # Rate Limiting
    rate_limit_per_minute: int = 300
    max_applications_per_day: int = 10000

    # Playwright
    playwright_headless: bool = True
    playwright_timeout: int = 30000

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Monitoring
    sentry_dsn: str = ""

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.strip("[]").split(",")]
        return v

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
