"""
Core configuration using Pydantic Settings.
Loads from environment variables.
"""

from typing import Literal
from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = Field(default="kie-ats", alias="APP_NAME")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", alias="APP_ENV"
    )
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )

    # API
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="ALLOWED_ORIGINS",
    )

    # Database
    database_url: PostgresDsn = Field(..., alias="DATABASE_URL")
    database_pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")

    # Redis
    redis_url: RedisDsn = Field(..., alias="REDIS_URL")

    # Celery
    celery_broker_url: RedisDsn = Field(..., alias="CELERY_BROKER_URL")
    celery_result_backend: RedisDsn = Field(..., alias="CELERY_RESULT_BACKEND")

    # S3
    aws_access_key_id: str = Field(..., alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(..., alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_s3_bucket: str = Field(..., alias="AWS_S3_BUCKET")

    # Google ADK / Gemini
    google_api_key: str = Field(..., alias="GOOGLE_API_KEY")
    google_project_id: str | None = Field(default=None, alias="GOOGLE_PROJECT_ID")

    # Auth
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Logging
    log_request_body: bool = Field(default=False, alias="LOG_REQUEST_BODY")
    log_response_body: bool = Field(default=False, alias="LOG_RESPONSE_BODY")
    log_max_body_size: int = Field(default=1024, alias="LOG_MAX_BODY_SIZE")
    json_logs: bool = Field(default=True, alias="JSON_LOGS")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_per_second: int = Field(default=10, alias="RATE_LIMIT_PER_SECOND")
    rate_limit_per_minute: int = Field(default=100, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, alias="RATE_LIMIT_PER_HOUR")

    # Email
    sendgrid_api_key: str | None = Field(default=None, alias="SENDGRID_API_KEY")
    from_email: str = Field(default="noreply@example.com", alias="FROM_EMAIL")

    # External APIs
    zoom_client_id: str | None = Field(default=None, alias="ZOOM_CLIENT_ID")
    zoom_client_secret: str | None = Field(default=None, alias="ZOOM_CLIENT_SECRET")


# Global settings instance
settings = Settings()
