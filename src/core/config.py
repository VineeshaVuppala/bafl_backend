"""
Application configuration settings.
Loads environment variables and provides typed configuration.
"""
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import json

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    # Application
    APP_NAME: str = Field(...)
    APP_VERSION: str = Field(...)
    DEBUG: bool = Field(...)
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(...)

    # Server
    HOST: str = Field(...)
    PORT: int = Field(...)

    # Security
    SECRET_KEY: str = Field(...)
    ALGORITHM: str = Field(...)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(...)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(...)

    # Database
    DATABASE_URL: str = Field(...)

    # CORS
    CORS_ORIGINS: list[str] | str = Field(...)
    CORS_ALLOW_CREDENTIALS: bool = Field(...)
    CORS_ALLOW_METHODS: list[str] | str = Field(...)
    CORS_ALLOW_HEADERS: list[str] | str = Field(...)

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(...)
    LOG_FORMAT: str = Field(...)

    # Initial Admin
    INITIAL_ADMIN_NAME: str = Field(...)
    INITIAL_ADMIN_USERNAME: str = Field(...)
    INITIAL_ADMIN_PASSWORD: str = Field(...)

    @field_validator('CORS_ORIGINS', 'CORS_ALLOW_METHODS', 'CORS_ALLOW_HEADERS', mode='before')
    @classmethod
    def parse_cors_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return [v]
        return v

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
