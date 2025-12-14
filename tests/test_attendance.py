from datetime import date

import pytest
from sqlalchemy import select, func

from src.db.models.attendance import (
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
    CoachAttendance,
)
from src.db.models.coach import Coach


pytestmark = pytest.mark.anyio


def seed_attendance_session(db_session, school, user, session_date, status_map):
    attendance_session = AttendanceSession(
        school_id=school.id,
        date=session_date,
        taken_by_user_id=user.id,
    )
    db_session.add(attendance_session)
    db_session.commit()
    db_session.refresh(attendance_session)

    for student, status in status_map.items():
        db_session.add(
            AttendanceRecord(
                session_id=attendance_session.id,
                student_id=student.id,
                status=status,
            )
        )
    db_session.commit()

    return attendance_session


def seed_coach_attendance(db_session, coach, school, entry_date, coach_name=None):
    record = CoachAttendance(
        coach_id=coach.id if coach else None,
        coach_name=coach_name or (coach.name if coach else "Unknown Coach"),
        school_id=school.id,
        school_name=school.name,
        date=entry_date,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


async def test_mark_attendance_creates_session(client, db_session, base_data):
    target_date = date(2024, 1, 2)
    payload = {
        "school_id": base_data["school"].id,
        "date": target_date.isoformat(),
        "records": [
            {"id": base_data["students"][0].id, "status": "Present"},
            {"id": base_data["students"][1].id, "status": "Absent"},
        ],
    }

    response = await client.post("/api/v1/attendance/student", json=payload)
    assert response.status_code == 201

    body = response.json()
    assert body["message"] == "Attendance recorded successfully"
    assert body["studentsUpdated"] == 2
    assert body["coachName"] is None

    session_in_db = db_session.scalar(
        select(AttendanceSession).where(
            AttendanceSession.school_id == base_data["school"].id,
            AttendanceSession.date == target_date,
        )
    )
    assert session_in_db is not None

    records = db_session.scalars(
        select(AttendanceRecord).where(AttendanceRecord.session_id == session_in_db.id)
    ).all()
    assert len(records) == 2

    status_by_student = {record.student_id: record.status for record in records}
    assert status_by_student[base_data["students"][0].id] == AttendanceStatus.PRESENT
    assert status_by_student[base_data["students"][1].id] == AttendanceStatus.ABSENT


async def test_mark_attendance_upserts_coach_attendance(client, db_session, base_data):
    coach = base_data["coach"]
    target_date = date(2024, 2, 5)
    payload = {
        "school_id": base_data["school"].id,
        "date": target_date.isoformat(),
        "records": [
            {"id": base_data["students"][0].id, "status": "Present"},
            {"id": base_data["students"][1].id, "status": "Present"},
        ],
        "marked_by_coach": coach.username,
    }

    first_response = await client.post("/api/v1/attendance/student", json=payload)
    assert first_response.status_code == 201
    assert first_response.json()["coachName"] == coach.username

    initial_entry = db_session.scalar(
        select(CoachAttendance).where(
            CoachAttendance.school_id == base_data["school"].id,
            CoachAttendance.date == target_date,
        )
    )
    assert initial_entry is not None
    assert initial_entry.coach_id == coach.id
    assert initial_entry.coach_name == coach.username

    second_response = await client.post("/api/v1/attendance/student", json=payload)
    assert second_response.status_code == 201
    assert second_response.json()["studentsUpdated"] == 0

    entry_count = db_session.scalar(select(func.count(CoachAttendance.id)))
    assert entry_count == 1

    reloaded_entry = db_session.scalar(
        select(CoachAttendance).where(CoachAttendance.id == initial_entry.id)
    )
    assert reloaded_entry.coach_id == coach.id
    assert reloaded_entry.coach_name == coach.username


async def test_view_attendance_student(client, db_session, base_data):
    session_date = date(2024, 3, 10)
    seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        session_date,
        {
            base_data["students"][0]: AttendanceStatus.PRESENT,
            base_data["students"][1]: AttendanceStatus.ABSENT,
        },
    )

    response = await client.get(
        "/api/v1/attendance/view",
        params={
            "type": "student",
            "school_id": base_data["school"].id,
            "date": session_date.isoformat(),
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert body["type"] == "student"
    assert body["session_id"] is not None
    assert body["date"] == session_date.isoformat()
    assert len(body["records"]) == 2

    records_by_id = {record["id"]: record for record in body["records"]}
    assert records_by_id[base_data["students"][0].id]["status"] == AttendanceStatus.PRESENT.value
    assert records_by_id[base_data["students"][1].id]["status"] == AttendanceStatus.ABSENT.value


async def test_view_attendance_coach(client, db_session, base_data):
    session_date = date(2024, 4, 4)
    seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        session_date,
        {
            base_data["students"][0]: AttendanceStatus.PRESENT,
        },
    )
    seed_coach_attendance(db_session, base_data["coach"], base_data["school"], session_date)

    response = await client.get(
        "/api/v1/attendance/view",
        params={
            "type": "coach",
            "school_id": base_data["school"].id,
            "date": session_date.isoformat(),
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert body["type"] == "coach"
    assert body["session_id"] is not None
    assert len(body["records"]) == 1

    record = body["records"][0]
    assert record["coachName"] == base_data["coach"].name
    assert record["schoolName"] == base_data["school"].name
    assert record["date"] == session_date.isoformat()


async def test_edit_attendance_updates_record(client, db_session, base_data):
    session_date = date(2024, 5, 15)
    attendance_session = seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        session_date,
        {
            base_data["students"][0]: AttendanceStatus.ABSENT,
        },
    )

    payload = {
        "records": [
            {"id": base_data["students"][0].id, "status": "Present"},
        ]
    }

    response = await client.put(
        f"/api/v1/attendance/student/{attendance_session.id}",
        json=payload,
    )
    assert response.status_code == 200

    body = response.json()
    assert body["studentsUpdated"] == 1
    assert body["sessionId"] == attendance_session.id

    updated_record = db_session.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == attendance_session.id,
            AttendanceRecord.student_id == base_data["students"][0].id,
        )
    )
    assert updated_record is not None
    assert updated_record.status == AttendanceStatus.PRESENT


