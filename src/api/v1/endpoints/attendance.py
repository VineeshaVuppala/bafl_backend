# src/api/v1/attendance.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date

from src.db.database import get_db
from src.api.v1.dependencies.auth import require_role
from src.db.models.user import User, UserRole

from src.schemas.attendance import (
    AttendanceMarkRequest,
    AttendanceMarkResponse,
    AttendanceViewResponse,
    AttendanceEditRequest,
    AttendanceEditResponse,
    AttendanceSummaryItem,
)
from src.services.attendance_service import (
    mark_attendance,
    view_attendance,
    edit_attendance,
    attendance_summary,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/student", response_model=AttendanceMarkResponse, status_code=status.HTTP_201_CREATED)
def mark_student_attendance(
    payload: AttendanceMarkRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.COACH)),
    db: Session = Depends(get_db),
):
    try:
        return mark_attendance(db, payload, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/view", response_model=AttendanceViewResponse)
def get_attendance_view(
    type: str = Query(..., regex="^(student|coach)$"),
    school_id: int = Query(...),
    date: date = Query(...),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.COACH)),
    db: Session = Depends(get_db),
):
    try:
        return view_attendance(db, type, school_id, date)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/student/{session_id}", response_model=AttendanceEditResponse)
def put_attendance_edit(
    session_id: int,
    payload: AttendanceEditRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.COACH)),
    db: Session = Depends(get_db),
):
    try:
        return edit_attendance(db, session_id, payload, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
def get_attendance_summary(
    school_id: int = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    summary_type: str = Query(..., regex="^(student|coach)$", alias="type"),
    studentId: int | None = Query(None),
    coachName: str | None = Query(None),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.COACH)),
    db: Session = Depends(get_db),
):
    try:
        return attendance_summary(
            db,
            start_date=start_date,
            end_date=end_date,
            summary_type=summary_type,
            student_id=studentId,
            school_id=school_id,
            coach_name=coachName,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
