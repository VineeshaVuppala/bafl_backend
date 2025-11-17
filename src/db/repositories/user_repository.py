"""
User repository for database operations.
"""
from typing import Optional
from sqlalchemy.orm import Session

from src.db.models.user import User, UserRole
from src.core.logging import db_logger


class UserRepository:
    """Repository for User model database operations."""
    
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination."""
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def create(db: Session, user_data: dict) -> User:
        """
        Create a new user.
        
        Args:
            db: Database session
            user_data: Dictionary with user data
            
        Returns:
            Created user
        """
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        db_logger.info(f"User created: {user.username} (ID: {user.id})")
        return user
    
    @staticmethod
    def update(db: Session, user: User, update_data: dict) -> User:
        """
        Update user fields.
        
        Args:
            db: Database session
            user: User to update
            update_data: Dictionary with fields to update
            
        Returns:
            Updated user
        """
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
                db_logger.debug(f"Setting {key} to {value if key != 'hashed_password' else '***'}")
        
        db.add(user)  # Explicitly mark as modified
        db.commit()
        db.refresh(user)
        db_logger.info(f"User updated: {user.username} (ID: {user.id})")
        return user
    
    @staticmethod
    def delete(db: Session, user: User) -> None:
        """Delete user."""
        username = user.username
        user_id = user.id
        db.delete(user)
        db.commit()
        db_logger.info(f"User deleted: {username} (ID: {user_id})")
    
    @staticmethod
    def exists_by_username(db: Session, username: str) -> bool:
        """Check if username exists."""
        return db.query(User).filter(User.username == username).first() is not None
