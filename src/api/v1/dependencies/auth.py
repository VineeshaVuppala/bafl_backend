"""
Authentication dependencies for route protection.
"""
from typing import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models.user import User, UserRole
from src.db.models.permission import PermissionType
from src.db.repositories.user_repository import UserRepository
from src.core.security import TokenHandler
from src.services.permission_service import PermissionService
from src.core.logging import auth_logger


# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    
    Args:
        token: JWT token from Authorization header
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = TokenHandler.decode_token(token)
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    user = UserRepository.get_by_username(db, username)
    
    if user is None:
        auth_logger.warning(f"Token valid but user not found: {username}")
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    return user


def require_role(*allowed_roles: UserRole) -> Callable:
    """
    Dependency factory to require specific user roles.
    
    Args:
        *allowed_roles: Variable number of allowed roles
        
    Returns:
        Dependency function
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            auth_logger.warning(
                f"Role check failed: {current_user.username} has {current_user.role.value}, "
                f"required: {[r.value for r in allowed_roles]}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges"
            )
        return current_user
    
    return role_checker


def require_permission(permission: PermissionType) -> Callable:
    """
    Dependency factory to require specific permission.
    
    Args:
        permission: Required permission
        
    Returns:
        Dependency function
    """
    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        if not PermissionService.has_permission(db, current_user, permission):
            auth_logger.warning(
                f"Permission denied: {current_user.username} lacks {permission.value}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission.value}"
            )
        return current_user
    
    return permission_checker


# Common permission dependencies
require_view_all_users = require_permission(PermissionType.VIEW_ALL_USERS)
require_edit_all_users = require_permission(PermissionType.EDIT_ALL_USERS)
require_delete_user = require_permission(PermissionType.DELETE_USER)
require_assign_permissions = require_permission(PermissionType.ASSIGN_PERMISSIONS)
require_revoke_permissions = require_permission(PermissionType.REVOKE_PERMISSIONS)
require_view_permissions = require_permission(PermissionType.VIEW_PERMISSIONS)


def can_access_user(target_user_id: int, current_user: User, db: Session) -> bool:
    """
    Check if current user can access another user's information.
    - ADMIN can access all users
    - Users/Coaches can only access their own profile
    """
    # Admin can access everyone
    if PermissionService.has_permission(db, current_user, PermissionType.VIEW_ALL_USERS):
        return True
    
    # Users can only access their own profile
    if current_user.id == target_user_id:
        return PermissionService.has_permission(db, current_user, PermissionType.VIEW_OWN_PROFILE)
    
    return False


def can_edit_user(target_user_id: int, current_user: User, db: Session) -> bool:
    """
    Check if current user can edit another user's information.
    - ADMIN can edit all users
    - Users/Coaches can only edit their own profile
    """
    # Admin can edit everyone
    if PermissionService.has_permission(db, current_user, PermissionType.EDIT_ALL_USERS):
        return True
    
    # Users can only edit their own profile
    if current_user.id == target_user_id:
        return PermissionService.has_permission(db, current_user, PermissionType.EDIT_OWN_PROFILE)
    
    return False
