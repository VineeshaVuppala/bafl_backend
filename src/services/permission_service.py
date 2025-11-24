"""Permission service containing business logic for permission operations."""
from dataclasses import dataclass
from typing import Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.db.models.permission import Permission, PermissionType
from src.db.models.user import User, UserRole
from src.db.repositories.permission_repository import (
    PermissionRepository,
    UserPermissionRepository
)
from src.core.logging import api_logger


class PermissionService:
    """Service for permission management operations."""

    class DynamicPermission(str):
        """Wrapper providing `.value` attribute for plain string permissions."""

        @property
        def value(self) -> str:  # pragma: no cover - trivial accessor
            return str(self)

    ROLE_BASE_PERMISSIONS = {
        UserRole.ADMIN: (
            PermissionType.CREATE_USER,
            PermissionType.CREATE_COACH,
            PermissionType.CREATE_ADMIN,
            PermissionType.DELETE_USER,
            PermissionType.DELETE_COACH,
            PermissionType.DELETE_ADMIN,
            PermissionType.VIEW_ALL_USERS,
            PermissionType.EDIT_ALL_USERS,
            PermissionType.ASSIGN_PERMISSIONS,
            PermissionType.REVOKE_PERMISSIONS,
            PermissionType.VIEW_PERMISSIONS,
            PermissionType.VIEW_OWN_PROFILE,
            PermissionType.EDIT_OWN_PROFILE,
            PermissionType.PHYSICAL_SESSIONS_VIEW,
            PermissionType.PHYSICAL_SESSIONS_EDIT,
            PermissionType.PHYSICAL_SESSIONS_ADD,
        ),
        UserRole.USER: (
            PermissionType.VIEW_OWN_PROFILE,
            PermissionType.EDIT_OWN_PROFILE,
            PermissionType.PHYSICAL_SESSIONS_VIEW,
            PermissionType.PHYSICAL_SESSIONS_EDIT,
            PermissionType.PHYSICAL_SESSIONS_ADD,
        ),
        UserRole.COACH: (
            PermissionType.VIEW_OWN_PROFILE,
            PermissionType.EDIT_OWN_PROFILE,
            PermissionType.PHYSICAL_SESSIONS_VIEW,
            PermissionType.PHYSICAL_SESSIONS_EDIT,
            PermissionType.PHYSICAL_SESSIONS_ADD,
        ),
    }

    @dataclass(frozen=True)
    class PermissionDetail:
        permission_id: int
        permission_name: str

    @staticmethod
    def _to_permission_token(name: str) -> Union[PermissionType, "PermissionService.DynamicPermission"]:
        try:
            return PermissionType(name)
        except ValueError:
            return PermissionService.DynamicPermission(name)
    
    @staticmethod
    def get_user_permissions(db: Session, user: User) -> list[Union[PermissionType, "PermissionService.DynamicPermission"]]:
        """
        Get all permissions for a user (role-based + custom).
        
        Args:
            db: Database session
            user: User instance
            
        Returns:
            List of permission types
        """
        base_permissions = PermissionService.ROLE_BASE_PERMISSIONS.get(user.role, tuple())
        permission_names = {perm.value for perm in base_permissions}

        for assignment in UserPermissionRepository.get_user_permissions(db, user.id):
            permission_names.add(assignment.permission.permission_name)

        normalized = [PermissionService._to_permission_token(name) for name in permission_names]
        return sorted(normalized, key=lambda perm: perm.value)

    @staticmethod
    def get_user_permission_details(
        db: Session,
        user: User,
    ) -> list["PermissionService.PermissionDetail"]:
        """Return both role-derived and custom permission details for a user."""

        collected: dict[str, PermissionService.PermissionDetail] = {}

        base_permissions = PermissionService.ROLE_BASE_PERMISSIONS.get(user.role, tuple())
        for perm in base_permissions:
            permission = PermissionRepository.get_or_create(
                db,
                perm,
                f"Permission: {perm.value}",
            )
            collected[permission.permission_name] = PermissionService.PermissionDetail(
                permission_id=permission.id,
                permission_name=permission.permission_name,
            )

        for assignment in UserPermissionRepository.get_user_permissions(db, user.id):
            permission = assignment.permission
            if permission is None:
                continue
            collected[permission.permission_name] = PermissionService.PermissionDetail(
                permission_id=permission.id,
                permission_name=permission.permission_name,
            )

        return sorted(collected.values(), key=lambda detail: detail.permission_name)
    
    @staticmethod
    def has_permission(db: Session, user: User, permission: PermissionType | str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            db: Database session
            user: User instance
            permission: Permission to check
            
        Returns:
            True if user has permission
        """
        target_name = permission.value if isinstance(permission, PermissionType) else str(permission)
        user_permissions = {perm.value for perm in PermissionService.get_user_permissions(db, user)}
        return target_name in user_permissions
    
    @staticmethod
    def can_create_role(db: Session, creator: User, target_role: UserRole) -> bool:
        """
        Check if user can create another user with specific role.
        
        Args:
            db: Database session
            creator: User attempting to create
            target_role: Role for new user
            
        Returns:
            True if allowed
        """
        required_permission = PermissionService.get_create_permission_for_role(target_role)
        if required_permission is None:
            return False
        return PermissionService.has_permission(db, creator, required_permission)

    @staticmethod
    def get_create_permission_for_role(target_role: UserRole) -> PermissionType | None:
        """Return the required create permission for the given role."""
        permission_map = {
            UserRole.USER: PermissionType.CREATE_USER,
            UserRole.COACH: PermissionType.CREATE_COACH,
            UserRole.ADMIN: PermissionType.CREATE_ADMIN,
        }
        return permission_map.get(target_role)

    @staticmethod
    def get_delete_permission_for_role(target_role: UserRole) -> PermissionType | None:
        """Return the required delete permission for the given role."""
        permission_map = {
            UserRole.USER: PermissionType.DELETE_USER,
            UserRole.COACH: PermissionType.DELETE_COACH,
            UserRole.ADMIN: PermissionType.DELETE_ADMIN,
        }
        return permission_map.get(target_role)

    @staticmethod
    def can_delete_user(db: Session, deleter: User, target_user: User) -> bool:
        """
        Check if the deleter can delete the target user based on permissions.
        """
        required_permission = PermissionService.get_delete_permission_for_role(target_user.role)
        if required_permission is None:
            return False
        return PermissionService.has_permission(db, deleter, required_permission)
    
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
    def get_permission_by_id(db: Session, permission_id: int) -> Permission:
        permission = PermissionRepository.get_by_id(db, permission_id)
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found",
            )
        return permission

    @staticmethod
    def assign_permission_by_id(
        db: Session,
        *,
        permission_id: int,
        assigner: User,
        user_id: int | None = None,
        coach_id: int | None = None,
    ) -> None:
        """Assign a permission by identifier to a user or coach."""
        
        if user_id == 0:
            user_id = None
        if coach_id == 0:
            coach_id = None

        if (user_id is None) == (coach_id is None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide exactly one of user_id or coach_id",
            )

        permission = PermissionService.get_permission_by_id(db, permission_id)

        if UserPermissionRepository.has_permission(
            db,
            permission_id,
            user_id=user_id,
            coach_id=coach_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission already assigned",
            )

        UserPermissionRepository.assign_permission(
            db,
            permission_id=permission.id,
            assigned_by=assigner.id,
            user_id=user_id,
            coach_id=coach_id,
        )

        target = user_id if user_id is not None else coach_id
        target_type = "user" if user_id is not None else "coach"
        api_logger.info(
            "Permission '%s' assigned to %s %s by '%s'",
            permission.permission_name,
            target_type,
            target,
            assigner.username,
        )

    @staticmethod
    def revoke_permission_by_id(
        db: Session,
        *,
        permission_id: int,
        revoker: User,
        user_id: int | None = None,
        coach_id: int | None = None,
    ) -> None:
        """Revoke a permission by identifier from a user or coach."""

        if user_id == 0:
            user_id = None
        if coach_id == 0:
            coach_id = None

        if (user_id is None) == (coach_id is None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide exactly one of user_id or coach_id",
            )

        permission = PermissionService.get_permission_by_id(db, permission_id)

        success = UserPermissionRepository.revoke_permission(
            db,
            permission_id=permission.id,
            user_id=user_id,
            coach_id=coach_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission not assigned to target",
            )

        target = user_id if user_id is not None else coach_id
        target_type = "user" if user_id is not None else "coach"
        api_logger.info(
            "Permission '%s' revoked from %s %s by '%s'",
            permission.permission_name,
            target_type,
            target,
            revoker.username,
        )
    
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
        if UserPermissionRepository.has_permission(db, permission.id, user_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission already assigned to user"
            )
        
        # Assign permission
        UserPermissionRepository.assign_permission(
            db,
            permission.id,
            assigner.id,
            user_id=user_id,
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
        
        success = UserPermissionRepository.revoke_permission(db, permission.id, user_id=user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission was not assigned to user"
            )
        
        api_logger.info(
            f"Permission '{permission_type.value}' revoked from user {user_id} "
            f"by '{revoker.username}'"
        )