async def test_attendance_summary_student_all(client, db_session, base_data):
    session_one_date = date(2024, 6, 1)
    session_two_date = date(2024, 6, 2)
    seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        session_one_date,
        {
            base_data["students"][0]: AttendanceStatus.PRESENT,
            base_data["students"][1]: AttendanceStatus.ABSENT,
        },
    )
    seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        session_two_date,
        {
            base_data["students"][0]: AttendanceStatus.PRESENT,
            base_data["students"][1]: AttendanceStatus.PRESENT,
        },
    )

    response = await client.get(
        "/api/v1/attendance/summary",
        params={
            "school_id": base_data["school"].id,
            "start_date": session_one_date.isoformat(),
            "end_date": session_two_date.isoformat(),
            "type": "student",
        },
    )
    assert response.status_code == 200

    summary = response.json()
    assert len(summary) == 2

    by_student_id = {item["studentId"]: item for item in summary}

    student_one_summary = by_student_id[base_data["students"][0].id]
    assert student_one_summary["totalSessions"] == 2
    assert student_one_summary["presentDays"] == 2
    assert student_one_summary["absentDays"] == 0
    assert student_one_summary["percentage"] == 100.0

    student_two_summary = by_student_id[base_data["students"][1].id]
    assert student_two_summary["totalSessions"] == 2
    assert student_two_summary["presentDays"] == 1
    assert student_two_summary["absentDays"] == 1
    assert student_two_summary["percentage"] == 50.0


