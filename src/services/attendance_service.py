# src/services/attendance_service.py
from datetime import date
from typing import Any, List

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.db.models.attendance import (
    AttendanceSession,
    AttendanceRecord,
    AttendanceStatus,
    CoachAttendance,
)
from src.db.models.school import School
from src.db.models.student import Student
from src.db.models.coach import Coach
from src.db.models.user import User

from src.db.repositories.coach_repository import CoachRepository


def _coerce_status_value(raw_status: Any) -> AttendanceStatus:
    """Normalize incoming status payloads regardless of casing or shorthand."""
    if isinstance(raw_status, AttendanceStatus):
        return raw_status
    if isinstance(raw_status, bool):
        return AttendanceStatus.PRESENT if raw_status else AttendanceStatus.ABSENT
    if isinstance(raw_status, (int, float)):
        return AttendanceStatus.PRESENT if raw_status else AttendanceStatus.ABSENT
    if isinstance(raw_status, str):
        normalized = raw_status.strip().lower()
        if normalized in {"present", "p", "1", "true", "yes"}:
            return AttendanceStatus.PRESENT
        if normalized in {"absent", "a", "0", "false", "no"}:
            return AttendanceStatus.ABSENT
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid attendance status value: {raw_status}",
    )


def _upsert_coach_attendance(db: Session, school: School, record_date: date, coach_name: str) -> None:
    coach = CoachRepository.get_by_username(db, coach_name)
    if not coach:
        coach = db.scalar(select(Coach).where(Coach.name == coach_name))

    existing_ca = db.scalar(
        select(CoachAttendance).where(
            CoachAttendance.coach_name == coach_name,
            CoachAttendance.school_id == school.id,
            CoachAttendance.date == record_date,
        )
    )

    if existing_ca:
        needs_update = False
        coach_id = coach.id if coach else None
        if existing_ca.coach_id != coach_id:
            existing_ca.coach_id = coach_id
            needs_update = True
        if existing_ca.coach_name != coach_name:
            existing_ca.coach_name = coach_name
            needs_update = True
        if needs_update:
            db.add(existing_ca)
            db.commit()
        return

    new_ca = CoachAttendance(
        coach_id=coach.id if coach else None,
        coach_name=coach_name,
        school_id=school.id,
        school_name=school.name,
        date=record_date,
    )
    db.add(new_ca)
    db.commit()


