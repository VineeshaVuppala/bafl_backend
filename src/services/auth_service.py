"""Authentication service containing business logic for auth operations."""
from datetime import datetime
from typing import Literal, Optional, Tuple, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.db.models.coach import Coach
from src.db.models.user import User
from src.db.repositories.coach_repository import CoachRepository
from src.db.repositories.permission_repository import RefreshTokenRepository
from src.db.repositories.user_repository import UserRepository
from src.core.security import PasswordHandler, TokenHandler
from src.core.logging import log_auth_event


class AuthService:
    """Service for authentication operations."""
    
    IdentityType = Literal["user", "coach"]
    Identity = Union[User, Coach]

    @staticmethod
    def authenticate_user(
        db: Session,
        username: str,
        password: str,
    ) -> Optional[Tuple[IdentityType, Identity]]:
        """Authenticate a username/password pair for either a user or a coach."""

        # Attempt user authentication first
        user = UserRepository.get_by_username(db, username)
        
        if user:
            if not PasswordHandler.verify(password, user.hashed_password):
                log_auth_event("login_attempt", username, success=False, details="Invalid password")
                return None
            if not user.is_active:
                log_auth_event("login_attempt", username, success=False, details="User inactive")
                return None
            log_auth_event("login_success", username, success=True)
            return ("user", user)

        log_auth_event(
            "login_attempt",
            username,
            success=False,
            details="User not found; checking coach store",
        )
        
        # Attempt coach authentication if user auth failed
        coach = CoachRepository.get_by_username(db, username)
        if not coach:
            log_auth_event("login_attempt", username, success=False, details="Coach not found")
            return None
        
        if not PasswordHandler.verify(password, coach.password):
            log_auth_event("login_attempt", username, success=False, details="Invalid password")
            return None
        if not coach.is_active:
            log_auth_event("login_attempt", username, success=False, details="Coach inactive")
            return None
        log_auth_event("login_success", username, success=True)
        return ("coach", coach)
    
    @staticmethod
    def _build_access_token_payload(
        principal_type: IdentityType,
        principal: Identity,
    ) -> dict:
        payload = {
            "sub": principal.username,
            "subject_type": principal_type,
        }

        if principal_type == "user" and isinstance(principal, User):
            payload.update({
                "user_id": principal.id,
                "role": principal.role.value,
            })
        elif principal_type == "coach" and isinstance(principal, Coach):
            payload.update({
                "coach_id": principal.id,
            })

        return payload

    @staticmethod
    def create_tokens(
        db: Session,
        principal_type: IdentityType,
        principal: Identity,
    ) -> tuple[str, str]:
        """Create access and refresh tokens for the authenticated principal."""

        access_token = TokenHandler.create_access_token(
            data=AuthService._build_access_token_payload(principal_type, principal)
        )

        if principal_type == "user" and isinstance(principal, User):
            refresh_token_obj = RefreshTokenRepository.create(db, user_id=principal.id)
        elif principal_type == "coach" and isinstance(principal, Coach):
            refresh_token_obj = RefreshTokenRepository.create(db, coach_id=principal.id)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to issue refresh token",
            )

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
        
        principal_type: AuthService.IdentityType
        principal: AuthService.Identity

        if token_obj.user_id is not None:
            user = UserRepository.get_by_id(db, token_obj.user_id)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                )
            principal_type = "user"
            principal = user
        elif token_obj.coach_id is not None:
            coach = CoachRepository.get_by_id(db, token_obj.coach_id)
            if not coach or not coach.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Coach not found or inactive",
                )
            principal_type = "coach"
            principal = coach
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token subject",
            )

        RefreshTokenRepository.revoke(db, refresh_token)
        
        new_access_token, new_refresh_token = AuthService.create_tokens(
            db,
            principal_type=principal_type,
            principal=principal,
        )
        
        log_auth_event("token_refresh", principal.username, success=True)
        
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
