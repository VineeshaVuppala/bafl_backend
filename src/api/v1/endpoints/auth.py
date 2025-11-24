"""Authentication endpoints for login, token refresh, and logout."""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.api.v1.dependencies.auth import AuthenticatedIdentity, get_current_identity
from src.core.logging import api_logger
from src.db.database import get_db
from src.db.models.coach import Coach
from src.db.models.user import User
from src.schemas.auth import (
    LoginCoachResponse,
    LoginCoachDetails,
    LoginRequest,
    LoginResponse,
    LoginUserResponse,
    LoginUserDetails,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from src.schemas.common import MessageResponse
from src.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Authentication"])


def perform_login(username: str, password: str, db: Session) -> LoginResponse:
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

    identity = AuthService.authenticate_user(db, username, password)

    if not identity:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    principal_type, principal = identity
    access_token, refresh_token = AuthService.create_tokens(db, principal_type, principal)

    api_logger.info(f"Login successful for user: {username}")

    if principal_type == "user" and isinstance(principal, User):
        return LoginUserResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=LoginUserDetails(
                user_id=principal.id,
                name=principal.name,
                username=principal.username,
                role=principal.role.value,
            ),
        )

    if principal_type == "coach" and isinstance(principal, Coach):
        return LoginCoachResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            coach=LoginCoachDetails(
                coach_id=principal.id,
                name=principal.name,
                username=principal.username,
            ),
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to construct login response",
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": LoginRequest.model_json_schema()
                }
            },
            "required": True,
        }
    }
)
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


@router.post(
    "/login/json",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
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
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Logout user by revoking refresh token.
    
    - **refresh_token**: Refresh token to revoke
    """
    if identity.user is not None:
        principal_name = identity.user.username
    elif identity.coach is not None:
        principal_name = identity.coach.username
    else:
        principal_name = "unknown"
    api_logger.info(f"Logout request from principal: {principal_name}")
    
    success = AuthService.logout(db, request.refresh_token)
    
    if success:
        api_logger.info(f"Principal logged out: {principal_name}")
        return MessageResponse(message="Successfully logged out", success=True)
    else:
        return MessageResponse(message="Token already revoked or invalid", success=True)
