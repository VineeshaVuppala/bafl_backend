# src/schemas/attendance.py
from __future__ import annotations
from datetime import date
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, AliasChoices, ConfigDict


class AttendanceRecordItem(BaseModel):
    id: int = Field(..., description="student id")
    status: str = Field(..., description="Present or Absent")


class AttendanceMarkRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    school_id: int
    date: date
    records: List[AttendanceRecordItem]
    marked_by_coach: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "marked_by_coach",
            "markedByCoach",
            "marked_by_name",
            "markedByName",
        ),
    )


class AttendanceMarkResponse(BaseModel):
    message: str
    sessionId: int
    studentsUpdated: int
    coachName: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceEditRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    records: List[AttendanceRecordItem]


class AttendanceEditResponse(BaseModel):
    message: str
    sessionId: int
    studentsUpdated: int

    class Config:
        from_attributes = True


class AttendanceViewResponse(BaseModel):
    session_id: int
    date: date
    type: str
    records: List[Dict[str, Any]]

    class Config:
        from_attributes = True


class AttendanceSummaryItem(BaseModel):
    studentId: int
    studentName: str
    totalSessions: int
    presentDays: int
    absentDays: int
    percentage: float


class CoachAttendanceSummaryResponse(BaseModel):
    detail: str
