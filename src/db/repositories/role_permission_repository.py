"""
Role permission repository for database operations.
"""
from typing import Optional
from sqlalchemy.orm import Session

from src.db.models.role_permission import RolePermission
from src.db.models.user import UserRole
from src.db.models.permission import Permission, PermissionType
from src.core.logging import db_logger


class RolePermissionRepository:
    """Repository for RolePermission model database operations."""
    
    @staticmethod
    def get_permissions_for_role(db: Session, role: UserRole) -> list[Permission]:
        """Get all default permissions for a role from database."""
        role_perms = db.query(RolePermission).filter(
            RolePermission.role == role
        ).all()
        
        return [rp.permission for rp in role_perms if rp.permission]
    
    @staticmethod
    def assign_permission_to_role(
        db: Session,
        role: UserRole,
        permission_id: int
    ) -> RolePermission:
        """Assign a default permission to a role."""
        # Check if already exists
        existing = db.query(RolePermission).filter(
            RolePermission.role == role,
            RolePermission.permission_id == permission_id
        ).first()
        
        if existing:
            return existing
        
        role_perm = RolePermission(
            role=role,
            permission_id=permission_id
        )
        db.add(role_perm)
        db.commit()
        db.refresh(role_perm)
        db_logger.info(f"Permission {permission_id} assigned to role {role.value}")
        return role_perm
    
    @staticmethod
    def revoke_permission_from_role(
        db: Session,
        role: UserRole,
        permission_id: int
    ) -> bool:
        """Revoke a default permission from a role."""
        role_perm = db.query(RolePermission).filter(
            RolePermission.role == role,
            RolePermission.permission_id == permission_id
        ).first()
        
        if role_perm:
            db.delete(role_perm)
            db.commit()
            db_logger.info(f"Permission {permission_id} revoked from role {role.value}")
            return True
        return False
    
    @staticmethod
    def clear_role_permissions(db: Session, role: UserRole) -> None:
        """Clear all permissions for a role."""
        db.query(RolePermission).filter(RolePermission.role == role).delete()
        db.commit()
        db_logger.info(f"All permissions cleared for role {role.value}")
