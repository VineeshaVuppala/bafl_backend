"""
Application configuration settings.
Loads environment variables and provides typed configuration.
"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import json


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = Field(default="BAFL Backend API")
    APP_VERSION: str = Field(default="1.0.0")
    DEBUG: bool = Field(default=True)
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(default="development")
    
    # Server
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=4256)
    
    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production-minimum-32-characters-long"
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./bafl_database.db")
    
    # CORS
    CORS_ORIGINS: list[str] | str = Field(default=["*"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: list[str] | str = Field(default=["*"])
    CORS_ALLOW_HEADERS: list[str] | str = Field(default=["*"])
    
    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    
    # Initial Admin (for first-time setup)
    INITIAL_ADMIN_NAME: str = Field(...)
    INITIAL_ADMIN_USERNAME: str = Field(...)
    INITIAL_ADMIN_PASSWORD: str = Field(...)
    
    @field_validator('CORS_ORIGINS', 'CORS_ALLOW_METHODS', 'CORS_ALLOW_HEADERS', mode='before')
    @classmethod
    def parse_cors_list(cls, v):
        """Parse CORS list from string if needed."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
