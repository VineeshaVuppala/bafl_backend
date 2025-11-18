"""
Database initialization utilities.
"""
from sqlalchemy.orm import Session

from src.db.database import SessionLocal, init_database
from src.db.models.user import User, UserRole
from src.db.models.permission import Permission, PermissionType
from src.db.models.role_permission import RolePermission
from src.db.repositories.user_repository import UserRepository
from src.db.repositories.permission_repository import PermissionRepository
from src.db.repositories.role_permission_repository import RolePermissionRepository
from src.core.security import PasswordHandler
from src.core.logging import db_logger, api_logger
from src.core.config import settings


# Default role-permission mappings for initial setup
DEFAULT_ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        # Can manage all users
        PermissionType.CREATE_USER,
        PermissionType.CREATE_COACH,
        PermissionType.CREATE_ADMIN,
        PermissionType.DELETE_USER,
        PermissionType.DELETE_COACH,
        PermissionType.DELETE_ADMIN,
        PermissionType.VIEW_ALL_USERS,
        PermissionType.EDIT_ALL_USERS,
        # Can manage permissions
        PermissionType.ASSIGN_PERMISSIONS,
        PermissionType.REVOKE_PERMISSIONS,
        PermissionType.VIEW_PERMISSIONS,
        # Can also view/edit own profile
        PermissionType.VIEW_OWN_PROFILE,
        PermissionType.EDIT_OWN_PROFILE,
    ],
    UserRole.USER: [
        # Can only manage own profile
        PermissionType.VIEW_OWN_PROFILE,
        PermissionType.EDIT_OWN_PROFILE,
    ],
    UserRole.COACH: [
        # Can only manage own profile
        PermissionType.VIEW_OWN_PROFILE,
        PermissionType.EDIT_OWN_PROFILE,
    ],
}


def create_initial_permissions(db: Session) -> None:
    """Create all system permissions in the database."""
    api_logger.info("Creating initial permissions...")
    
    for perm_type in PermissionType:
        existing = PermissionRepository.get_by_name(db, perm_type)
        if not existing:
            PermissionRepository.create(
                db,
                perm_type,
                f"Permission: {perm_type.value}"
            )
            api_logger.info(f"Created permission: {perm_type.value}")
    
    api_logger.info("Initial permissions created successfully")


def create_default_role_permissions(db: Session) -> None:
    """Create default role-permission mappings in database."""
    api_logger.info("Setting up default role permissions...")
    
    for role, permissions in DEFAULT_ROLE_PERMISSIONS.items():
        for perm_type in permissions:
            permission = PermissionRepository.get_by_name(db, perm_type)
            if permission:
                RolePermissionRepository.assign_permission_to_role(
                    db,
                    role,
                    permission.id
                )
    
    api_logger.info("Default role permissions configured")


def create_initial_admin(db: Session) -> None:
    """Create the initial admin user from environment variables."""
    api_logger.info("Checking for initial admin...")
    
    # Get credentials from environment
    username = settings.INITIAL_ADMIN_USERNAME
    name = settings.INITIAL_ADMIN_NAME
    password = settings.INITIAL_ADMIN_PASSWORD
    
    # Check if admin exists
    existing = UserRepository.get_by_username(db, username)
    
    if existing:
        api_logger.info(f"Initial admin '{username}' already exists")
        return
    
    # Create admin
    user_data = {
        "name": name,
        "username": username,
        "hashed_password": PasswordHandler.hash(password),
        "role": UserRole.ADMIN,
        "is_active": True
    }
    
    admin = UserRepository.create(db, user_data)
    api_logger.info(f"Initial admin created: {admin.username} (ID: {admin.id})")


def setup_database() -> None:
    """Initialize database with tables and seed data."""
    api_logger.info("Setting up database...")
    
    try:
        # Create tables
        init_database()
        
        # Create session for seeding
        db = SessionLocal()
        
        try:
            # Create permissions first
            create_initial_permissions(db)
            
            # Create default role-permission mappings
            create_default_role_permissions(db)
            
            # Create initial admin
            create_initial_admin(db)
            
            api_logger.info("Database setup completed successfully")
            
        except Exception as e:
            db_logger.error(f"Error during database seeding: {str(e)}")
            db.rollback()
            raise
        
        finally:
            db.close()
    
    except Exception as e:
        db_logger.error(f"Error during database setup: {str(e)}")
        raise
