"""
Authentication service containing business logic for auth operations.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.db.models.user import User
from src.db.repositories.user_repository import UserRepository
from src.db.repositories.permission_repository import RefreshTokenRepository
from src.core.security import PasswordHandler, TokenHandler
from src.core.logging import log_auth_event
from src.core.config import settings


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password.
        
        Args:
            db: Database session
            username: Username
            password: Plain text password
            
        Returns:
            User if authentication successful, None otherwise
        """
        user = UserRepository.get_by_username(db, username)
        
        if not user:
            log_auth_event("login_attempt", username, success=False, details="User not found")
            return None
        
        if not PasswordHandler.verify(password, user.hashed_password):
            log_auth_event("login_attempt", username, success=False, details="Invalid password")
            return None
        
        if not user.is_active:
            log_auth_event("login_attempt", username, success=False, details="User inactive")
            return None
        
        log_auth_event("login_success", username, success=True)
        return user
    
    @staticmethod
    def create_tokens(db: Session, user: User) -> tuple[str, str]:
        """
        Create access and refresh tokens for user.
        
        Args:
            db: Database session
            user: User instance
            
        Returns:
            Tuple of (access_token, refresh_token)
        """
        # Create access token
        access_token = TokenHandler.create_access_token(
            data={
                "sub": user.username,
                "user_id": user.id,
                "role": user.role.value
            }
        )
        
        # Create refresh token
        refresh_token_obj = RefreshTokenRepository.create(db, user.id)
        
        return access_token, refresh_token_obj.token
    
    @staticmethod
    def refresh_tokens(db: Session, refresh_token: str) -> tuple[str, str]:
        """
        Refresh access token using refresh token.
        
        Args:
            db: Database session
            refresh_token: Refresh token string
            
        Returns:
            Tuple of (new_access_token, new_refresh_token)
            
        Raises:
            HTTPException: If refresh token is invalid or expired
        """
        # Get refresh token from database
        token_obj = RefreshTokenRepository.get_by_token(db, refresh_token)
        
        if not token_obj or token_obj.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check expiration
        if token_obj.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        
        # Get user
        user = UserRepository.get_by_id(db, token_obj.user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Revoke old token
        RefreshTokenRepository.revoke(db, refresh_token)
        
        # Create new tokens
        new_access_token, new_refresh_token = AuthService.create_tokens(db, user)
        
        log_auth_event("token_refresh", user.username, success=True)
        
        return new_access_token, new_refresh_token
    
    @staticmethod
    def logout(db: Session, refresh_token: str) -> bool:
        """
        Logout user by revoking refresh token.
        
        Args:
            db: Database session
            refresh_token: Refresh token to revoke
            
        Returns:
            True if logout successful
        """
        return RefreshTokenRepository.revoke(db, refresh_token)
