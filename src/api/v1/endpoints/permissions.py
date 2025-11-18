"""
Permission management endpoints for assigning and revoking permissions.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from json import JSONDecodeError
from starlette.datastructures import FormData
from pydantic import ValidationError
from fastapi.encoders import jsonable_encoder

from src.db.database import get_db
from src.db.models.user import User
from src.schemas.permission import (
    PermissionListResponse,
    PermissionResponse,
    UserPermissionsResponse,
    AssignPermissionRequest,
    RevokePermissionRequest
)
from src.schemas.common import MessageResponse
from src.services.user_service import UserService
from src.services.permission_service import PermissionService
from src.api.v1.dependencies.auth import (
    get_current_user,
    require_view_permissions,
    require_assign_permissions,
    require_revoke_permissions
)
from src.core.logging import api_logger


router = APIRouter(prefix="/permissions", tags=["Permission Management"])

SUPPORTED_CONTENT_TYPES_DETAIL = (
    "Supported content types are application/json, application/x-www-form-urlencoded, and multipart/form-data."
)


def _is_json_content_type(content_type: str | None) -> bool:
    """Return ``True`` when the provided content type represents JSON."""

    if not content_type:
        return True
    return "application/json" in content_type


def _is_form_content_type(content_type: str | None) -> bool:
    """Return ``True`` when the provided content type represents form data."""

    if not content_type:
        return False
    return any(
        candidate in content_type
        for candidate in ("application/x-www-form-urlencoded", "multipart/form-data")
    )


def _missing_field_errors(fields: list[str]) -> list[dict[str, object]]:
    """Produce FastAPI-compatible validation errors for missing form fields."""

    return [
        {"loc": ["body", field], "msg": "Field required", "type": "value_error.missing"}
        for field in fields
    ]


def _parse_permission_form(form: FormData, schema_cls):
    """Validate and normalise permission actions submitted via form payloads."""

    raw_data = {
        "user_id": form.get("user_id"),
        "permission": form.get("permission"),
    }

    missing = [field for field, value in raw_data.items() if value in (None, "")]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_missing_field_errors(missing),
        )

    raw_data["permission"] = str(raw_data["permission"]).lower()

    try:
        return schema_cls.model_validate(raw_data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(exc.errors()),
        ) from exc


async def _extract_permission_request(request: Request, schema_cls):
    """Read and validate permission action payload from JSON or form input."""

    content_type = request.headers.get("content-type")

    if _is_json_content_type(content_type):
        try:
            raw_data = await request.json()
        except JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON body.",
            ) from exc

        try:
            return schema_cls.model_validate(raw_data)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=jsonable_encoder(exc.errors()),
            ) from exc

    if _is_form_content_type(content_type):
        form = await request.form()
        return _parse_permission_form(form, schema_cls)

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=SUPPORTED_CONTENT_TYPES_DETAIL,
    )


@router.get("/", response_model=PermissionListResponse, status_code=status.HTTP_200_OK)
def list_all_permissions(
    current_user: User = Depends(require_view_permissions),
    db: Session = Depends(get_db)
) -> PermissionListResponse:
    """
    List all available permissions in the system. Requires VIEW_PERMISSIONS permission.
    """
    api_logger.info(f"All permissions list requested by {current_user.username}")
    
    permissions = PermissionService.get_all_permissions(db)
    
    permission_responses = [
        PermissionResponse(
            id=p.id,
            name=p.name,
            description=p.description
        )
        for p in permissions
    ]
    
    return PermissionListResponse(
        permissions=permission_responses,
        total=len(permission_responses)
    )


@router.get("/user/{user_id}", response_model=UserPermissionsResponse, status_code=status.HTTP_200_OK)
def get_user_permissions(
    user_id: int,
    current_user: User = Depends(require_view_permissions),
    db: Session = Depends(get_db)
) -> UserPermissionsResponse:
    """
    Get all permissions for a specific user. Requires VIEW_PERMISSIONS permission.
    
    - **user_id**: User ID
    """
    api_logger.info(f"Permissions for user {user_id} requested by {current_user.username}")
    
    user = UserService.get_user_by_id(db, user_id)
    permissions = PermissionService.get_user_permissions(db, user)
    
    return UserPermissionsResponse(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
        permissions=[p.value for p in permissions]
    )


@router.post("/assign", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def assign_permission(
    request: Request,
    current_user: User = Depends(require_assign_permissions),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Assign a permission to a user. Requires ASSIGN_PERMISSIONS permission.
    
    - **user_id**: Target user ID
    - **permission**: Permission to assign
    """
    payload = await _extract_permission_request(request, AssignPermissionRequest)

    api_logger.info(
        f"Permission assignment: {payload.permission.value} to user {payload.user_id} "
        f"by {current_user.username}"
    )
    
    # Get target user
    target_user = UserService.get_user_by_id(db, payload.user_id)
    
    # Check if current user can manage target user's permissions
    if not PermissionService.can_manage_permissions(db, current_user, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this user's permissions"
        )
    
    # Assign permission
    PermissionService.assign_permission(
        db,
        payload.user_id,
        payload.permission,
        current_user
    )
    
    return MessageResponse(
        message=f"Permission '{payload.permission.value}' assigned successfully",
        success=True
    )


@router.post("/revoke", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def revoke_permission(
    request: Request,
    current_user: User = Depends(require_revoke_permissions),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Revoke a permission from a user. Requires REVOKE_PERMISSIONS permission.
    
    - **user_id**: Target user ID
    - **permission**: Permission to revoke
    """
    payload = await _extract_permission_request(request, RevokePermissionRequest)

    api_logger.info(
        f"Permission revocation: {payload.permission.value} from user {payload.user_id} "
        f"by {current_user.username}"
    )
    
    # Get target user
    target_user = UserService.get_user_by_id(db, payload.user_id)
    
    # Check if current user can manage target user's permissions
    if not PermissionService.can_manage_permissions(db, current_user, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this user's permissions"
        )
    
    # Revoke permission
    PermissionService.revoke_permission(db, payload.user_id, payload.permission, current_user)
    
    return MessageResponse(
        message=f"Permission '{payload.permission.value}' revoked successfully",
        success=True
    )
