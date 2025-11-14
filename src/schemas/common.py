"""
Common/shared Pydantic schemas.
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """Generic message response schema."""
    message: str
    success: bool = True
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    detail: str
    success: bool = False
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    app_name: str
    version: str
    environment: str
