from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime, time
from src.schemas.student import StudentResponse
from src.schemas.batch import BatchSummary, BatchScheduleItem
from src.schemas.school import SchoolResponse

class PhysicalAssessmentResultBase(BaseModel):
    discipline: Optional[str] = None
    curl_up: Optional[int] = 0
    push_up: Optional[int] = 0
    sit_and_reach: Optional[float] = 0.0
    walk_600m: Optional[float] = 0.0
    dash_50m: Optional[float] = 0.0
    bow_hold: Optional[float] = 0.0
    plank: Optional[float] = 0.0
    is_present: Optional[bool] = False


class PhysicalAssessmentResultInput(PhysicalAssessmentResultBase):
    student_id: int


class PhysicalAssessmentResultCreate(PhysicalAssessmentResultBase):
    student_id: int

class PhysicalAssessmentResultUpdate(PhysicalAssessmentResultBase):
    pass

class PhysicalAssessmentResultResponse(PhysicalAssessmentResultBase):
    id: int
    session_id: int
    student_id: int
    student: Optional[StudentResponse] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PhysicalAssessmentSessionBase(BaseModel):
    coach_id: Optional[int] = None
    school_id: Optional[int] = None
    batch_id: Optional[int] = None
    date_of_session: date
    time_of_session: Optional[time] = None
    student_count: int

class PhysicalAssessmentSessionCreate(PhysicalAssessmentSessionBase):
    pass

class PhysicalAssessmentSessionWithResultsCreate(PhysicalAssessmentSessionBase):
    results: List["PhysicalAssessmentResultInput"]
    admin_override: Optional[bool] = False


class PhysicalAssessmentSessionUpdate(BaseModel):
    coach_id: Optional[int] = None
    school_id: Optional[int] = None
    batch_id: Optional[int] = None
    date_of_session: Optional[date] = None
    student_count: Optional[int] = None

class PhysicalAssessmentSessionResponse(PhysicalAssessmentSessionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    batch: Optional[BatchSummary] = None
    school: Optional[SchoolResponse] = None
    batch_schedule: List[BatchScheduleItem] = Field(default_factory=list)
    results: List[PhysicalAssessmentResultResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

class PhysicalAssessmentSessionAdminView(BaseModel):
    session_id: int
    batch_id: Optional[int] = None
    batch_name: Optional[str] = None
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    coach_id: Optional[int] = None
    coach_name: Optional[str] = None
    date_of_session: date
    time_of_session: Optional[time] = None

class PhysicalAssessmentSessionAdminViewResponse(BaseModel):
    sessions: List[PhysicalAssessmentSessionAdminView]

class PreCreateSchedule(BaseModel):
    schedule_id: int
    day_of_week: str
    start_time: time
    end_time: time

class PreCreateCoach(BaseModel):
    coach_id: int
    coach_name: str

class PreCreateStudent(BaseModel):
    student_id: int
    student_name: str
    age: int

class PreCreateBatch(BaseModel):
    batch_id: int
    batch_name: str
    school_id: int
    school_name: str
    schedule: List[PreCreateSchedule]
    coaches: List[PreCreateCoach]
    students: List[PreCreateStudent]

class PreCreateResponse(BaseModel):
    batches: List[PreCreateBatch]
