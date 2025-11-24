"""Permission related Pydantic schemas."""
from pydantic import BaseModel, Field, model_validator


class PermissionSummary(BaseModel):
    """Permission item returned in list responses."""

    permission_id: int
    permission_name: str


class PermissionListResponse(BaseModel):
    """Contract response for listing permissions."""

    permissions: list[PermissionSummary]


class AssignPermissionRequest(BaseModel):
    """Contract request for assigning a permission."""

    permission_id: int
    user_id: int | None = Field(default=None, description="Target user identifier")
    coach_id: int | None = Field(default=None, description="Target coach identifier")
    assigned_by: int | None = Field(default=None, description="Submitting admin identifier")

    @model_validator(mode="after")
    def validate_target(cls, values: "AssignPermissionRequest") -> "AssignPermissionRequest":
        if (values.user_id is None) == (values.coach_id is None):
            raise ValueError("Provide exactly one of user_id or coach_id")
        return values


class RevokePermissionRequest(BaseModel):
    """Contract request for revoking a permission."""

    permission_id: int
    user_id: int | None = None
    coach_id: int | None = None

    @model_validator(mode="after")
    def validate_target(cls, values: "RevokePermissionRequest") -> "RevokePermissionRequest":
        if (values.user_id is None) == (values.coach_id is None):
            raise ValueError("Provide exactly one of user_id or coach_id")
        return values
