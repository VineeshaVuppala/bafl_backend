import pytest
import httpx
from main import app

from src.db.database import init_database, SessionLocal
from src.db.models.coach import Coach
from src.db.models.batch import Batch
from src.db.models.student import Student
from src.db.models.user import UserRole


pytestmark = pytest.mark.anyio


def make_dummy_user(role, coach_id=None):
    class DummyUser:
        pass

    u = DummyUser()
    u.role = role
    if coach_id is not None:
        u.coach_profile = type('C', (), {'id': coach_id})()
    else:
        u.coach_profile = None
    u.id = 9999
    return u


@pytest.fixture(autouse=True)
def setup_db():
    # Initialize tables
    init_database()
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


async def test_create_with_results_happy_path(client):
    db = SessionLocal()
    # create coach, batch, students
    coach = Coach(username='coach1', name='Coach One', password='hashed')
    db.add(coach)
    db.commit()
    db.refresh(coach)

    batch = Batch(name='Batch A', coach_id=coach.id)
    db.add(batch)
    db.commit()
    db.refresh(batch)

    s1 = Student(name='S1', age=10, batch_id=batch.id)
    s2 = Student(name='S2', age=11, batch_id=batch.id)
    db.add_all([s1, s2])
    db.commit()

    # Override dependency to simulate coach
    import src.api.v1.endpoints.assessments as assessments
    dummy = make_dummy_user(UserRole.COACH, coach_id=coach.id)
    app.dependency_overrides[assessments.require_add_sessions] = lambda: dummy

    payload = {
        "coach_id": coach.id,
        "school_id": None,
        "batch_id": batch.id,
        "date_of_session": "2025-11-23",
        "results": [
            {"student_id": s1.id, "curl_up": 10, "push_up": 5},
            {"student_id": s2.id, "curl_up": 0, "push_up": 0}
        ]
    }

    resp = await client.post("/api/v1/physical/sessions/create-with-results", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data.get('id') is not None
    assert isinstance(data.get('results'), list)
    assert len(data['results']) == 2

    db.close()


async def test_create_with_results_invalid_student_rejected(client):
    db = SessionLocal()
    coach = Coach(username='coach2', name='Coach Two', password='hashed')
    db.add(coach)
    db.commit()
    db.refresh(coach)

    batch1 = Batch(name='Batch1', coach_id=coach.id)
    batch2 = Batch(name='Batch2', coach_id=coach.id)
    db.add_all([batch1, batch2])
    db.commit()
    db.refresh(batch1)
    db.refresh(batch2)

    s1 = Student(name='A', age=12, batch_id=batch1.id)
    s2 = Student(name='B', age=13, batch_id=batch2.id)  # different batch
    db.add_all([s1, s2])
    db.commit()

    import src.api.v1.endpoints.assessments as assessments
    dummy = make_dummy_user(UserRole.COACH, coach_id=coach.id)
    app.dependency_overrides[assessments.require_add_sessions] = lambda: dummy

    payload = {
        "coach_id": coach.id,
        "school_id": None,
        "batch_id": batch1.id,
        "date_of_session": "2025-11-23",
        "results": [
            {"student_id": s1.id, "curl_up": 10},
            {"student_id": s2.id, "curl_up": 5}
        ]
    }

    resp = await client.post("/api/v1/physical/sessions/create-with-results", json=payload)
    assert resp.status_code == 400

    db.close()


async def test_atomic_rollback_on_negative_value(client):
    db = SessionLocal()
    coach = Coach(username='coach3', name='Coach Three', password='hashed')
    db.add(coach)
    db.commit()
    db.refresh(coach)

    batch = Batch(name='BatchX', coach_id=coach.id)
    db.add(batch)
    db.commit()
    db.refresh(batch)

    s1 = Student(name='P', age=14, batch_id=batch.id)
    db.add(s1)
    db.commit()

    import src.api.v1.endpoints.assessments as assessments
    dummy = make_dummy_user(UserRole.COACH, coach_id=coach.id)
    app.dependency_overrides[assessments.require_add_sessions] = lambda: dummy

    payload = {
        "coach_id": coach.id,
        "school_id": None,
        "batch_id": batch.id,
        "date_of_session": "2025-11-23",
        "results": [
            {"student_id": s1.id, "curl_up": -5}
        ]
    }

    resp = await client.post("/api/v1/physical/sessions/create-with-results", json=payload)
    assert resp.status_code == 400

    # ensure no session created
    sessions = db.execute("SELECT count(*) FROM physical_assessment_sessions WHERE batch_id = :b", {'b': batch.id}).scalar()
    assert sessions == 0

    db.close()
