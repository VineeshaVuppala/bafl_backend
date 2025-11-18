"""
User management endpoints for creating, viewing, updating, and deleting users.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Optional
from json import JSONDecodeError
from starlette.datastructures import FormData
from pydantic import ValidationError
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models.user import User, UserRole
from src.schemas.user import UserCreate, UserResponse, UserUpdate, UserListResponse
from src.schemas.common import MessageResponse
from src.services.user_service import UserService
from src.services.permission_service import PermissionService
from src.api.v1.dependencies.auth import (
    get_current_user,
    require_view_all_users,
    can_access_user,
    can_edit_user
)
from src.core.logging import api_logger


router = APIRouter(prefix="/users", tags=["User Management"])

SUPPORTED_CONTENT_TYPES_DETAIL = (
    "Supported content types are application/json, application/x-www-form-urlencoded, and multipart/form-data."
)


def _is_json_content_type(content_type: Optional[str]) -> bool:
    """Return ``True`` when the provided content type represents JSON."""

    if not content_type:
        return True
    return "application/json" in content_type


def _is_form_content_type(content_type: Optional[str]) -> bool:
    """Return ``True`` when the provided content type represents form data."""

    if not content_type:
        return False
    return any(
        candidate in content_type
        for candidate in ("application/x-www-form-urlencoded", "multipart/form-data")
    )


def _missing_field_errors(fields: list[str]) -> list[dict[str, object]]:
    """Produce FastAPI-compatible validation errors for missing form fields."""

    return [
        {"loc": ["body", field], "msg": "Field required", "type": "value_error.missing"}
        for field in fields
    ]


def _parse_optional_bool(value: object, field: str) -> Optional[bool]:
    """Parse truthy/falsey string values into ``bool`` while preserving ``None``."""

    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value

    value_str = str(value).strip().lower()
    if value_str in {"true", "1", "yes", "on"}:
        return True
    if value_str in {"false", "0", "no", "off"}:
        return False

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=[
            {
                "loc": ["body", field],
                "msg": "Invalid boolean value",
                "type": "type_error.bool",
            }
        ],
    )


def _parse_user_create_form(form: FormData) -> UserCreate:
    """Validate and normalise user creation data submitted via form payloads."""

    raw_data = {
        "name": form.get("name"),
        "username": form.get("username"),
        "password": form.get("password"),
        "role": form.get("role"),
    }

    missing = [field for field, value in raw_data.items() if value in (None, "")]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_missing_field_errors(missing),
        )

    raw_data["role"] = str(raw_data["role"]).lower()

    try:
        return UserCreate.model_validate(raw_data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(exc.errors()),
        ) from exc


def _parse_user_update_form(form: FormData) -> UserUpdate:
    """Validate and normalise user update data submitted via form payloads."""

    raw_data: dict[str, object] = {}

    for field in ("name", "username", "password"):
        value = form.get(field)
        if value not in (None, ""):
            raw_data[field] = value

    is_active_value = form.get("is_active")
    parsed_is_active = _parse_optional_bool(is_active_value, "is_active")
    if parsed_is_active is not None:
        raw_data["is_active"] = parsed_is_active

    try:
        return UserUpdate.model_validate(raw_data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(exc.errors()),
        ) from exc


async def _extract_user_create_payload(request: Request) -> UserCreate:
    """Read and validate user creation payload from JSON or form input."""

    content_type = request.headers.get("content-type")

    if _is_json_content_type(content_type):
        try:
            raw_data = await request.json()
        except JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON body.",
            ) from exc

        try:
            return UserCreate.model_validate(raw_data)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=jsonable_encoder(exc.errors()),
            ) from exc

    if _is_form_content_type(content_type):
        form = await request.form()
        return _parse_user_create_form(form)

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=SUPPORTED_CONTENT_TYPES_DETAIL,
    )


async def _extract_user_update_payload(request: Request) -> UserUpdate:
    """Read and validate user update payload from JSON or form input."""

    content_type = request.headers.get("content-type")

    if _is_json_content_type(content_type):
        try:
            raw_data = await request.json()
        except JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON body.",
            ) from exc

        try:
            return UserUpdate.model_validate(raw_data)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=jsonable_encoder(exc.errors()),
            ) from exc

    if _is_form_content_type(content_type):
        form = await request.form()
        return _parse_user_update_form(form)

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=SUPPORTED_CONTENT_TYPES_DETAIL,
    )


def perform_create_user(
    name: str,
    username: str,
    password: str,
    role: UserRole,
    current_user: User,
    db: Session
) -> UserResponse:
    """
    Core user creation logic.
    
    Args:
        name: User's full name
        username: Unique username
        password: User's password
        role: User role
        current_user: User creating this user
        db: Database session
        
    Returns:
        UserResponse with created user data
        
    Raises:
        HTTPException: If permission denied or username exists
    """
    api_logger.info(
        f"User creation request by {current_user.username} for new user: {username}"
    )
    
    # Check if current user can create this role
    if not PermissionService.can_create_role(db, current_user, role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to create users with role: {role.value}"
        )
    
    # Create user
    new_user = UserService.create_user(
        db=db,
        name=name,
        username=username,
        password=password,
        role=role,
        creator=current_user
    )
    
    # Get user permissions for response
    permissions = PermissionService.get_user_permissions(db, new_user)
    
    return UserResponse(
        id=new_user.id,
        name=new_user.name,
        username=new_user.username,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        permissions=[p.value for p in permissions]
    )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Create a new user from either JSON or form payloads."""

    user_data = await _extract_user_create_payload(request)

    return perform_create_user(
        user_data.name,
        user_data.username,
        user_data.password,
        user_data.role,
        current_user,
        db
    )


