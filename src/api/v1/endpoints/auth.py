"""
Authentication endpoints for login, token refresh, and logout.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Body, Request
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


def perform_login(username: str, password: str, db: Session) -> TokenResponse:
    """
    Core login logic - authenticates user and returns tokens.
    
    Args:
        username: User's username
        password: User's password
        db: Database session
        
    Returns:
        TokenResponse with access and refresh tokens
        
    Raises:
        HTTPException: If authentication fails
    """
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


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Login endpoint that accepts both form-data and JSON.
    Returns JSON response with access and refresh tokens.

    Provide either form fields `username` and `password`,
    or a JSON body: {"username": "...", "password": "..."}.
    """
    final_username: Optional[str] = None
    final_password: Optional[str] = None

    content_type = (request.headers.get("content-type") or "").lower()
    try:
        if "application/json" in content_type:
            body = await request.json()
            if isinstance(body, dict):
                final_username = body.get("username")
                final_password = body.get("password")
        else:
            form = await request.form()
            final_username = form.get("username")
            final_password = form.get("password")
    except Exception:
        # Fallback: attempt both if parsing fails due to incorrect content-type
        try:
            body = await request.json()
            if isinstance(body, dict):
                final_username = final_username or body.get("username")
                final_password = final_password or body.get("password")
        except Exception:
            try:
                form = await request.form()
                final_username = final_username or form.get("username")
                final_password = final_password or form.get("password")
            except Exception:
                pass

    if not final_username or not final_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username and password are required (via JSON or form).",
        )

    return perform_login(str(final_username), str(final_password), db)


@router.post("/login/json", response_model=TokenResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
def login_json(
    credentials: LoginRequest = Body(...),
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Login with JSON (hidden from documentation, for API testing).
    Accepts JSON only.
    Returns JSON response with access and refresh tokens.
    """
    return perform_login(credentials.username, credentials.password, db)


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
