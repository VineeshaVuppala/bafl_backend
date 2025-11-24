"""Authentication dependencies for route protection."""
from dataclasses import dataclass
from typing import Callable, Literal, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from src.core.logging import auth_logger
from src.core.security import TokenHandler
from src.db.database import get_db
from src.db.models.coach import Coach
from src.db.models.permission import PermissionType
from src.db.models.user import User, UserRole
from src.db.repositories.coach_repository import CoachRepository
from src.db.repositories.user_repository import UserRepository
from src.services.permission_service import PermissionService


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass
class AuthenticatedIdentity:
    """Represents the authenticated principal resolved from an access token."""

    subject_type: Literal["user", "coach"]
    user: Optional[User] = None
    coach: Optional[Coach] = None


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_identity(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedIdentity:
    """Resolve the authenticated principal (user or coach) from the token."""

    credentials_exception = _credentials_exception()

    try:
        payload = TokenHandler.decode_token(token)
    except JWTError:
        raise credentials_exception

    subject_type = payload.get("subject_type")
    if subject_type not in {"user", "coach"}:
        raise credentials_exception

    if subject_type == "user":
        user_id = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        user = UserRepository.get_by_id(db, user_id)
        if user is None:
            auth_logger.warning("Token valid but user not found: %s", payload.get("sub"))
            raise credentials_exception
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user account",
            )
        return AuthenticatedIdentity(subject_type="user", user=user)

    coach_id = payload.get("coach_id")
    if coach_id is None:
        raise credentials_exception
    coach = CoachRepository.get_by_id(db, coach_id)
    if coach is None:
        auth_logger.warning("Token valid but coach not found: %s", payload.get("sub"))
        raise credentials_exception
    if not coach.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive coach account",
        )
    return AuthenticatedIdentity(subject_type="coach", coach=coach)


def get_current_user(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
) -> User:
    """Ensure the authenticated principal is a user."""

    if identity.user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User credentials required",
        )
    return identity.user


def require_role(*allowed_roles: UserRole) -> Callable:
    """Dependency factory to require specific user roles."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            auth_logger.warning(
                "Role check failed: %s has %s, required: %s",
                current_user.username,
                current_user.role.value,
                [r.value for r in allowed_roles],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges",
            )
        return current_user

    return role_checker


def require_permission(permission: PermissionType) -> Callable:
    """Dependency factory to require specific permission."""

    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not PermissionService.has_permission(db, current_user, permission):
            auth_logger.warning(
                "Permission denied: %s lacks %s",
                current_user.username,
                permission.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission.value}",
            )
        return current_user

    return permission_checker


require_view_all_users = require_permission(PermissionType.VIEW_ALL_USERS)
require_edit_all_users = require_permission(PermissionType.EDIT_ALL_USERS)
require_delete_user = require_permission(PermissionType.DELETE_USER)
require_assign_permissions = require_permission(PermissionType.ASSIGN_PERMISSIONS)
require_revoke_permissions = require_permission(PermissionType.REVOKE_PERMISSIONS)
require_view_permissions = require_permission(PermissionType.VIEW_PERMISSIONS)


def can_access_user(target_user_id: int, current_user: User, db: Session) -> bool:
    """Determine if the current user can access the target user's profile."""

    if PermissionService.has_permission(db, current_user, PermissionType.VIEW_ALL_USERS):
        return True

    if current_user.id == target_user_id:
        return PermissionService.has_permission(db, current_user, PermissionType.VIEW_OWN_PROFILE)

    return False


def can_edit_user(target_user_id: int, current_user: User, db: Session) -> bool:
    """Determine if the current user can modify the target user's profile."""

    if PermissionService.has_permission(db, current_user, PermissionType.EDIT_ALL_USERS):
        return True

    if current_user.id == target_user_id:
        return PermissionService.has_permission(db, current_user, PermissionType.EDIT_OWN_PROFILE)

    return False
