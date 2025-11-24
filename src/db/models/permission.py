"""Permission related database models."""
from datetime import datetime
import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from src.db.database import Base


class PermissionType(str, enum.Enum):
    """Baseline permission names used by legacy business logic."""

    CREATE_USER = "create_user"
    CREATE_COACH = "create_coach"
    CREATE_ADMIN = "create_admin"
    DELETE_USER = "delete_user"
    DELETE_COACH = "delete_coach"
    DELETE_ADMIN = "delete_admin"
    VIEW_ALL_USERS = "view_all_users"
    EDIT_ALL_USERS = "edit_all_users"
    VIEW_OWN_PROFILE = "view_own_profile"
    EDIT_OWN_PROFILE = "edit_own_profile"
    ASSIGN_PERMISSIONS = "assign_permissions"
    REVOKE_PERMISSIONS = "revoke_permissions"
    VIEW_PERMISSIONS = "view_permissions"
    PHYSICAL_SESSIONS_VIEW = "physical_sessions_view"
    PHYSICAL_SESSIONS_EDIT = "physical_sessions_edit"
    PHYSICAL_SESSIONS_ADD = "physical_sessions_add"


class Permission(Base):
    """Permission model."""

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    permission_name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    assignments = relationship("UserPermission", back_populates="permission", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, permission_name='{self.permission_name}')>"

    @property
    def user_permissions(self):
        return self.assignments


class UserPermission(Base):
    """Flexible permission assignment spanning users and coaches."""

    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id", ondelete="CASCADE"), nullable=True, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], back_populates="permissions")
    coach = relationship("Coach", foreign_keys=[coach_id], back_populates="permissions")
    permission = relationship("Permission", back_populates="assignments")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        UniqueConstraint("user_id", "permission_id", name="uq_user_permissions_user"),
        UniqueConstraint("coach_id", "permission_id", name="uq_user_permissions_coach"),
        CheckConstraint(
            "(user_id IS NOT NULL) OR (coach_id IS NOT NULL)",
            name="chk_user_permissions_target",
        ),
    )

    def __repr__(self) -> str:
        target = f"user_id={self.user_id}" if self.user_id is not None else f"coach_id={self.coach_id}"
        return f"<UserPermission({target}, permission_id={self.permission_id})>"
