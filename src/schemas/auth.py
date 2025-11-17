"""
Authentication related Pydantic schemas.
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Schema for logout request."""
    refresh_token: str = Field(..., description="Refresh token to revoke")


class TokenPayload(BaseModel):
    """Schema for token payload (internal use)."""
    sub: str  # username
    user_id: int
    role: str
    exp: int
    iat: int
    type: str
