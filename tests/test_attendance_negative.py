from __future__ import annotations

from datetime import date

import pytest
import httpx
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.v1.endpoints import attendance
from src.api.v1.dependencies.auth import get_current_user
from src.db.database import Base, get_db
from src.db.models.attendance import AttendanceStatus
from src.db.models.batch import Batch
from src.db.models.school import School
from src.db.models.student import Student
from src.db.models.user import User, UserRole

from tests.test_attendance import seed_attendance_session


pytestmark = pytest.mark.anyio


@pytest.fixture(scope="session")
def engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(scope="function")
def db_session(engine):
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def base_data(db_session):
    admin = User(name="Admin", username="admin@example.com", password="secret", role=UserRole.ADMIN)
    school = School(name="Central High", address="123 Main St")
    batch = Batch(batch_name="Batch A", school=school)
    student_one = Student(name="Alice", age=13, batch=batch)
    student_two = Student(name="Bob", age=14, batch=batch)

    db_session.add_all([admin, school, batch, student_one, student_two])
    db_session.commit()

    for model in (admin, school, batch, student_one, student_two):
        db_session.refresh(model)

    return {
        "user": admin,
        "school": school,
        "batch": batch,
        "students": [student_one, student_two],
    }


@pytest.fixture(scope="function")
def test_app(db_session, base_data):
    app = FastAPI()
    app.include_router(attendance.router, prefix="/api/v1")

    def override_get_db():
        yield db_session

    def override_get_current_user():
        return base_data["user"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client(test_app):
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


async def test_mark_attendance_missing_school_id(client):
    payload = {
        "date": date(2024, 1, 1).isoformat(),
        "records": [],
    }

    response = await client.post("/api/v1/attendance/student", json=payload)
    assert response.status_code == 422
    payload = response.json()["detail"][0]
    assert payload["loc"][-1] == "school_id"
    assert payload["msg"].lower().startswith("field required")


async def test_mark_attendance_invalid_status(client, base_data):
    payload = {
        "school_id": base_data["school"].id,
        "date": date(2024, 1, 2).isoformat(),
        "records": [
            {"id": base_data["students"][0].id, "status": "banana"},
        ],
    }

    response = await client.post("/api/v1/attendance/student", json=payload)
    assert response.status_code == 400
    assert "Invalid attendance status value" in response.json()["detail"]


async def test_view_attendance_no_session(client, base_data):
    response = await client.get(
        "/api/v1/attendance/view",
        params={
            "type": "student",
            "school_id": base_data["school"].id,
            "date": date(2024, 1, 3).isoformat(),
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "No attendance session found for given filters"


async def test_edit_attendance_session_not_found(client):
    response = await client.put(
        "/api/v1/attendance/student/9999",
        json={"records": []},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Attendance session not found"


async def test_attendance_summary_missing_school_id(client):
    response = await client.get(
        "/api/v1/attendance/summary",
        params={
            "type": "student",
            "start_date": date(2024, 1, 1).isoformat(),
            "end_date": date(2024, 1, 2).isoformat(),
            "school_id": 0,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "school_id is required"


async def test_attendance_summary_invalid_type(client, base_data):
    response = await client.get(
        "/api/v1/attendance/summary",
        params={
            "type": "wrong",
            "school_id": base_data["school"].id,
            "start_date": date(2024, 1, 1).isoformat(),
            "end_date": date(2024, 1, 2).isoformat(),
        },
    )
    assert response.status_code == 422
    assert "String should match pattern" in response.text



async def test_attendance_summary_no_coach_data(client, db_session, base_data):
    seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        date(2024, 1, 4),
        {base_data["students"][0]: AttendanceStatus.PRESENT},
    )

    response = await client.get(
        "/api/v1/attendance/summary",
        params={
            "type": "coach",
            "school_id": base_data["school"].id,
            "start_date": date(2024, 1, 1).isoformat(),
            "end_date": date(2024, 1, 5).isoformat(),
            "coachName": "Nonexistent Coach",
        },
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_mark_attendance_student_not_in_school(client, db_session, base_data):
    other_school = School(name="South Academy", address="456 Elm St")
    other_batch = Batch(batch_name="Batch B", school=other_school)
    outsider = Student(name="Charlie", age=15, batch=other_batch)

    db_session.add_all([other_school, other_batch, outsider])
    db_session.commit()
    db_session.refresh(outsider)

    payload = {
        "school_id": base_data["school"].id,
        "date": date(2024, 1, 6).isoformat(),
        "records": [
            {"id": outsider.id, "status": "Present"},
        ],
    }

    response = await client.post("/api/v1/attendance/student", json=payload)
    assert response.status_code == 400
    expected_detail = f"Student {outsider.id} does not belong to school {base_data['school'].id}"
    assert response.json()["detail"] == expected_detail
