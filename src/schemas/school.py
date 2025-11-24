from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SchoolBase(BaseModel):
    name: str


class SchoolCreate(SchoolBase):
    """Input payload for creating schools (legacy/internal)."""


class SchoolUpdate(BaseModel):
    name: Optional[str] = None


class SchoolResponse(SchoolBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SchoolCreateResponse(BaseModel):
    """Contract response for school creation."""
    school_id: int
    school_name: str
