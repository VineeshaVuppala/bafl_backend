"""Deprecated stub for role permissions repository."""
from sqlalchemy.orm import Session

from src.db.models.permission import PermissionType
from src.db.models.user import UserRole


class RolePermissionRepository:
    """Legacy compatibility shim; role permissions are now dynamic."""

    @staticmethod
    def get_permissions_for_role(db: Session, role: UserRole) -> list[PermissionType]:  # pragma: no cover - legacy path
        return []

    @staticmethod
    def assign_permission_to_role(db: Session, role: UserRole, permission_id: int) -> None:  # pragma: no cover - legacy path
        return None

    @staticmethod
    def revoke_permission_from_role(db: Session, role: UserRole, permission_id: int) -> bool:  # pragma: no cover - legacy path
        return False

    @staticmethod
    def clear_role_permissions(db: Session, role: UserRole) -> None:  # pragma: no cover - legacy path
        return None
