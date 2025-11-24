"""Authentication and identity response schemas."""
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
	"""Request body for login via JSON."""
	username: str
	password: str


class TokenResponse(BaseModel):
	"""Response with access/refresh tokens only (refresh endpoint)."""
	access_token: str
	refresh_token: str
	token_type: str = Field(default="bearer")


class RefreshTokenRequest(BaseModel):
	"""Request body for refreshing tokens."""
	refresh_token: str


class LogoutRequest(BaseModel):
	"""Request body for logout (revoke refresh token)."""
	refresh_token: str


class LoginUserDetails(BaseModel):
	"""User information returned on successful user login."""
	user_id: int
	name: str
	username: str
	role: str


class LoginCoachDetails(BaseModel):
	"""Coach information returned on successful coach login."""
	coach_id: int
	name: str
	username: str


class LoginResponseBase(BaseModel):
	"""Shared token information returned on login."""
	access_token: str
	refresh_token: str
	token_type: Literal["bearer"] = Field(default="bearer")


class LoginUserResponse(LoginResponseBase):
	"""Login response for user principals."""
	user_type: Literal["user"] = Field(default="user")
	user: LoginUserDetails


class LoginCoachResponse(LoginResponseBase):
	"""Login response for coach principals."""
	user_type: Literal["coach"] = Field(default="coach")
	coach: LoginCoachDetails


LoginResponse = Annotated[LoginUserResponse | LoginCoachResponse, Field(discriminator="user_type")]


class PermissionSummary(BaseModel):
	"""Permission detail with identifier and name."""
	permission_id: int
	permission_name: str


class UserProfileInfo(BaseModel):
	"""Detailed user profile information."""
	user_id: int
	name: str
	username: str
	role: str
	permissions: list[PermissionSummary]


class CoachSchoolSummary(BaseModel):
	"""Coach school assignment summary."""
	school_id: int
	school_name: str


class CoachBatchSummary(BaseModel):
	"""Coach batch assignment summary."""
	batch_id: int
	batch_name: str
	school_id: int
	school_name: str


class CoachProfileInfo(BaseModel):
	"""Detailed coach profile information."""
	coach_id: int
	name: str
	username: str
	schools: list[CoachSchoolSummary]
	batches: list[CoachBatchSummary]


class UserProfileResponse(BaseModel):
	"""Discriminated response for user principals."""
	user_type: Literal["user"] = Field(default="user")
	user: UserProfileInfo


class CoachProfileResponse(BaseModel):
	"""Discriminated response for coach principals."""
	user_type: Literal["coach"] = Field(default="coach")
	coach: CoachProfileInfo


UserMeResponse = Annotated[UserProfileResponse | CoachProfileResponse, Field(discriminator="user_type")]

