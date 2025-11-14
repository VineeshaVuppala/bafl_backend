"""
User service containing business logic for user operations.
"""
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.db.models.user import User, UserRole
from src.db.repositories.user_repository import UserRepository
from src.core.security import PasswordHandler
from src.core.logging import api_logger


class UserService:
    """Service for user management operations."""
    
    @staticmethod
    def create_user(
        db: Session,
        name: str,
        username: str,
        password: str,
        role: UserRole,
        creator: User
    ) -> User:
        """
        Create a new user.
        
        Args:
            db: Database session
            name: User's full name
            username: Unique username
            password: Plain text password
            role: User role
            creator: User creating this user
            
        Returns:
            Created user
            
        Raises:
            HTTPException: If username exists or creator lacks permission
        """
        # Check if username exists
        if UserRepository.exists_by_username(db, username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{username}' already exists"
            )
        
        # Hash password
        hashed_password = PasswordHandler.hash(password)
        
        # Create user
        user_data = {
            "name": name,
            "username": username,
            "hashed_password": hashed_password,
            "role": role,
            "is_active": True
        }
        
        user = UserRepository.create(db, user_data)
        api_logger.info(f"User '{username}' created by '{creator.username}'")
        
        return user
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """
        Get user by ID.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            User instance
            
        Raises:
            HTTPException: If user not found
        """
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        return user
    
    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination."""
        return UserRepository.get_all(db, skip, limit)
    
    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        name: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> User:
        """
        Update user information.
        
        Args:
            db: Database session
            user_id: User ID
            name: New name (optional)
            is_active: New active status (optional)
            
        Returns:
            Updated user
            
        Raises:
            HTTPException: If user not found
        """
        user = UserService.get_user_by_id(db, user_id)
        
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if is_active is not None:
            update_data["is_active"] = is_active
        
        updated_user = UserRepository.update(db, user, update_data)
        api_logger.info(f"User '{user.username}' updated")
        
        return updated_user
    
    @staticmethod
    def delete_user(db: Session, user_id: int, deleter: User) -> None:
        """
        Delete a user.
        
        Args:
            db: Database session
            user_id: User ID to delete
            deleter: User performing the deletion
            
        Raises:
            HTTPException: If user not found or trying to delete self
        """
        if user_id == deleter.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        user = UserService.get_user_by_id(db, user_id)
        UserRepository.delete(db, user)
        api_logger.info(f"User '{user.username}' deleted by '{deleter.username}'")
