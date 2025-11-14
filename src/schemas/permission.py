"""
Permission related Pydantic schemas.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from src.db.models.permission import PermissionType


class PermissionResponse(BaseModel):
    """Schema for permission response."""
    id: int
    name: PermissionType
    description: str | None = None
    
    model_config = ConfigDict(from_attributes=True)


class PermissionListResponse(BaseModel):
    """Schema for list of permissions."""
    permissions: list[PermissionResponse]
    total: int


class AssignPermissionRequest(BaseModel):
    """Schema for assigning permission to user."""
    user_id: int = Field(..., gt=0, description="User ID")
    permission: PermissionType = Field(..., description="Permission to assign")


class RevokePermissionRequest(BaseModel):
    """Schema for revoking permission from user."""
    user_id: int = Field(..., gt=0, description="User ID")
    permission: PermissionType = Field(..., description="Permission to revoke")


class UserPermissionsResponse(BaseModel):
    """Schema for user permissions response."""
    user_id: int
    username: str
    role: str
    permissions: list[str]
