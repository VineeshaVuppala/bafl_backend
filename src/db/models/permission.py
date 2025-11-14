"""
Permission related database models.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from src.db.database import Base


class PermissionType(str, enum.Enum):
    """Available permission types in the system."""
    
    # User management
    CREATE_USER = "create_user"
    CREATE_COACH = "create_coach"
    DELETE_USER = "delete_user"
    VIEW_ALL_USERS = "view_all_users"
    EDIT_ALL_USERS = "edit_all_users"
    VIEW_OWN_PROFILE = "view_own_profile"
    EDIT_OWN_PROFILE = "edit_own_profile"
    
    # Permission management
    ASSIGN_PERMISSIONS = "assign_permissions"
    REVOKE_PERMISSIONS = "revoke_permissions"
    VIEW_PERMISSIONS = "view_permissions"


class Permission(Base):
    """Permission model."""
    
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(SQLEnum(PermissionType), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user_permissions = relationship("UserPermission", back_populates="permission")
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name='{self.name.value}')>"


class UserPermission(Base):
    """User-Permission association table for custom permissions."""
    
    __tablename__ = "user_permissions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    granted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="permissions")
    permission = relationship("Permission", back_populates="user_permissions")
    granted_by = relationship("User", foreign_keys=[granted_by_user_id], post_update=True)
    
    def __repr__(self) -> str:
        return f"<UserPermission(user_id={self.user_id}, permission_id={self.permission_id})>"