@router.post(
    "/json",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False
)
async def create_user_json_legacy(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Backward compatible JSON-only endpoint kept for existing clients/tests."""

    return perform_create_user(
        user_data.name,
        user_data.username,
        user_data.password,
        user_data.role,
        current_user,
        db
    )


@router.get("/", response_model=UserListResponse, status_code=status.HTTP_200_OK)
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_view_all_users),
    db: Session = Depends(get_db)
) -> UserListResponse:
    """
    List all users. Requires VIEW_ALL_USERS permission (ADMIN only).
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    """
    api_logger.info(f"User list requested by {current_user.username}")
    
    users = UserService.get_all_users(db, skip, limit)
    
    user_responses = []
    for user in users:
        permissions = PermissionService.get_user_permissions(db, user)
        user_responses.append(
            UserResponse(
                id=user.id,
                name=user.name,
                username=user.username,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                permissions=[p.value for p in permissions]
            )
        )
    
    return UserListResponse(users=user_responses, total=len(user_responses))


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Get current authenticated user's information.
    """
    api_logger.info(f"User info requested by {current_user.username}")
    
    permissions = PermissionService.get_user_permissions(db, current_user)
    
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        permissions=[p.value for p in permissions]
    )


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Get a specific user by ID. 
    - ADMIN can view all users
    - Users/Coaches can only view their own profile
    
    - **user_id**: User ID
    """
    api_logger.info(f"User {user_id} info requested by {current_user.username}")
    
    # Check if user can access this profile
    if not can_access_user(user_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile"
        )
    
    user = UserService.get_user_by_id(db, user_id)
    permissions = PermissionService.get_user_permissions(db, user)
    
    return UserResponse(
        id=user.id,
        name=user.name,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        permissions=[p.value for p in permissions]
    )


def perform_update_user(
    user_id: int,
    name: Optional[str],
    username: Optional[str],
    password: Optional[str],
    is_active: Optional[bool],
    current_user: User,
    db: Session
) -> UserResponse:
    """
    Core user update logic.
    
    Args:
        user_id: User ID to update
        name: New name (optional)
        username: New username (optional)
        password: New password (optional)
        is_active: New active status (optional)
        current_user: User performing the update
        db: Database session
        
    Returns:
        UserResponse with updated user data
        
    Raises:
        HTTPException: If permission denied or username exists
    """
    api_logger.info(f"User {user_id} update requested by {current_user.username}")
    
    # Check if user can edit this profile
    if not can_edit_user(user_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own profile"
        )
    
    updated_user = UserService.update_user(
        db=db,
        user_id=user_id,
        name=name,
        username=username,
        password=password,
        is_active=is_active
    )
    
    permissions = PermissionService.get_user_permissions(db, updated_user)
    
    return UserResponse(
        id=updated_user.id,
        name=updated_user.name,
        username=updated_user.username,
        role=updated_user.role,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at,
        permissions=[p.value for p in permissions]
    )


@router.put("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Update a user from either JSON or form payloads."""

    user_update = await _extract_user_update_payload(request)

    return perform_update_user(
        user_id,
        user_update.name,
        user_update.username,
        user_update.password,
        user_update.is_active,
        current_user,
        db
    )


@router.put(
    "/{user_id}/json",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
async def update_user_json_legacy(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Backward compatible JSON-only endpoint kept for existing clients/tests."""

    return perform_update_user(
        user_id,
        user_update.name,
        user_update.username,
        user_update.password,
        user_update.is_active,
        current_user,
        db
    )


@router.delete("/{user_id}", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Delete a user. Requires the appropriate delete permission for the target role.
    
    - **user_id**: User ID
    """
    api_logger.info(f"User {user_id} deletion requested by {current_user.username}")

    target_user = UserService.get_user_by_id(db, user_id)

    if not PermissionService.can_delete_user(db, current_user, target_user):
        required_permission = PermissionService.get_delete_permission_for_role(target_user.role)
        detail = "You do not have permission to delete this user"
        if required_permission:
            detail = f"Missing required permission: {required_permission.value}"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

    UserService.delete_user(db, target_user, current_user)

    return MessageResponse(message="User deleted successfully", success=True)
