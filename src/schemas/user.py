"""
User related Pydantic schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from src.db.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema with common fields."""
    name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=6, max_length=100, description="User password")
    role: UserRole = Field(..., description="User role")


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    permissions: list[str] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Schema for list of users response."""
    users: list[UserResponse]
    total: int
