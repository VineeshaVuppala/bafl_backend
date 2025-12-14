from __future__ import annotations

from datetime import date

import pytest
from src.db.models.attendance import AttendanceStatus
from src.db.models.batch import Batch
from src.db.models.school import School
from src.db.models.student import Student

from tests.test_attendance import seed_attendance_session


pytestmark = pytest.mark.anyio


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
