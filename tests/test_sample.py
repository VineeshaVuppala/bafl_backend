"""Integration tests covering permissions and role-based operations."""

from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.v1.router import api_v1_router
from src.core.security import PasswordHandler
from src.db.database import Base, get_db
from src.db.models.user import UserRole
from src.db.repositories.user_repository import UserRepository
from src.utils.db_init import (
    create_initial_permissions,
    create_default_role_permissions,
)


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "AdminPass123!"
DEFAULT_PASSWORD = "Password123!"


def _build_test_app(session_factory):
    """Create a FastAPI app instance bound to the given session factory."""
    app = FastAPI()
    app.include_router(api_v1_router, prefix="/api")

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest_asyncio.fixture
async def api_client():
    """Provide an API client with an isolated in-memory database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    # Seed database with initial permissions and admin user
    with TestingSessionLocal() as db:
        create_initial_permissions(db)
        create_default_role_permissions(db)
        UserRepository.create(
            db,
            {
                "name": "System Admin",
                "username": ADMIN_USERNAME,
                "hashed_password": PasswordHandler.hash(ADMIN_PASSWORD),
                "role": UserRole.ADMIN,
                "is_active": True,
            },
        )

    app = _build_test_app(TestingSessionLocal)
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://testserver")

    try:
        yield client
    finally:
        await client.aclose()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


async def login(client: AsyncClient, username: str, password: str) -> str:
    """Authenticate a user and return the access token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    return data["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    """Return authorization headers for requests."""
    return {"Authorization": f"Bearer {token}"}


async def create_user(
    client: AsyncClient,
    token: str,
    *,
    role: UserRole,
    password: str = DEFAULT_PASSWORD,
) -> dict:
    """Create a user via the API and return the response body."""
    username = f"user_{uuid4().hex[:8]}"
    payload = {
        "name": f"Test {username}",
        "username": username,
        "password": password,
        "role": role.value,
    }
    response = await client.post(
        "/api/v1/users/",
        json=payload,
        headers=auth_headers(token),
    )
    assert response.status_code == 201, response.text
    data = response.json()
    data["plain_password"] = password  # include for convenience in tests
    return data


async def assign_permission(
    client: AsyncClient,
    token: str,
    user_id: int,
    permission: str,
) -> None:
    """Assign a permission to a user."""
    response = await client.post(
        "/api/v1/permissions/assign",
        json={"user_id": user_id, "permission": permission},
        headers=auth_headers(token),
    )
    assert response.status_code == 200, response.text


async def get_user_details(
    client: AsyncClient,
    token: str,
    user_id: int,
) -> dict:
    """Fetch a user's details via the API."""
    response = await client.get(
        f"/api/v1/users/{user_id}",
        headers=auth_headers(token),
    )
    assert response.status_code == 200, response.text
    return response.json()


async def get_user_permissions(
    client: AsyncClient,
    token: str,
    user_id: int,
) -> list[str]:
    """Fetch the permissions assigned to a user."""
    response = await client.get(
        f"/api/v1/permissions/user/{user_id}",
        headers=auth_headers(token),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    return payload["permissions"]


@pytest.mark.asyncio
async def test_admin_can_create_admin(api_client: AsyncClient) -> None:
    """Admins should be able to create additional admin accounts."""
    token = await login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = await api_client.post(
        "/api/v1/users/",
        json={
            "name": "Second Admin",
            "username": "secondary_admin",
            "password": "SecurePass456!",
            "role": UserRole.ADMIN.value,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == UserRole.ADMIN.value


@pytest.mark.asyncio
async def test_user_needs_permission_to_create_coach(api_client: AsyncClient) -> None:
    """A user must have the create_coach permission to create coaches."""
    admin_token = await login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    creator = await create_user(api_client, admin_token, role=UserRole.USER)

    user_token = await login(api_client, creator["username"], creator["plain_password"])

    # Attempt to create a coach without permission
    response = await api_client.post(
        "/api/v1/users/",
        json={
            "name": "Coach Candidate",
            "username": "coach_candidate",
            "password": "CoachPass!",
            "role": UserRole.COACH.value,
        },
        headers=auth_headers(user_token),
    )
    assert response.status_code == 403

    # Grant create_coach permission and retry
    await assign_permission(api_client, admin_token, creator["id"], "create_coach")

    response = await api_client.post(
        "/api/v1/users/",
        json={
            "name": "Coach Success",
            "username": "coach_success",
            "password": "CoachPass!",
            "role": UserRole.COACH.value,
        },
        headers=auth_headers(user_token),
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_delete_permissions_are_role_specific(api_client: AsyncClient) -> None:
    """Deleting users requires role-specific delete permissions."""
    admin_token = await login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    coach = await create_user(api_client, admin_token, role=UserRole.COACH)

    deleter = await create_user(api_client, admin_token, role=UserRole.USER)
    deleter_token = await login(api_client, deleter["username"], deleter["plain_password"])

    # Without delete permissions, deletion should fail
    response = await api_client.delete(
        f"/api/v1/users/{coach['id']}",
        headers=auth_headers(deleter_token),
    )
    assert response.status_code == 403

    # Grant delete_coach permission and retry
    await assign_permission(api_client, admin_token, deleter["id"], "delete_coach")

    response = await api_client.delete(
        f"/api/v1/users/{coach['id']}",
        headers=auth_headers(deleter_token),
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_cannot_delete_admin_without_permission(api_client: AsyncClient) -> None:
    """Ensure delete_admin permission is required to delete administrators."""
    admin_token = await login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    new_admin = await create_user(api_client, admin_token, role=UserRole.ADMIN)

    deleter = await create_user(api_client, admin_token, role=UserRole.USER)
    deleter_token = await login(api_client, deleter["username"], deleter["plain_password"])

    # Grant delete_user but not delete_admin
    await assign_permission(api_client, admin_token, deleter["id"], "delete_user")

    response = await api_client.delete(
        f"/api/v1/users/{new_admin['id']}",
        headers=auth_headers(deleter_token),
    )
    assert response.status_code == 403

    # Grant delete_admin and try again
    await assign_permission(api_client, admin_token, deleter["id"], "delete_admin")

    response = await api_client.delete(
        f"/api/v1/users/{new_admin['id']}",
        headers=auth_headers(deleter_token),
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_create_admin_permission_for_non_admin_user(api_client: AsyncClient) -> None:
    """Users granted create_admin should be able to create admin accounts."""
    admin_token = await login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    privileged_user = await create_user(api_client, admin_token, role=UserRole.USER)

    user_token = await login(
        api_client,
        privileged_user["username"],
        privileged_user["plain_password"],
    )

    await assign_permission(api_client, admin_token, privileged_user["id"], "create_admin")

    response = await api_client.post(
        "/api/v1/users/",
        json={
            "name": "Delegated Admin",
            "username": "delegated_admin",
            "password": "DelegatedPass!",
            "role": UserRole.ADMIN.value,
        },
        headers=auth_headers(user_token),
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_create_user_accepts_json_and_form(api_client: AsyncClient) -> None:
    """User creation endpoint should accept both JSON and form payloads."""

    admin_token = await login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)

    json_username = f"json_{uuid4().hex[:8]}"
    json_response = await api_client.post(
        "/api/v1/users/",
        json={
            "name": "JSON User",
            "username": json_username,
            "password": "JsonPass123!",
            "role": UserRole.COACH.value,
        },
        headers=auth_headers(admin_token),
    )
    assert json_response.status_code == 201, json_response.text
    assert json_response.json()["username"] == json_username

    form_username = f"form_{uuid4().hex[:8]}"
    form_response = await api_client.post(
        "/api/v1/users/",
        data={
            "name": "Form User",
            "username": form_username,
            "password": "FormPass123!",
            "role": UserRole.USER.value,
        },
        headers=auth_headers(admin_token),
    )
    assert form_response.status_code == 201, form_response.text
    form_payload = form_response.json()
    assert form_payload["username"] == form_username
    assert form_payload["role"] == UserRole.USER.value


@pytest.mark.asyncio
async def test_update_user_accepts_json_and_form(api_client: AsyncClient) -> None:
    """User update endpoint should accept JSON and form data separately."""

    admin_token = await login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    user = await create_user(api_client, admin_token, role=UserRole.USER)

    new_password = "NewPass456!"
    json_update = await api_client.put(
        f"/api/v1/users/{user['id']}",
        json={
            "name": "Updated JSON",
            "password": new_password,
        },
        headers=auth_headers(admin_token),
    )
    assert json_update.status_code == 200, json_update.text
    updated_body = json_update.json()
    assert updated_body["name"] == "Updated JSON"

    # Newly set password should work
    json_login_response = await api_client.post(
        "/api/v1/auth/login",
        json={"username": user["username"], "password": new_password},
    )
    assert json_login_response.status_code == 200, json_login_response.text

    new_username = f"renamed_{uuid4().hex[:6]}"
    form_update = await api_client.put(
        f"/api/v1/users/{user['id']}",
        data={
            "username": new_username,
            "is_active": "false",
        },
        headers=auth_headers(admin_token),
    )
    assert form_update.status_code == 200, form_update.text
    form_body = form_update.json()
    assert form_body["username"] == new_username
    assert form_body["is_active"] is False

    user_snapshot = await get_user_details(api_client, admin_token, user["id"])
    assert user_snapshot["username"] == new_username
    assert user_snapshot["is_active"] is False

    # Disabled user should no longer be able to login
    login_after_deactivation = await api_client.post(
        "/api/v1/auth/login",
        json={"username": new_username, "password": new_password},
    )
    assert login_after_deactivation.status_code == 401


@pytest.mark.asyncio
async def test_permission_assign_and_revoke_accepts_json_and_form(api_client: AsyncClient) -> None:
    """Permission endpoints must accept both JSON and form submissions."""

    admin_token = await login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    managed_user = await create_user(api_client, admin_token, role=UserRole.USER)

    json_assign = await api_client.post(
        "/api/v1/permissions/assign",
        json={"user_id": managed_user["id"], "permission": "create_coach"},
        headers=auth_headers(admin_token),
    )
    assert json_assign.status_code == 200, json_assign.text

    form_assign = await api_client.post(
        "/api/v1/permissions/assign",
        data={"user_id": str(managed_user["id"]), "permission": "delete_user"},
        headers=auth_headers(admin_token),
    )
    assert form_assign.status_code == 200, form_assign.text

    permissions_after_assign = await get_user_permissions(
        api_client, admin_token, managed_user["id"]
    )
    assert "create_coach" in permissions_after_assign
    assert "delete_user" in permissions_after_assign

    json_revoke = await api_client.post(
        "/api/v1/permissions/revoke",
        json={"user_id": managed_user["id"], "permission": "delete_user"},
        headers=auth_headers(admin_token),
    )
    assert json_revoke.status_code == 200, json_revoke.text

    form_revoke = await api_client.post(
        "/api/v1/permissions/revoke",
        data={"user_id": str(managed_user["id"]), "permission": "create_coach"},
        headers=auth_headers(admin_token),
    )
    assert form_revoke.status_code == 200, form_revoke.text

    final_permissions = await get_user_permissions(api_client, admin_token, managed_user["id"])
    assert "create_coach" not in final_permissions
    assert "delete_user" not in final_permissions


@pytest.mark.asyncio
async def test_create_user_missing_form_fields_returns_422(api_client: AsyncClient) -> None:
    """Form submissions missing required user fields should fail validation."""

    admin_token = await login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = await api_client.post(
        "/api/v1/users/",
        data={"name": "Incomplete"},
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 422
    body = response.json()
    assert any(err["loc"] == ["body", "username"] for err in body["detail"])
    assert any(err["loc"] == ["body", "password"] for err in body["detail"])
    assert any(err["loc"] == ["body", "role"] for err in body["detail"])


@pytest.mark.asyncio
async def test_update_user_invalid_boolean_form_returns_422(api_client: AsyncClient) -> None:
    """Form submissions with invalid boolean values should raise validation errors."""

    admin_token = await login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    user = await create_user(api_client, admin_token, role=UserRole.USER)

    response = await api_client.put(
        f"/api/v1/users/{user['id']}",
        data={"is_active": "maybe"},
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"][0]["loc"] == ["body", "is_active"]


@pytest.mark.asyncio
async def test_create_user_unsupported_media_type(api_client: AsyncClient) -> None:
    """Requests sent with unsupported media types should receive 415 responses."""

    admin_token = await login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = await api_client.post(
        "/api/v1/users/",
        content=b"name=raw",
        headers={**auth_headers(admin_token), "Content-Type": "text/plain"},
    )
    assert response.status_code == 415
