"""
Authentication endpoints for login, token refresh, and logout.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Body
from typing import Optional
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest, LogoutRequest
from src.schemas.common import MessageResponse
from src.services.auth_service import AuthService
from src.api.v1.dependencies.auth import get_current_user
from src.db.models.user import User
from src.core.logging import api_logger


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    json_body: Optional[LoginRequest] = Body(None),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user and return tokens.
    Supports both JSON and form-data.
    """

    # Priority: JSON body first
    if json_body:
        username = json_body.username
        password = json_body.password

    # If still missing → invalid request
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="username and password are required"
        )

    api_logger.info(f"Login attempt for username: {username}")

    user = AuthService.authenticate_user(db, username, password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, refresh_token = AuthService.create_tokens(db, user)

    api_logger.info(f"Login successful for user: {username}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    """
    api_logger.info("Token refresh request")
    
    try:
        access_token, refresh_token = AuthService.refresh_tokens(db, request.refresh_token)
        
        api_logger.info("Token refresh successful")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def logout(
    request: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Logout user by revoking refresh token.
    
    - **refresh_token**: Refresh token to revoke
    """
    api_logger.info(f"Logout request from user: {current_user.username}")
    
    success = AuthService.logout(db, request.refresh_token)
    
    if success:
        api_logger.info(f"User logged out: {current_user.username}")
        return MessageResponse(message="Successfully logged out", success=True)
    else:
        return MessageResponse(message="Token already revoked or invalid", success=True)
