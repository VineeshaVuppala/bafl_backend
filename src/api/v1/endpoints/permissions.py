"""Permission management endpoints for assigning and revoking permissions."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.v1.dependencies.auth import (
    get_current_user,
    require_assign_permissions,
    require_revoke_permissions,
    require_view_permissions,
)
from src.core.logging import api_logger
from src.db.database import get_db
from src.db.models.user import User, UserRole
from src.db.repositories.coach_repository import CoachRepository
from src.schemas.common import MessageResponse
from src.schemas.permission import (
    AssignPermissionRequest,
    PermissionListResponse,
    PermissionSummary,
    RevokePermissionRequest,
)
from src.services.permission_service import PermissionService
from src.services.user_service import UserService


router = APIRouter(prefix="/permissions", tags=["Permission Management"])


@router.get("/", response_model=PermissionListResponse, status_code=status.HTTP_200_OK)
def list_all_permissions(
    current_user: User = Depends(require_view_permissions),
    db: Session = Depends(get_db),
) -> PermissionListResponse:
    """Return all permissions available in the system."""

    api_logger.info("Permission list requested by %s", current_user.username)
    permissions = PermissionService.get_all_permissions(db)
    return PermissionListResponse(
        permissions=[
            PermissionSummary(permission_id=p.id, permission_name=p.permission_name)
            for p in permissions
        ]
    )


@router.post("/assign", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def assign_permission(
    payload: AssignPermissionRequest,
    current_user: User = Depends(require_assign_permissions),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Assign a permission to a user or coach."""

    if payload.user_id is not None:
        target_user = UserService.get_user_by_id(db, payload.user_id)
        if not PermissionService.can_manage_permissions(db, current_user, target_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage this user's permissions",
            )
        PermissionService.assign_permission_by_id(
            db,
            permission_id=payload.permission_id,
            assigner=current_user,
            user_id=payload.user_id,
        )
        target_label = f"user {payload.user_id}"
    else:
        coach = CoachRepository.get_by_id(db, payload.coach_id)
        if not coach:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach not found")
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can manage coach permissions",
            )
        PermissionService.assign_permission_by_id(
            db,
            permission_id=payload.permission_id,
            assigner=current_user,
            coach_id=payload.coach_id,
        )
        target_label = f"coach {payload.coach_id}"

    if payload.assigned_by and payload.assigned_by != current_user.id:
        api_logger.warning(
            "Ignoring mismatched assigned_by value %s provided by %s",
            payload.assigned_by,
            current_user.username,
        )

    return MessageResponse(message="Permission assigned.")


@router.delete("/revoke", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def revoke_permission(
    payload: RevokePermissionRequest,
    current_user: User = Depends(require_revoke_permissions),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Revoke a permission from a user or coach."""

    if payload.user_id is not None:
        target_user = UserService.get_user_by_id(db, payload.user_id)
        if not PermissionService.can_manage_permissions(db, current_user, target_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage this user's permissions",
            )
        PermissionService.revoke_permission_by_id(
            db,
            permission_id=payload.permission_id,
            revoker=current_user,
            user_id=payload.user_id,
        )
    else:
        coach = CoachRepository.get_by_id(db, payload.coach_id)
        if not coach:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach not found")
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can manage coach permissions",
            )
        PermissionService.revoke_permission_by_id(
            db,
            permission_id=payload.permission_id,
            revoker=current_user,
            coach_id=payload.coach_id,
        )

    return MessageResponse(message="Permission revoked.")
