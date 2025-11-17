"""
User management endpoints for creating, viewing, updating, and deleting users.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models.user import User
from src.schemas.user import UserCreate, UserResponse, UserUpdate, UserListResponse
from src.schemas.common import MessageResponse
from src.services.user_service import UserService
from src.services.permission_service import PermissionService
from src.api.v1.dependencies.auth import (
    get_current_user,
    require_view_all_users,
    require_delete_user,
    can_access_user,
    can_edit_user
)
from src.core.logging import api_logger


router = APIRouter(prefix="/users", tags=["User Management"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Create a new user. Only ADMIN can create users.
    
    - **name**: User's full name
    - **username**: Unique username
    - **password**: User's password
    - **role**: User role (admin, user, or coach)
    """
    api_logger.info(
        f"User creation request by {current_user.username} for new user: {user_data.username}"
    )
    
    # Check if current user can create this role
    if not PermissionService.can_create_role(db, current_user, user_data.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to create users with role: {user_data.role.value}"
        )
    
    # Create user
    new_user = UserService.create_user(
        db=db,
        name=user_data.name,
        username=user_data.username,
        password=user_data.password,
        role=user_data.role,
        creator=current_user
    )
    
    # Get user permissions for response
    permissions = PermissionService.get_user_permissions(db, new_user)
    
    return UserResponse(
        id=new_user.id,
        name=new_user.name,
        username=new_user.username,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        permissions=[p.value for p in permissions]
    )


@router.get("/", response_model=UserListResponse, status_code=status.HTTP_200_OK)
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_view_all_users),
    db: Session = Depends(get_db)
) -> UserListResponse:
    """
    List all users. Requires VIEW_ALL_USERS permission (ADMIN only).
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    """
    api_logger.info(f"User list requested by {current_user.username}")
    
    users = UserService.get_all_users(db, skip, limit)
    
    user_responses = []
    for user in users:
        permissions = PermissionService.get_user_permissions(db, user)
        user_responses.append(
            UserResponse(
                id=user.id,
                name=user.name,
                username=user.username,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                permissions=[p.value for p in permissions]
            )
        )
    
    return UserListResponse(users=user_responses, total=len(user_responses))


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Get current authenticated user's information.
    """
    api_logger.info(f"User info requested by {current_user.username}")
    
    permissions = PermissionService.get_user_permissions(db, current_user)
    
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        permissions=[p.value for p in permissions]
    )


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Get a specific user by ID. 
    - ADMIN can view all users
    - Users/Coaches can only view their own profile
    
    - **user_id**: User ID
    """
    api_logger.info(f"User {user_id} info requested by {current_user.username}")
    
    # Check if user can access this profile
    if not can_access_user(user_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile"
        )
    
    user = UserService.get_user_by_id(db, user_id)
    permissions = PermissionService.get_user_permissions(db, user)
    
    return UserResponse(
        id=user.id,
        name=user.name,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        permissions=[p.value for p in permissions]
    )


@router.put("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Update a user.
    - ADMIN can edit all users
    - Users/Coaches can only edit their own profile
    
    - **user_id**: User ID
    - **name**: New name (optional)
    - **username**: New username (optional)
    - **password**: New password (optional)
    - **is_active**: New active status (optional, ADMIN only)
    """
    api_logger.info(f"User {user_id} update requested by {current_user.username}")
    
    # Check if user can edit this profile
    if not can_edit_user(user_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own profile"
        )
    
    updated_user = UserService.update_user(
        db=db,
        user_id=user_id,
        name=user_update.name,
        username=user_update.username,
        password=user_update.password,
        is_active=user_update.is_active
    )
    
    permissions = PermissionService.get_user_permissions(db, updated_user)
    
    return UserResponse(
        id=updated_user.id,
        name=updated_user.name,
        username=updated_user.username,
        role=updated_user.role,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at,
        permissions=[p.value for p in permissions]
    )


@router.delete("/{user_id}", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_delete_user),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Delete a user. Requires DELETE_USER permission.
    
    - **user_id**: User ID
    """
    api_logger.info(f"User {user_id} deletion requested by {current_user.username}")
    
    UserService.delete_user(db, user_id, current_user)
    
    return MessageResponse(message="User deleted successfully", success=True)
