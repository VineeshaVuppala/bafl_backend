"""
Authentication-related Pydantic schemas.
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
	"""Request body for login via JSON."""
	username: str
	password: str


class TokenResponse(BaseModel):
	"""Response with access/refresh tokens."""
	access_token: str
	refresh_token: str
	token_type: str = Field(default="bearer")


class RefreshTokenRequest(BaseModel):
	"""Request body for refreshing tokens."""
	refresh_token: str


class LogoutRequest(BaseModel):
	"""Request body for logout (revoke refresh token)."""
	refresh_token: str

