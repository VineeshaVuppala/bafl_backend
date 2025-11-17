"""
Permission repository for database operations.
"""
from typing import Optional
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
    def get_by_name(db: Session, name: PermissionType) -> Optional[Permission]:
        """Get permission by name."""
        return db.query(Permission).filter(Permission.name == name).first()
    
    @staticmethod
    def get_all(db: Session) -> list[Permission]:
        """Get all permissions."""
        return db.query(Permission).all()
    
    @staticmethod
    def create(db: Session, name: PermissionType, description: str = None) -> Permission:
        """Create a new permission."""
        permission = Permission(name=name, description=description)
        db.add(permission)
        db.commit()
        db.refresh(permission)
        db_logger.info(f"Permission created: {name.value}")
        return permission
    
    @staticmethod
    def get_or_create(db: Session, name: PermissionType, description: str = None) -> Permission:
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
    def has_permission(db: Session, user_id: int, permission_id: int) -> bool:
        """Check if user has a specific permission."""
        return db.query(UserPermission).filter(
            UserPermission.user_id == user_id,
            UserPermission.permission_id == permission_id
        ).first() is not None
    
    @staticmethod
    def assign_permission(
        db: Session,
        user_id: int,
        permission_id: int,
        granted_by_user_id: int
    ) -> UserPermission:
        """Assign permission to user."""
        user_permission = UserPermission(
            user_id=user_id,
            permission_id=permission_id,
            granted_by_user_id=granted_by_user_id
        )
        db.add(user_permission)
        db.commit()
        db.refresh(user_permission)
        db_logger.info(f"Permission {permission_id} assigned to user {user_id}")
        return user_permission
    
    @staticmethod
    def revoke_permission(db: Session, user_id: int, permission_id: int) -> bool:
        """Revoke permission from user."""
        user_permission = db.query(UserPermission).filter(
            UserPermission.user_id == user_id,
            UserPermission.permission_id == permission_id
        ).first()
        
        if user_permission:
            db.delete(user_permission)
            db.commit()
            db_logger.info(f"Permission {permission_id} revoked from user {user_id}")
            return True
        return False


class RefreshTokenRepository:
    """Repository for RefreshToken model database operations."""
    
    @staticmethod
    def create(db: Session, user_id: int) -> RefreshToken:
        """Create a new refresh token."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        refresh_token = RefreshToken(
            token=token,
            user_id=user_id,
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
