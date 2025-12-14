from __future__ import annotations

import pytest
import httpx
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.v1.endpoints import attendance
from src.api.v1.dependencies.auth import get_current_user
from src.db.database import Base, get_db
from src.db.models.batch import Batch
from src.db.models.coach import Coach
from src.db.models.school import School
from src.db.models.student import Student
from src.db.models.user import User, UserRole


@pytest.fixture(scope="session")
def engine():
    """Provide an in-memory SQLite engine shared across tests."""

    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a fresh database schema and transaction per test."""

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
    """Seed core reference data needed across attendance tests."""

    admin = User(name="Admin", username="admin@example.com", password="secret", role=UserRole.ADMIN)
    school = School(name="Central High", address="123 Main St")
    batch = Batch(batch_name="Batch A", school=school)
    student_one = Student(name="Alice", age=13, batch=batch)
    student_two = Student(name="Bob", age=14, batch=batch)
    coach = Coach(name="Coach Carter", username="coach.carter", password="hashed")

    db_session.add_all([admin, school, batch, student_one, student_two, coach])
    db_session.commit()

    db_session.refresh(admin)
    db_session.refresh(school)
    db_session.refresh(batch)
    db_session.refresh(student_one)
    db_session.refresh(student_two)
    db_session.refresh(coach)

    return {
        "user": admin,
        "school": school,
        "batch": batch,
        "students": [student_one, student_two],
        "coach": coach,
    }


@pytest.fixture(scope="function")
def test_app(db_session, base_data):
    """Create a FastAPI instance wired with attendance routes and overrides."""

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
    """Provide an async HTTP client against the configured FastAPI app."""

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
