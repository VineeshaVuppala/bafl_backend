"""
Permission service containing business logic for permission operations.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.db.models.user import User, UserRole
from src.db.models.permission import Permission, PermissionType
from src.db.repositories.permission_repository import (
    PermissionRepository,
    UserPermissionRepository
)
from src.db.repositories.role_permission_repository import RolePermissionRepository
from src.core.logging import api_logger


class PermissionService:
    """Service for permission management operations."""
    
    @staticmethod
    def get_user_permissions(db: Session, user: User) -> list[PermissionType]:
        """
        Get all permissions for a user (role-based + custom).
        
        Args:
            db: Database session
            user: User instance
            
        Returns:
            List of permission types
        """
        # Start with role-based permissions from database
        role_permissions = RolePermissionRepository.get_permissions_for_role(db, user.role)
        permissions = set(perm.name for perm in role_permissions)
        
        # Add custom user-specific permissions
        user_perms = UserPermissionRepository.get_user_permissions(db, user.id)
        for user_perm in user_perms:
            permissions.add(user_perm.permission.name)
        
        return list(permissions)
    
    @staticmethod
    def has_permission(db: Session, user: User, permission: PermissionType) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            db: Database session
            user: User instance
            permission: Permission to check
            
        Returns:
            True if user has permission
        """
        user_permissions = PermissionService.get_user_permissions(db, user)
        return permission in user_permissions
    
    @staticmethod
    def can_create_role(db: Session, creator: User, target_role: UserRole) -> bool:
        """
        Check if user can create another user with specific role.
        Only ADMIN can create users/coaches.
        
        Args:
            db: Database session
            creator: User attempting to create
            target_role: Role for new user
            
        Returns:
            True if allowed
        """
        # Only ADMIN can create users
        if creator.role != UserRole.ADMIN:
            return False
        
        # ADMIN can create USER or COACH
        if target_role in [UserRole.USER, UserRole.COACH]:
            perm_map = {
                UserRole.USER: PermissionType.CREATE_USER,
                UserRole.COACH: PermissionType.CREATE_COACH,
            }
            return PermissionService.has_permission(db, creator, perm_map[target_role])
        
        # ADMIN cannot create another ADMIN
        return False
    
    @staticmethod
    def can_manage_permissions(db: Session, manager: User, target_user: User) -> bool:
        """
        Check if user can manage another user's permissions.
        Only ADMIN can manage permissions.
        
        Args:
            db: Database session
            manager: User attempting to manage permissions
            target_user: User whose permissions are being managed
            
        Returns:
            True if allowed
        """
        # Cannot manage own permissions
        if manager.id == target_user.id:
            return False
        
        # Only ADMIN can manage permissions
        if manager.role != UserRole.ADMIN:
            return False
        
        # Must have permission
        if not PermissionService.has_permission(db, manager, PermissionType.ASSIGN_PERMISSIONS):
            return False
        
        return True
    
    @staticmethod
    def get_all_permissions(db: Session) -> list[Permission]:
        """Get all available permissions."""
        return PermissionRepository.get_all(db)
    
    @staticmethod
    def assign_permission(
        db: Session,
        user_id: int,
        permission_type: PermissionType,
        assigner: User
    ) -> None:
        """
        Assign permission to user.
        
        Args:
            db: Database session
            user_id: Target user ID
            permission_type: Permission to assign
            assigner: User assigning the permission
            
        Raises:
            HTTPException: If permission already assigned or not allowed
        """
        # Get or create permission
        permission = PermissionRepository.get_or_create(
            db,
            permission_type,
            f"Permission: {permission_type.value}"
        )
        
        # Check if already assigned
        if UserPermissionRepository.has_permission(db, user_id, permission.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission already assigned to user"
            )
        
        # Assign permission
        UserPermissionRepository.assign_permission(
            db,
            user_id,
            permission.id,
            assigner.id
        )
        
        api_logger.info(
            f"Permission '{permission_type.value}' assigned to user {user_id} "
            f"by '{assigner.username}'"
        )
    
    @staticmethod
    def revoke_permission(
        db: Session,
        user_id: int,
        permission_type: PermissionType,
        revoker: User
    ) -> None:
        """
        Revoke permission from user.
        
        Args:
            db: Database session
            user_id: Target user ID
            permission_type: Permission to revoke
            revoker: User revoking the permission
            
        Raises:
            HTTPException: If permission not found
        """
        permission = PermissionRepository.get_by_name(db, permission_type)
        
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found"
            )
        
        success = UserPermissionRepository.revoke_permission(db, user_id, permission.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission was not assigned to user"
            )
        
        api_logger.info(
            f"Permission '{permission_type.value}' revoked from user {user_id} "
            f"by '{revoker.username}'"
        )
