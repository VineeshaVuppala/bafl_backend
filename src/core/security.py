"""
Security utilities for password hashing and JWT token management.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings
from src.core.logging import auth_logger


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordHandler:
    """Handles password hashing and verification."""
    
    @staticmethod
    def hash(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database
            
        Returns:
            True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)


class TokenHandler:
    """Handles JWT token creation and verification."""
    
    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Data to encode in token
            expires_delta: Optional custom expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })
        
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
    
    @staticmethod
    def decode_token(token: str) -> dict:
        """
        Decode and verify a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            JWTError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError as e:
            auth_logger.error(f"Token verification failed: {str(e)}")
            raise