def mark_attendance(db: Session, payload: Any, current_user: User) -> dict:
    # Resolve school by id
    school = db.scalar(select(School).where(School.id == payload.school_id))
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    record_date: date = payload.date

    # Find or create AttendanceSession for (school_id, date)
    session = db.scalar(
        select(AttendanceSession).where(
            AttendanceSession.school_id == school.id,
            AttendanceSession.date == record_date,
        )
    )

    if not session:
        session = AttendanceSession(
            school_id=school.id,
            date=record_date,
            taken_by_user_id=current_user.id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    students_updated = 0

    # Upsert attendance records
    for rec in payload.records:
        student = db.scalar(select(Student).where(Student.id == rec.id))
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with id {rec.id} not found")
        # Validate student belongs to the same school via student's batch
        if not student.batch or getattr(student.batch, "school_id", None) != school.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Student {rec.id} does not belong to school {school.id}")

        existing = db.scalar(
            select(AttendanceRecord).where(
                AttendanceRecord.session_id == session.id,
                AttendanceRecord.student_id == student.id,
            )
        )

        status_enum = _coerce_status_value(rec.status)

        if existing:
            if existing.status != status_enum:
                existing.status = status_enum
                db.add(existing)
                db.commit()
                students_updated += 1
        else:
            new_rec = AttendanceRecord(session_id=session.id, student_id=student.id, status=status_enum)
            db.add(new_rec)
            db.commit()
            students_updated += 1

    # If marked_by_coach present, create/update CoachAttendance
    coach_name = getattr(payload, "marked_by_coach", None)
    if coach_name:
        _upsert_coach_attendance(db, school, record_date, coach_name)

    return {"message": "Attendance recorded successfully", "sessionId": session.id, "studentsUpdated": students_updated, "coachName": coach_name}


def view_attendance(db: Session, type_: str, school_id: int, date_val: date) -> dict:
    if type_ not in ("student", "coach"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid type parameter")

    # Load the most recent (or only) attendance session for the school + date
    session = db.scalar(
        select(AttendanceSession)
        .where(
            AttendanceSession.school_id == school_id,
            AttendanceSession.date == date_val,
        )
        .order_by(AttendanceSession.id.desc())
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No attendance session found for given filters")

    records_out = []
    if type_ == "student":
        # List students for the school by joining batches -> students
        from src.db.models.batch import Batch
        students = db.scalars(select(Student).join(Batch, Student.batch_id == Batch.id).where(Batch.school_id == school_id)).all()

        for s in students:
            rec = db.scalar(select(AttendanceRecord).where(AttendanceRecord.session_id == session.id, AttendanceRecord.student_id == s.id))
            status_value = rec.status.value if rec else "Absent"
            records_out.append({"id": s.id, "name": s.name, "status": status_value})
    else:
        # coach view: return CoachAttendance records for this school + date
        cas = db.scalars(select(CoachAttendance).where(CoachAttendance.school_id == school_id, CoachAttendance.date == date_val)).all()
        for c in cas:
            records_out.append({"coachName": c.coach_name, "schoolName": c.school_name, "date": c.date.isoformat()})

    response = {"session_id": session.id, "date": session.date, "type": type_, "records": records_out}
    return response


def edit_attendance(db: Session, session_id: int, payload: Any, current_user: User) -> dict:
    session = db.scalar(select(AttendanceSession).where(AttendanceSession.id == session_id))
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance session not found"
        )

    students_updated = 0

    for rec in payload.records:
        student = db.scalar(select(Student).where(Student.id == rec.id))
        if not student:
            continue

        existing = db.scalar(
            select(AttendanceRecord)
            .where(
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.student_id == student.id
            )
        )

        status_enum = _coerce_status_value(rec.status)

        if existing:
            db.refresh(existing)
            if existing.status != status_enum:
                existing.status = status_enum
                db.add(existing)
                students_updated += 1
        else:
            new_rec = AttendanceRecord(
                session_id=session_id,
                student_id=student.id,
                status=status_enum
            )
            db.add(new_rec)
            students_updated += 1

    db.commit()  # ❗ COMMIT ONCE AFTER THE LOOP

    return {
        "message": "Attendance updated successfully",
        "sessionId": session_id,
        "studentsUpdated": students_updated
    }


def attendance_summary(
    db: Session,
    start_date: date,
    end_date: date,
    summary_type: str,
    student_id: int | None = None,
    school_id: int | None = None,
    coach_name: str | None = None,
) -> List[dict]:
    if not school_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="school_id is required")

    normalized_type = (summary_type or "").lower()
    if normalized_type not in {"student", "coach"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid summary type")

    total_sessions = db.scalar(
        select(func.count(AttendanceSession.id)).where(
            AttendanceSession.school_id == school_id,
            AttendanceSession.date.between(start_date, end_date),
        )
    ) or 0

    if normalized_type == "student":
        students = []
        if student_id:
            s = db.scalar(select(Student).where(Student.id == student_id))
            if not s:
                return []
            students = [s]
        else:
            from src.db.models.batch import Batch

            students = db.scalars(
                select(Student)
                .join(Batch, Student.batch_id == Batch.id)
                .where(Batch.school_id == school_id)
            ).all()

        out: List[dict] = []
        for s in students:
            present_days = db.scalar(
                select(func.count(AttendanceRecord.id))
                .select_from(AttendanceRecord)
                .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
                .where(
                    AttendanceRecord.student_id == s.id,
                    AttendanceRecord.status == AttendanceStatus.PRESENT,
                    AttendanceSession.school_id == school_id,
                    AttendanceSession.date.between(start_date, end_date),
                )
            ) or 0

            absent_days = int(total_sessions) - int(present_days)
            percentage = (float(present_days) / float(total_sessions) * 100.0) if total_sessions else 0.0

            out.append(
                {
                    "studentId": s.id,
                    "studentName": s.name,
                    "totalSessions": int(total_sessions),
                    "presentDays": int(present_days),
                    "absentDays": int(absent_days),
                    "percentage": float(round(percentage, 2)),
                }
            )

        return out

    # Coach summary
    filters = [
        CoachAttendance.school_id == school_id,
        CoachAttendance.date.between(start_date, end_date),
    ]
    if coach_name:
        filters.append(CoachAttendance.coach_name == coach_name)

    coach_rows = db.execute(
        select(CoachAttendance.coach_name, CoachAttendance.date)
        .where(*filters)
        .order_by(CoachAttendance.coach_name, CoachAttendance.date)
    ).all()

    if not coach_rows:
        return []

    summary_map: dict[str, dict[str, object]] = {}
    for coach_value, _attendance_date in coach_rows:
        normalized_coach = coach_value or "Unknown Coach"
        if normalized_coach not in summary_map:
            summary_map[normalized_coach] = {
                "coach_name": normalized_coach,
                "totalSessions": int(total_sessions),
                "presentDays": 0,
            }

        entry = summary_map[normalized_coach]
        entry["presentDays"] = int(entry["presentDays"]) + 1

    results: List[dict] = []
    for coach_key in sorted(summary_map.keys(), key=lambda name: name.lower() if name else ""):
        entry = summary_map[coach_key]
        present_days = int(entry["presentDays"])

        results.append(
            {
                "coach_name": entry["coach_name"],
                "totalSessions": int(total_sessions),
                "presentDays": present_days,
            }
        )

    return results
