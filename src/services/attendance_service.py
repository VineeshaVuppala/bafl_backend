"""Attendance service helpers for student and coach tracking."""

from datetime import date
from typing import Any, Iterable, List, Optional

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
from src.db.repositories.school_repository import SchoolRepository
from src.db.repositories.student_repository import StudentRepository


def _coerce_status_value(raw_status: Any) -> AttendanceStatus:
    """Normalize an arbitrary payload value into an ``AttendanceStatus`` enum."""
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
def _resolve_coach(db: Session, coach_name: str) -> Optional[Coach]:
    """Return a coach by username first, then by display name if needed."""

    coach = CoachRepository.get_by_username(db, coach_name)
    if coach:
        return coach
    return db.scalar(select(Coach).where(Coach.name == coach_name))


def _fetch_coach_attendance(
    db: Session,
    *,
    coach_name: str,
    school_id: int,
    record_date: date,
) -> Optional[CoachAttendance]:
    """Load an existing coach attendance row if it already exists."""

    return db.scalar(
        select(CoachAttendance).where(
            CoachAttendance.coach_name == coach_name,
            CoachAttendance.school_id == school_id,
            CoachAttendance.date == record_date,
        )
    )


def _ensure_coach_attendance(
    db: Session,
    *,
    school: School,
    record_date: date,
    coach_name: str,
) -> None:
    """Insert or update the coach attendance record for the given payload."""

    coach = _resolve_coach(db, coach_name)
    existing = _fetch_coach_attendance(
        db,
        coach_name=coach_name,
        school_id=school.id,
        record_date=record_date,
    )

    coach_id = coach.id if coach else None
    if existing:
        has_changes = False
        if existing.coach_id != coach_id:
            existing.coach_id = coach_id
            has_changes = True
        if existing.coach_name != coach_name:
            existing.coach_name = coach_name
            has_changes = True
        if has_changes:
            db.add(existing)
        return

    db.add(
        CoachAttendance(
            coach_id=coach_id,
            coach_name=coach_name,
            school_id=school.id,
            school_name=school.name,
            date=record_date,
        )
    )


def _get_school_or_404(db: Session, school_id: int) -> School:
    """Return the school object or raise if it does not exist."""

    school = SchoolRepository.get_by_id(db, school_id)
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")
    return school


def _get_or_create_session(
    db: Session,
    *,
    school: School,
    record_date: date,
    taken_by_user: User,
) -> AttendanceSession:
    """Fetch the attendance session for the school/date or create it."""

    session = db.scalar(
        select(AttendanceSession).where(
            AttendanceSession.school_id == school.id,
            AttendanceSession.date == record_date,
        )
    )

    if session:
        return session

    session = AttendanceSession(
        school_id=school.id,
        date=record_date,
        taken_by_user_id=taken_by_user.id,
    )
    db.add(session)
    db.flush()
    return session


def _validate_student_membership(student: Student, school_id: int) -> None:
    """Ensure the student belongs to the provided school."""

    if not student.batch or getattr(student.batch, "school_id", None) != school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student {student.id} does not belong to school {school_id}",
        )


def _update_attendance_records(
    db: Session,
    *,
    session: AttendanceSession,
    records: Iterable[Any],
) -> int:
    """Create or update ``AttendanceRecord`` entries and return the update count."""

    students_updated = 0

    for rec in records:
        student = StudentRepository.get_by_id(db, rec.id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with id {rec.id} not found",
            )

        _validate_student_membership(student, session.school_id)

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
                students_updated += 1
            continue

        db.add(
            AttendanceRecord(
                session_id=session.id,
                student_id=student.id,
                status=status_enum,
            )
        )
        students_updated += 1

    return students_updated


def mark_attendance(db: Session, payload: Any, current_user: User) -> dict:
    """Record student attendance and optionally track coach presence."""

    school = _get_school_or_404(db, payload.school_id)
    record_date: date = payload.date

    session = _get_or_create_session(
        db,
        school=school,
        record_date=record_date,
        taken_by_user=current_user,
    )

    students_updated = _update_attendance_records(
        db,
        session=session,
        records=payload.records,
    )

    coach_name = getattr(payload, "marked_by_coach", None)
    if coach_name:
        _ensure_coach_attendance(
            db,
            school=school,
            record_date=record_date,
            coach_name=coach_name,
        )

    db.commit()

    return {
        "message": "Attendance recorded successfully",
        "sessionId": session.id,
        "studentsUpdated": students_updated,
        "coachName": coach_name,
    }


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
