"""
Permission management endpoints for assigning and revoking permissions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
def assign_permission(
    request: AssignPermissionRequest,
    current_user: User = Depends(require_assign_permissions),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Assign a permission to a user. Requires ASSIGN_PERMISSIONS permission.
    
    - **user_id**: Target user ID
    - **permission**: Permission to assign
    """
    api_logger.info(
        f"Permission assignment: {request.permission.value} to user {request.user_id} "
        f"by {current_user.username}"
    )
    
    # Get target user
    target_user = UserService.get_user_by_id(db, request.user_id)
    
    # Check if current user can manage target user's permissions
    if not PermissionService.can_manage_permissions(db, current_user, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this user's permissions"
        )
    
    # Assign permission
    PermissionService.assign_permission(
        db,
        request.user_id,
        request.permission,
        current_user
    )
    
    return MessageResponse(
        message=f"Permission '{request.permission.value}' assigned successfully",
        success=True
    )


@router.post("/revoke", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def revoke_permission(
    request: RevokePermissionRequest,
    current_user: User = Depends(require_revoke_permissions),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Revoke a permission from a user. Requires REVOKE_PERMISSIONS permission.
    
    - **user_id**: Target user ID
    - **permission**: Permission to revoke
    """
    api_logger.info(
        f"Permission revocation: {request.permission.value} from user {request.user_id} "
        f"by {current_user.username}"
    )
    
    # Get target user
    target_user = UserService.get_user_by_id(db, request.user_id)
    
    # Check if current user can manage target user's permissions
    if not PermissionService.can_manage_permissions(db, current_user, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this user's permissions"
        )
    
    # Revoke permission
    PermissionService.revoke_permission(
        db,
        request.user_id,
        request.permission,
        current_user
    )
    
    return MessageResponse(
        message=f"Permission '{request.permission.value}' revoked successfully",
        success=True
    )