async def test_attendance_summary_student_single(client, db_session, base_data):
    session_one_date = date(2024, 7, 1)
    session_two_date = date(2024, 7, 2)
    seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        session_one_date,
        {
            base_data["students"][0]: AttendanceStatus.PRESENT,
            base_data["students"][1]: AttendanceStatus.ABSENT,
        },
    )
    seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        session_two_date,
        {
            base_data["students"][0]: AttendanceStatus.ABSENT,
            base_data["students"][1]: AttendanceStatus.PRESENT,
        },
    )

    response = await client.get(
        "/api/v1/attendance/summary",
        params={
            "school_id": base_data["school"].id,
            "start_date": session_one_date.isoformat(),
            "end_date": session_two_date.isoformat(),
            "type": "student",
            "studentId": base_data["students"][0].id,
        },
    )
    assert response.status_code == 200

    summary = response.json()
    assert len(summary) == 1

    student_summary = summary[0]
    assert student_summary["studentId"] == base_data["students"][0].id
    assert student_summary["totalSessions"] == 2
    assert student_summary["presentDays"] == 1
    assert student_summary["absentDays"] == 1
    assert student_summary["percentage"] == 50.0


async def test_attendance_summary_coach_all(client, db_session, base_data):
    session_one_date = date(2024, 8, 1)
    session_two_date = date(2024, 8, 2)
    seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        session_one_date,
        {base_data["students"][0]: AttendanceStatus.PRESENT},
    )
    seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        session_two_date,
        {base_data["students"][0]: AttendanceStatus.PRESENT},
    )

    coach_two = Coach(name="Coach Blake", username="coach.blake", password="hashed")
    db_session.add(coach_two)
    db_session.commit()
    db_session.refresh(coach_two)

    seed_coach_attendance(db_session, base_data["coach"], base_data["school"], session_one_date)
    seed_coach_attendance(db_session, base_data["coach"], base_data["school"], session_two_date)
    seed_coach_attendance(db_session, coach_two, base_data["school"], session_one_date)

    response = await client.get(
        "/api/v1/attendance/summary",
        params={
            "school_id": base_data["school"].id,
            "start_date": session_one_date.isoformat(),
            "end_date": session_two_date.isoformat(),
            "type": "coach",
        },
    )
    assert response.status_code == 200

    summary = response.json()
    assert len(summary) == 2

    by_coach_name = {item["coach_name"]: item for item in summary}

    coach_one_summary = by_coach_name[base_data["coach"].name]
    assert coach_one_summary["totalSessions"] == 2
    assert coach_one_summary["presentDays"] == 2

    coach_two_summary = by_coach_name[coach_two.name]
    assert coach_two_summary["totalSessions"] == 2
    assert coach_two_summary["presentDays"] == 1


async def test_attendance_summary_coach_single(client, db_session, base_data):
    session_one_date = date(2024, 9, 1)
    session_two_date = date(2024, 9, 2)
    seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        session_one_date,
        {base_data["students"][0]: AttendanceStatus.PRESENT},
    )
    seed_attendance_session(
        db_session,
        base_data["school"],
        base_data["user"],
        session_two_date,
        {base_data["students"][1]: AttendanceStatus.ABSENT},
    )

    seed_coach_attendance(db_session, base_data["coach"], base_data["school"], session_one_date)
    seed_coach_attendance(db_session, base_data["coach"], base_data["school"], session_two_date)

    response = await client.get(
        "/api/v1/attendance/summary",
        params={
            "school_id": base_data["school"].id,
            "start_date": session_one_date.isoformat(),
            "end_date": session_two_date.isoformat(),
            "type": "coach",
            "coachName": base_data["coach"].name,
        },
    )
    assert response.status_code == 200

    summary = response.json()
    assert len(summary) == 1

    coach_summary = summary[0]
    assert coach_summary["coach_name"] == base_data["coach"].name
    assert coach_summary["totalSessions"] == 2
    assert coach_summary["presentDays"] == 2
