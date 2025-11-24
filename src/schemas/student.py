from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StudentBase(BaseModel):
    name: str
    age: int
    school_id: Optional[int] = None
    coach_id: Optional[int] = None
    batch_id: Optional[int] = None

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    school_id: Optional[int] = None
    coach_id: Optional[int] = None
    batch_id: Optional[int] = None

class StudentResponse(StudentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class StudentChangeBatchRequest(BaseModel):
    new_batch_id: int

class StudentChangeBatchResponse(BaseModel):
    message: str
    student: dict
