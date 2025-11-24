"""
Permission repository for database operations.
"""
from typing import Optional, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import secrets

from src.db.models.permission import Permission, UserPermission, PermissionType
from src.db.models.user import User, RefreshToken
from src.core.config import settings
from src.core.logging import db_logger


class PermissionRepository:
    """Repository for Permission model database operations."""
    
    @staticmethod
    def _normalize_name(name: Union[str, PermissionType]) -> str:
        return name.value if isinstance(name, PermissionType) else name

    @staticmethod
    def get_by_name(db: Session, name: Union[str, PermissionType]) -> Optional[Permission]:
        """Get permission by name."""
        normalized = PermissionRepository._normalize_name(name)
        return db.query(Permission).filter(Permission.permission_name == normalized).first()

    @staticmethod
    def get_by_id(db: Session, permission_id: int) -> Optional[Permission]:
        """Get permission by identifier."""
        return db.query(Permission).filter(Permission.id == permission_id).first()
    
    @staticmethod
    def get_all(db: Session) -> list[Permission]:
        """Get all permissions."""
        return db.query(Permission).all()
    
    @staticmethod
    def create(db: Session, name: Union[str, PermissionType], description: str | None = None) -> Permission:
        """Create a new permission."""
        normalized = PermissionRepository._normalize_name(name)
        permission = Permission(permission_name=normalized, description=description)
        db.add(permission)
        db.commit()
        db.refresh(permission)
        db_logger.info(f"Permission created: {normalized}")
        return permission
    
    @staticmethod
    def get_or_create(db: Session, name: Union[str, PermissionType], description: str | None = None) -> Permission:
        """Get permission or create if it doesn't exist."""
        permission = PermissionRepository.get_by_name(db, name)
        if not permission:
            permission = PermissionRepository.create(db, name, description)
        return permission


class UserPermissionRepository:
    """Repository for UserPermission model database operations."""
    
    @staticmethod
    def get_user_permissions(db: Session, user_id: int) -> list[UserPermission]:
        """Get all custom permissions for a user."""
        return db.query(UserPermission).filter(UserPermission.user_id == user_id).all()

    @staticmethod
    def get_coach_permissions(db: Session, coach_id: int) -> list[UserPermission]:
        """Get all custom permissions for a coach."""
        return db.query(UserPermission).filter(UserPermission.coach_id == coach_id).all()
    
    @staticmethod
    def has_permission(
        db: Session,
        permission_id: int,
        user_id: int | None = None,
        coach_id: int | None = None,
    ) -> bool:
        """Check if a user or coach has a specific permission."""
        query = db.query(UserPermission).filter(UserPermission.permission_id == permission_id)
        if user_id is not None:
            query = query.filter(UserPermission.user_id == user_id)
        if coach_id is not None:
            query = query.filter(UserPermission.coach_id == coach_id)
        return query.first() is not None
    
    @staticmethod
    def assign_permission(
        db: Session,
        permission_id: int,
        assigned_by: int | None,
        user_id: int | None = None,
        coach_id: int | None = None,
    ) -> UserPermission:
        """Assign permission to a user or coach."""

        if user_id is None and coach_id is None:
            raise ValueError("Either user_id or coach_id must be provided when assigning a permission")

        user_permission = UserPermission(
            user_id=user_id,
            coach_id=coach_id,
            permission_id=permission_id,
            assigned_by=assigned_by,
        )
        db.add(user_permission)
        db.commit()
        db.refresh(user_permission)

        target = user_id if user_id is not None else coach_id
        target_type = "user" if user_id is not None else "coach"
        db_logger.info(f"Permission {permission_id} assigned to {target_type} {target}")
        return user_permission
    
    @staticmethod
    def revoke_permission(
        db: Session,
        permission_id: int,
        user_id: int | None = None,
        coach_id: int | None = None,
    ) -> bool:
        """Revoke permission from a user or coach."""

        query = db.query(UserPermission).filter(UserPermission.permission_id == permission_id)
        if user_id is not None:
            query = query.filter(UserPermission.user_id == user_id)
        if coach_id is not None:
            query = query.filter(UserPermission.coach_id == coach_id)

        user_permission = query.first()

        if user_permission:
            db.delete(user_permission)
            db.commit()
            target = user_id if user_id is not None else coach_id
            target_type = "user" if user_id is not None else "coach"
            db_logger.info(f"Permission {permission_id} revoked from {target_type} {target}")
            return True
        return False


class RefreshTokenRepository:
    """Repository for RefreshToken model database operations."""
    
    @staticmethod
    def create(
        db: Session,
        *,
        user_id: int | None = None,
        coach_id: int | None = None,
    ) -> RefreshToken:
        """Create a new refresh token for a user or coach."""

        if (user_id is None and coach_id is None) or (user_id is not None and coach_id is not None):
            raise ValueError("Provide exactly one of user_id or coach_id when creating a refresh token")

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        refresh_token = RefreshToken(
            token=token,
            user_id=user_id,
            coach_id=coach_id,
            expires_at=expires_at
        )
        db.add(refresh_token)
        db.commit()
        db.refresh(refresh_token)
        return refresh_token
    
    @staticmethod
    def get_by_token(db: Session, token: str) -> Optional[RefreshToken]:
        """Get refresh token by token string."""
        return db.query(RefreshToken).filter(RefreshToken.token == token).first()
    
    @staticmethod
    def revoke(db: Session, token: str) -> bool:
        """Revoke a refresh token."""
        refresh_token = RefreshTokenRepository.get_by_token(db, token)
        if refresh_token:
            refresh_token.is_revoked = True
            db.commit()
            return True
        return False
    
    @staticmethod
    def revoke_all_user_tokens(db: Session, user_id: int) -> None:
        """Revoke all refresh tokens for a user."""
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id
        ).update({"is_revoked": True})
        db.commit()

    @staticmethod
    def revoke_all_coach_tokens(db: Session, coach_id: int) -> None:
        """Revoke all refresh tokens for a coach."""
        db.query(RefreshToken).filter(
            RefreshToken.coach_id == coach_id
        ).update({"is_revoked": True})
        db.commit()
